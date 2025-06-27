"""
Ofi Documentos Adjuntos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app, make_response
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.exceptions import NotFound

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError, MyUploadError
from lib.exceptions import (
    MyFilenameError,
    MyMissingConfigurationError,
    MyNotAllowedExtensionError,
    MyUnknownExtensionError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs, upload_file_to_gcs
from lib.safe_string import safe_string, safe_message, safe_uuid
from lib.storage import GoogleCloudStorage
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.ofi_documentos_adjuntos.models import OfiDocumentoAdjunto
from hercules.blueprints.ofi_documentos_adjuntos.forms import OfiDocumentoAdjuntoForm
from hercules.blueprints.ofi_documentos.models import OfiDocumento


MODULO = "OFI DOCUMENTOS ADJUNTOS"

ofi_documentos_adjuntos = Blueprint("ofi_documentos_adjuntos", __name__, template_folder="templates")

SUBDIRECTORIO = "oficios_adjuntos"


@ofi_documentos_adjuntos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Oficios-Documentos-Adjuntos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiDocumentoAdjunto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "ofi_documento_id" in request.form:
        consulta = consulta.filter_by(ofi_documento_id=request.form["ofi_documento_id"])
    # Luego filtrar por columnas de otras tablas
    # if "persona_rfc" in request.form:
    #     consulta = consulta.join(Persona)
    #     consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(OfiDocumentoAdjunto.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=resultado.id),
                },
                "nombre": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos")
def list_active():
    """Listado de Oficios-Documentos-Adjuntos activos"""
    return render_template(
        "ofi_documentos_adjuntos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Documentos Adjuntos",
        estatus="A",
    )


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Oficios-Documentos-Adjuntos inactivos"""
    return render_template(
        "ofi_documentos_adjuntos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Documentos Adjuntos inactivos",
        estatus="B",
    )


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/<ofi_documento_adjunto_id>")
def detail(ofi_documento_adjunto_id):
    """Detalle de un Oficio-Documento-Adjunto"""
    ofi_documento_adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_adjunto.ofi_documento_id)
    # Mostrar boton de quitar
    mostrar_boton_quitar = False
    if (
        ofi_documento.estado == "BORRADOR"
        or ofi_documento.estado == "FIRMADO"
        and not ofi_documento.esta_cancelado
        and not ofi_documento.esta_archivado
    ):
        mostrar_boton_quitar = True
    # Entregar plantilla
    return render_template(
        "ofi_documentos_adjuntos/detail.jinja2",
        ofi_documento_adjunto=ofi_documento_adjunto,
        mostrar_boton_quitar=mostrar_boton_quitar,
    )


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/nuevo/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_ofi_documento(ofi_documento_id):
    """Nuevo Oficio-Documento-Adjunto"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    form = OfiDocumentoAdjuntoForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True
        # Guardar cambios con un archivo adjunto
        # Validar archivo
        archivo = request.files["archivo"]
        storage = GoogleCloudStorage(base_directory=SUBDIRECTORIO, allowed_extensions=["pdf", "jpg", "jpeg", "docx", "xlsx"])
        try:
            storage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False
        if es_valido:
            # crear un nuevo registro
            ofi_documento_adjunto = OfiDocumentoAdjunto(
                ofi_documento=ofi_documento,
                descripcion=safe_string(form.descripcion.data),
            )
            ofi_documento_adjunto.save()
            # Subir a Google Cloud Storage
            es_exitoso = True
            try:
                storage.set_filename(hashed_id=ofi_documento_adjunto.encode_id(), description=ofi_documento_adjunto.descripcion)
                # storage.set_content_type(archivo.tipo)
                storage.upload(archivo.stream.read())
            except (MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError):
                flash("Error fatal al subir el archivo a GCS.", "warning")
                es_exitoso = False
            except MyMissingConfigurationError:
                flash("Error al subir el archivo porque falla la configuración de GCS.", "danger")
                es_exitoso = False
            except Exception:
                flash("Error desconocido al subir el archivo.", "danger")
                es_exitoso = False
            # Remplazar archivo
            if es_exitoso:
                ofi_documento_adjunto.archivo = storage.filename
                ofi_documento_adjunto.url = storage.url
                ofi_documento_adjunto.save()
                # Salida en bitacora
                bitacora = Bitacora(
                    modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                    usuario=current_user,
                    descripcion=safe_message(f"Nuevo Oficio - Documento Adjunto {ofi_documento_adjunto.descripcion}"),
                    url=url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=ofi_documento_adjunto.id),
                )
                bitacora.save()
                flash(bitacora.descripcion, "success")
                return redirect(bitacora.url)
    return render_template("ofi_documentos_adjuntos/new.jinja2", form=form, ofi_documento=ofi_documento)


# TODO: Edit


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/eliminar/<ofi_documento_adjunto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_documento_adjunto_id):
    """Eliminar Oficio-Documento-Adjunto"""
    ofi_documento_adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)
    if ofi_documento_adjunto.estatus == "A":
        ofi_documento_adjunto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Oficio-Documento-Adjunto {ofi_documento_adjunto.descripcion}"),
            url=url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=ofi_documento_adjunto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_adjunto.ofi_documento_id))


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/recuperar/<ofi_documento_adjunto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_documento_adjunto_id):
    """Recuperar Oficio-Documento-Adjunto"""
    ofi_documento_adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)
    if ofi_documento_adjunto.estatus == "B":
        ofi_documento_adjunto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Oficio-Documento-Adjunto {ofi_documento_adjunto.descripcion}"),
            url=url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=ofi_documento_adjunto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_adjunto.ofi_documento_id))


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/<ofi_documento_adjunto_id>/pdf")
def download_pdf(ofi_documento_adjunto_id):
    """Descargar el archivo PDF de un Archivo"""

    # Consultar
    adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)

    # Si el estatus es B, no se puede descargar
    if adjunto.estatus == "B":
        flash("No se puede descargar un archivo inactivo", "warning")
        return redirect(url_for("personas_adjuntos.detail", ofi_documento_adjunto_id=adjunto.id))

    # Tomar el nombre del archivo con el que sera descargado
    descarga_nombre = adjunto.archivo

    # Obtener el contenido del archivo desde Google Storage
    try:
        descarga_contenido = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(adjunto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        flash(str(error), "danger")
        return redirect(url_for("ofi_documentos_adjuntos.detail", ofi_documento_adjunto_id=adjunto.id))

    # Descargar un archivo PDF
    response = make_response(descarga_contenido)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={descarga_nombre}"
    return response


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/ver_archivo_pdf/<ofi_documento_adjunto_id>")
def view_file_pdf(ofi_documento_adjunto_id):
    """Ver archivo PDF de adjunto para insertarlo en un iframe en el detalle"""

    # Consultar
    adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(adjunto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        print(adjunto.url)
        raise NotFound("No se encontró el archivo.")

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response


@ofi_documentos_adjuntos.route("/ofi_documentos_adjuntos/ver_archivo_img/<ofi_documento_adjunto_id>")
def view_file_img(ofi_documento_adjunto_id):
    """Ver archivo PDF de adjunto para insertarlo en un iframe en el detalle"""

    # Consultar
    adjunto = OfiDocumentoAdjunto.query.get_or_404(ofi_documento_adjunto_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(adjunto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        print(adjunto.url)
        raise NotFound("No se encontró el archivo.")

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "image/jpeg"
    return response
