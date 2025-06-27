"""
Exh Exhortos Promociones Archivos, vistas
"""

import hashlib
import json
from datetime import datetime

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.exceptions import NotFound
from werkzeug.utils import secure_filename

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos_promociones.models import ExhExhortoPromocion
from hercules.blueprints.exh_exhortos_promociones_archivos.forms import (
    ExhExhortoPromocionArchivoEditForm,
    ExhExhortoPromocionArchivoNewForm,
)
from hercules.blueprints.exh_exhortos_promociones_archivos.models import ExhExhortoPromocionArchivo
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError, MyUploadError
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs, upload_file_to_gcs
from lib.safe_string import safe_message, safe_string

MODULO = "EXH EXHORTOS PROMOCIONES ARCHIVOS"

exh_exhortos_promociones_archivos = Blueprint("exh_exhortos_promociones_archivos", __name__, template_folder="templates")


@exh_exhortos_promociones_archivos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_promociones_archivos.route("/exh_exhortos_promociones_archivos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de archivos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoPromocionArchivo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_promocion_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_promocion_id=request.form["exh_exhorto_promocion_id"])
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoPromocionArchivo.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre_archivo": resultado.nombre_archivo,
                    "url": url_for("exh_exhortos_promociones_archivos.detail", exh_exhorto_promocion_archivo_id=resultado.id),
                },
                "descargar_pdf": {
                    "nombre_archivo": resultado.nombre_archivo,
                    "url": url_for(
                        "exh_exhortos_promociones_archivos.download_pdf", exh_exhorto_promocion_archivo_id=resultado.id
                    ),
                },
                "tipo_documento_descripcion": resultado.tipo_documento_descripcion,
                "tamano": f"{round((resultado.tamano / 1024), 2)} MB",
                "estado": resultado.estado,
                "folio_origen_promocion": resultado.exh_exhorto_promocion.folio_origen_promocion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_promociones_archivos.route("/exh_exhortos_promociones_archivos")
def list_active():
    """Listado de archivos activos"""
    return render_template(
        "exh_exhortos_promociones_archivos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos Promociones Archivos",
        estatus="A",
    )


@exh_exhortos_promociones_archivos.route("/exh_exhortos_promociones_archivos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de archivos inactivos"""
    return render_template(
        "exh_exhortos_promociones_archivos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos Promociones Archivos inactivos",
        estatus="B",
    )


@exh_exhortos_promociones_archivos.route("/exh_exhortos_promociones_archivos/<int:exh_exhorto_promocion_archivo_id>")
def detail(exh_exhorto_promocion_archivo_id):
    """Detalle de un archivo"""
    exh_exhorto_promocion_archivo = ExhExhortoPromocionArchivo.query.get_or_404(exh_exhorto_promocion_archivo_id)
    return render_template(
        "exh_exhortos_promociones_archivos/detail.jinja2", exh_exhorto_promocion_archivo=exh_exhorto_promocion_archivo
    )


@exh_exhortos_promociones_archivos.route(
    "/exh_exhortos_promociones_archivos/nuevo/<int:exh_exhorto_promocion_id>", methods=["GET", "POST"]
)
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto_promocion(exh_exhorto_promocion_id):
    """Nuevo archivo con el ID de una promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)

    # Crear el formulario
    form = ExhExhortoPromocionArchivoNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        # Tomar el archivo del formulario
        archivo = request.files["archivo"]

        # Validar que el nombre del archivo tenga la extension PDF
        nombre_archivo = secure_filename(archivo.filename)
        if not nombre_archivo.lower().endswith(".pdf"):
            flash("El archivo debe ser un PDF", "warning")
            return redirect(url_for("exh_exhortos_promocion.detail", exh_exhorto_promocion_id=exh_exhorto_promocion_id))

        # Definir la fecha y hora de recepción
        fecha_hora_recepcion = datetime.now()

        # Insertar el registro ExhExhortoArchivo
        exh_exhorto_promocion_archivo = ExhExhortoPromocionArchivo(
            exh_exhorto_promocion=exh_exhorto_promocion,
            nombre_archivo=nombre_archivo,
            hash_sha1="",
            hash_sha256="",
            tipo_documento=form.tipo_documento.data,
            url="",
            estado="PENDIENTE",
            tamano=0,
            fecha_hora_recepcion=fecha_hora_recepcion,
        )
        exh_exhorto_promocion_archivo.save()

        # Definir el nombre del archivo a subir a Google Storage
        archivo_pdf_nombre = f"exh_exhorto_promocion_archivo-{exh_exhorto_promocion_archivo.encode_id()}.pdf"

        # Definir la ruta para blob_name con la fecha actual
        year = fecha_hora_recepcion.strftime("%Y")
        month = fecha_hora_recepcion.strftime("%m")
        day = fecha_hora_recepcion.strftime("%d")
        blob_name = f"exh_exhortos_archivos/{year}/{month}/{day}/{archivo_pdf_nombre}"

        # Subir el archivo en Google Storage
        try:
            data = archivo.stream.read()
            archivo_pdf_url = upload_file_to_gcs(
                bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
                blob_name=blob_name,
                content_type="application/pdf",
                data=data,
            )
        except (MyBucketNotFoundError, MyUploadError) as error:
            exh_exhorto_promocion_archivo.delete()
            flash(str(error), "danger")
            return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion_id))

        # Definir con hashlib el sha1 y hash256 del archivo
        exh_exhorto_promocion_archivo.hash_sha1 = hashlib.sha1(data).hexdigest()
        exh_exhorto_promocion_archivo.hash_sha256 = hashlib.sha256(data).hexdigest()

        # Si se sube con éxito, actualizar el registro con la URL del archivo
        exh_exhorto_promocion_archivo.url = archivo_pdf_url
        exh_exhorto_promocion_archivo.tamano = len(data)
        exh_exhorto_promocion_archivo.estado = "PENDIENTE"
        exh_exhorto_promocion_archivo.save()

        # Insertar en la Bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Archivo {exh_exhorto_promocion_archivo.nombre_archivo}"),
            url=url_for(
                "exh_exhortos_promociones_archivos.detail", exh_exhorto_promocion_archivo_id=exh_exhorto_promocion_archivo.id
            ),
        )
        bitacora.save()

        # Mostrar mensaje de éxito y redirigir a la página del detalle del ExhExhorto
        flash(bitacora.descripcion, "success")
        return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion_id))

    # Entregar el formulario
    return render_template(
        "exh_exhortos_promociones_archivos/new_with_exh_exhorto_promocion.jinja2",
        form=form,
        exh_exhorto_promocion=exh_exhorto_promocion,
    )


@exh_exhortos_promociones_archivos.route(
    "/exh_exhortos_promociones_archivos/edicion/<int:exh_exhorto_promocion_archivo_id>", methods=["GET", "POST"]
)
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_promocion_archivo_id):
    """Editar un archivo"""
    exh_exhorto_promocion_archivo = ExhExhortoPromocionArchivo.query.get_or_404(exh_exhorto_promocion_archivo_id)
    # Si el estado del promoción NO es PENDIENTE, no se puede editar
    if exh_exhorto_promocion_archivo.exh_exhorto_promocion.estado != "PENDIENTE":
        flash("No se puede editar porque la promoción que no está en estado PENDIENTE", "warning")
        return redirect(
            url_for(
                "exh_exhortos_promociones_archivos.detail", exh_exhorto_promocion_archivo_id=exh_exhorto_promocion_archivo_id
            )
        )
    # Crear formulario
    form = ExhExhortoPromocionArchivoEditForm()
    if form.validate_on_submit():
        exh_exhorto_promocion_archivo.nombre_archivo = safe_string(form.nombre_archivo.data)
        exh_exhorto_promocion_archivo.tipo_documento = form.tipo_documento.data
        exh_exhorto_promocion_archivo.fecha_hora_recepcion = datetime.now()
        exh_exhorto_promocion_archivo.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Archivo {exh_exhorto_promocion_archivo.nombre_archivo}"),
            url=url_for(
                "exh_exhortos_promociones_archivos.detail", exh_exhorto_promocion_archivo_id=exh_exhorto_promocion_archivo.id
            ),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.nombre_archivo.data = exh_exhorto_promocion_archivo.nombre_archivo
    form.hash_sha1.data = exh_exhorto_promocion_archivo.hash_sha1
    form.hash_sha256.data = exh_exhorto_promocion_archivo.hash_sha256
    form.tipo_documento.data = exh_exhorto_promocion_archivo.tipo_documento
    form.url.data = exh_exhorto_promocion_archivo.url
    form.tamano.data = f"{exh_exhorto_promocion_archivo.tamano / 1024} MB"
    form.fecha_hora_recepcion.data = exh_exhorto_promocion_archivo.fecha_hora_recepcion.strftime("%Y-%m-%d %H:%M:%S")
    return render_template(
        "exh_exhortos_promociones_archivos/edit.jinja2", form=form, exh_exhorto_promocion_archivo=exh_exhorto_promocion_archivo
    )


@exh_exhortos_promociones_archivos.route("/exh_exhortos_promociones_archivos/eliminar/<int:exh_exhorto_promocion_archivo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_promocion_archivo_id):
    """Eliminar un archivo"""
    exh_exhorto_promocion_archivo = ExhExhortoPromocionArchivo.query.get_or_404(exh_exhorto_promocion_archivo_id)
    if exh_exhorto_promocion_archivo.estatus == "A":
        exh_exhorto_promocion_archivo.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Archivo {exh_exhorto_promocion_archivo.id}"),
            url=url_for(
                "exh_exhortos_promociones_archivos.detail", exh_exhorto_promocion_archivo_id=exh_exhorto_promocion_archivo.id
            ),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(
        url_for("exh_exhortos_promociones_archivos.detail", exh_exhorto_promocion_archivo_id=exh_exhorto_promocion_archivo.id)
    )


@exh_exhortos_promociones_archivos.route("/exh_exhortos_promociones_archivos/recuperar/<int:exh_exhorto_promocion_archivo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_promocion_archivo_id):
    """Recuperar un archivo"""
    exh_exhorto_promocion_archivo = ExhExhortoPromocionArchivo.query.get_or_404(exh_exhorto_promocion_archivo_id)
    if exh_exhorto_promocion_archivo.estatus == "B":
        exh_exhorto_promocion_archivo.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Archivo {exh_exhorto_promocion_archivo.id}"),
            url=url_for(
                "exh_exhortos_promociones_archivos.detail", exh_exhorto_promocion_archivo_id=exh_exhorto_promocion_archivo.id
            ),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(
        url_for("exh_exhortos_promociones_archivos.detail", exh_exhorto_promocion_archivo_id=exh_exhorto_promocion_archivo.id)
    )


@exh_exhortos_promociones_archivos.route("/exh_exhortos_promociones_archivos/<int:exh_exhorto_promocion_archivo_id>/pdf")
def download_pdf(exh_exhorto_promocion_archivo_id):
    """Descargar un archivo PDF"""

    # Consultar
    exh_exhorto_promocion_archivo = ExhExhortoPromocionArchivo.query.get_or_404(exh_exhorto_promocion_archivo_id)

    # Si el estatus es B, no se puede descargar
    if exh_exhorto_promocion_archivo.estatus == "B":
        flash("No se puede descargar un archivo inactivo", "warning")
        return redirect(
            url_for(
                "exh_exhortos_promociones.detail",
                exh_exhorto_promocion_id=exh_exhorto_promocion_archivo.exh_exhorto_promocion_id,
            )
        )

    # Tomar el nombre del archivo con el que sera descargado
    descarga_nombre = exh_exhorto_promocion_archivo.nombre_archivo

    # Obtener el contenido del archivo desde Google Storage
    try:
        descarga_contenido = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(exh_exhorto_promocion_archivo.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        flash(str(error), "danger")
        return redirect(
            url_for(
                "exh_exhortos_promociones.detail",
                exh_exhorto_promocion_id=exh_exhorto_promocion_archivo.exh_exhorto_promocion_id,
            )
        )

    # Descargar un archivo PDF
    response = make_response(descarga_contenido)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={descarga_nombre}"
    return response


@exh_exhortos_promociones_archivos.route(
    "/exh_exhortos_promociones_archivos/ver_archivo_pdf/<int:exh_exhorto_promocion_archivo_id>"
)
def view_file_pdf(exh_exhorto_promocion_archivo_id):
    """Ver un archivo PDF para insertarlo en un iframe en el detalle"""

    # Consultar
    exh_exhorto_promocion_archivo = ExhExhortoPromocionArchivo.query.get_or_404(exh_exhorto_promocion_archivo_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO"],
            blob_name=get_blob_name_from_url(exh_exhorto_promocion_archivo.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.")

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response
