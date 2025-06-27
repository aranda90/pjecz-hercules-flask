"""
Ofi Documentos Destinatarios, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message, safe_uuid

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.ofi_documentos_destinatarios.models import OfiDocumentoDestinatario
from hercules.blueprints.ofi_documentos_destinatarios.forms import OfiDocumentoDestinatarioForm
from hercules.blueprints.ofi_documentos.models import OfiDocumento


MODULO = "OFI DOCUMENTOS DESTINATARIOS"

ofi_documentos_destinatarios = Blueprint("ofi_documentos_destinatarios", __name__, template_folder="templates")


@ofi_documentos_destinatarios.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Ofi-Documentos-Destinatarios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiDocumentoDestinatario.query
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
    registros = consulta.order_by(OfiDocumentoDestinatario.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=resultado.id),
                },
                "usuario_nombre": resultado.usuario.nombre,
                "usuario_email": {
                    "email": resultado.usuario.email,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario.id),
                },
                "fue_leido": resultado.fue_leido,
                "con_copia": resultado.con_copia,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios")
def list_active():
    """Listado de Ofi-Documentos-Destinatarios activos"""
    return render_template(
        "ofi_documentos_destinatarios/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Destinatarios",
        estatus="A",
    )


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Ofi-Documentos-Destinatarios inactivos"""
    return render_template(
        "ofi_documentos_destinatarios/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Destinatarios inactivos",
        estatus="B",
    )


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/<ofi_documento_destinatario_id>")
def detail(ofi_documento_destinatario_id):
    """Detalle de un Ofi-Documento-Destinatario"""
    ofi_documento_destinatario = OfiDocumentoDestinatario.query.get_or_404(ofi_documento_destinatario_id)
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_destinatario.ofi_documento_id)
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
        "ofi_documentos_destinatarios/detail.jinja2",
        ofi_documento_destinatario=ofi_documento_destinatario,
        mostrar_boton_quitar=mostrar_boton_quitar,
    )


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/nuevo/<ofi_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_ofi_documento(ofi_documento_id):
    """Nuevo Ofi-Documento-Destinatario"""
    ofi_documento = OfiDocumento.query.get_or_404(ofi_documento_id)
    form = OfiDocumentoDestinatarioForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que el destinatario no esté ya listado en este ofi-documento
        destinatario_repetido = OfiDocumentoDestinatario.query.filter_by(
            ofi_documento_id=ofi_documento_id, usuario_id=form.usuario.data
        ).first()
        if destinatario_repetido:
            if destinatario_repetido.estatus == "B":
                destinatario_repetido.recover()
                return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_id))
            else:
                flash(f"Destinatario '{destinatario_repetido.usuario.nombre}' ya se encuentra agregado", "warning")
                es_valido = False
        if es_valido:
            ofi_documento_destinatario = OfiDocumentoDestinatario(
                ofi_documento=ofi_documento,
                usuario_id=form.usuario.data,
                con_copia=form.con_copia.data,
            )
            ofi_documento_destinatario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Ofi-Documento-Destinatario {ofi_documento_destinatario.usuario}"),
                url=url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=ofi_documento_destinatario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_id))
    # Llenar Campos ReadOnly
    form.ofi_documento.data = ofi_documento.descripcion
    # Entregar plantilla
    return render_template("ofi_documentos_destinatarios/new.jinja2", form=form, ofi_documento=ofi_documento)


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/eliminar/<ofi_documento_destinatario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_documento_destinatario_id):
    """Eliminar Oficio-Destinatario"""
    ofi_documento_destinatario = OfiDocumentoDestinatario.query.get_or_404(ofi_documento_destinatario_id)
    if ofi_documento_destinatario.estatus == "A":
        ofi_documento_destinatario.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Oficio-Destinatario {ofi_documento_destinatario.usuario.nombre}"),
            url=url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=ofi_documento_destinatario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_destinatario.ofi_documento_id))


@ofi_documentos_destinatarios.route("/ofi_documentos_destinatarios/recuperar/<ofi_documento_destinatario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_documento_destinatario_id):
    """Recuperar Oficio-Destinatario"""
    ofi_documento_destinatario = OfiDocumentoDestinatario.query.get_or_404(ofi_documento_destinatario_id)
    if ofi_documento_destinatario.estatus == "B":
        ofi_documento_destinatario.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Oficio-Destinatario {ofi_documento_destinatario.usuario.nombre}"),
            url=url_for("ofi_documentos_destinatarios.detail", ofi_documento_destinatario_id=ofi_documento_destinatario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_documentos.detail", ofi_documento_id=ofi_documento_destinatario.ofi_documento_id))
