"""
Exhorto Promociones, vistas
"""

import hashlib
import json
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_promociones.forms import ExhExhortoPromocionEditForm, ExhExhortoPromocionNewForm
from hercules.blueprints.exh_exhortos_promociones.models import ExhExhortoPromocion
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.municipios.models import Municipio
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.pwgen import generar_identificador
from lib.safe_string import safe_message, safe_string

MODULO = "EXH EXHORTOS PROMOCIONES"

exh_exhortos_promociones = Blueprint("exh_exhortos_promociones", __name__, template_folder="templates")


@exh_exhortos_promociones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_promociones.route("/exh_exhortos_promociones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Promociones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoPromocion.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_id=request.form["exh_exhorto_id"])
    if "folio_origen" in request.form:
        folio_origen = safe_string(request.form["folio_origen"])
        consulta = consulta.filter(ExhExhortoPromocion.folio_origen_promocion.contains(folio_origen))
    if "remitente" in request.form:
        consulta = consulta.filter_by(remitente=request.form["remitente"])
    if "observaciones" in request.form:
        observaciones = safe_string(request.form["observaciones"])
        consulta = consulta.filter(ExhExhortoPromocion.observaciones.contains(observaciones))
    # Luego filtrar por columnas de otras tablas
    # if "persona_rfc" in request.form:
    #     consulta = consulta.join(Persona)
    #     consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoPromocion.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "folio_origen_promocion": {
                    "folio": resultado.folio_origen_promocion,
                    "url": url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=resultado.id),
                },
                "fecha_origen": resultado.fecha_origen.strftime("%Y/%m/%d %H:%M"),
                "remitente": resultado.remitente,
                "fojas": resultado.fojas,
                "observaciones": resultado.observaciones,
                "estado": resultado.estado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_promociones.route("/exh_exhortos_promociones")
def list_active():
    """Listado de Promociones activos"""
    return render_template(
        "exh_exhortos_promociones/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Promociones",
        remitentes=ExhExhortoPromocion.REMITENTES,
        estatus="A",
    )


@exh_exhortos_promociones.route("/exh_exhortos_promociones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Promociones inactivos"""
    return render_template(
        "exh_exhortos_promociones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Promociones inactivos",
        remitentes=ExhExhortoPromocion.REMITENTES,
        estatus="B",
    )


@exh_exhortos_promociones.route("/exh_exhortos_promociones/<int:exh_exhorto_promocion_id>")
def detail(exh_exhorto_promocion_id):
    """Detalle de un Promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    # Consultar el municipio de origen porque NO es una relacion
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto_promocion.exh_exhorto.municipio_destino_id).first()
    estado = municipio_destino.estado.nombre
    return render_template("exh_exhortos_promociones/detail.jinja2", exh_exhorto_promocion=exh_exhorto_promocion, estado=estado)


@exh_exhortos_promociones.route("/exh_exhortos_promociones/nuevo_con_exhorto/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto(exh_exhorto_id):
    """Nuevo Archivo con un Exhorto"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)

    form = ExhExhortoPromocionNewForm()
    if form.validate_on_submit():
        # Insertar el registro ExhExhortoPromocion
        exh_exhorto_promocion = ExhExhortoPromocion(
            exh_exhorto=exh_exhorto,
            folio_origen_promocion=form.folio_origen.data,
            fecha_origen=datetime.now(),
            fojas=form.fojas.data,
            remitente="INTERNO",
            estado="PENDIENTE",
            observaciones=safe_string(form.observaciones.data, max_len=1024),
        )
        exh_exhorto_promocion.save()

        # Insertar en la Bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva Promoción {exh_exhorto_promocion.id}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()

        # Mostrar mensaje de éxito y redirigir a la página del detalle del ExhExhorto
        flash(bitacora.descripcion, "success")
        return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))

    # Entregar el formulario
    # Crear y mostrar el folio de origen
    form.folio_origen.data = generar_identificador()
    return render_template("exh_exhortos_promociones/new_with_exh_exhorto.jinja2", form=form, exh_exhorto=exh_exhorto)


@exh_exhortos_promociones.route("/exh_exhortos_promociones/edicion/<int:exh_exhorto_promocion_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_promocion_id):
    """Editar Promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    form = ExhExhortoPromocionEditForm()
    if form.validate_on_submit():
        exh_exhorto_promocion.fojas = form.fojas.data
        exh_exhorto_promocion.observaciones = safe_string(form.observaciones.data, max_len=1024)
        exh_exhorto_promocion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Promoción {exh_exhorto_promocion.folio_origen_promocion}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.fecha_origen.data = exh_exhorto_promocion.fecha_origen.strftime("%Y/%m/%d %H:%M")
    form.fojas.data = exh_exhorto_promocion.fojas
    form.observaciones.data = exh_exhorto_promocion.observaciones
    return render_template("exh_exhortos_promociones/edit.jinja2", form=form, exh_exhorto_promocion=exh_exhorto_promocion)


@exh_exhortos_promociones.route("/exh_exhortos_promociones/eliminar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_promocion_id):
    """Eliminar Promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    if exh_exhorto_promocion.estatus == "A":
        exh_exhorto_promocion.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Promoción {exh_exhorto_promocion.folio_origen_promocion}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))


@exh_exhortos_promociones.route("/exh_exhortos_promociones/recuperar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_promocion_id):
    """Recuperar Promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    if exh_exhorto_promocion.estatus == "B":
        exh_exhorto_promocion.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Promoción {exh_exhorto_promocion.folio_origen_promocion}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))


@exh_exhortos_promociones.route("/exh_exhortos_promociones/enviar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def launch_task_send_promotion(exh_exhorto_promocion_id):
    """Lanzar tarea en el fondo para enviar una promoción al PJ Externo"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    # Validar el estado
    if exh_exhorto_promocion.estado != "PENDIENTE":
        flash("El estado de la promoción debe ser PENDIENTE.", "warning")
        return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))
    # Lanzar tarea en el fondo
    tarea = current_user.launch_task(
        comando="exh_exhortos_promociones.tasks.task_enviar_promocion",
        mensaje="Enviando la promoción al PJ externo",
        exh_exhorto_promocion_id=exh_exhorto_promocion_id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))
