"""
Exh Exhortos Actualizaciones, vistas
"""

import json
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_actualizaciones.forms import ExhExhortoActualizacionForm
from hercules.blueprints.exh_exhortos_actualizaciones.models import ExhExhortoActualizacion
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.pwgen import generar_identificador
from lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "EXH EXHORTOS ACTUALIZACIONES"

exh_exhortos_actualizaciones = Blueprint("exh_exhortos_actualizaciones", __name__, template_folder="templates")


@exh_exhortos_actualizaciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Actualizaciones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoActualizacion.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_id=request.form["exh_exhorto_id"])
    if "actualizacion_origen_id" in request.form:
        actualizacion_origen_id = safe_string(
            request.form["actualizacion_origen_id"], max_len=64, do_unidecode=True, to_uppercase=False
        )
        if actualizacion_origen_id:
            consulta = consulta.filter(ExhExhortoActualizacion.actualizacion_origen_id.contains(actualizacion_origen_id))
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoActualizacion.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "actualizacion_origen_id": resultado.actualizacion_origen_id,
                    "url": url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=resultado.id),
                },
                "tipo_actualizacion": resultado.tipo_actualizacion,
                "descripcion": resultado.descripcion,
                "remitente": resultado.remitente,
                "estado": resultado.estado,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
                "exhorto_origen_id": resultado.exh_exhorto.exhorto_origen_id,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones")
def list_active():
    """Listado de Actualizaciones activos"""
    return render_template(
        "exh_exhortos_actualizaciones/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos Actualizaciones",
        estatus="A",
    )


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Actualizaciones inactivas"""
    return render_template(
        "exh_exhortos_actualizaciones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos Actualizaciones inactivas",
        estatus="B",
    )


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/<int:exh_exhorto_actualizacion_id>")
def detail(exh_exhorto_actualizacion_id):
    """Detalle de un Actualización"""
    exh_exhorto_actualizacion = ExhExhortoActualizacion.query.get_or_404(exh_exhorto_actualizacion_id)
    return render_template("exh_exhortos_actualizaciones/detail.jinja2", exh_exhorto_actualizacion=exh_exhorto_actualizacion)


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/nuevo/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto(exh_exhorto_id):
    """Nuevo Actualización"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)

    # Validar el estatus del exhorto
    if exh_exhorto.estatus != "A":
        flash("El exhorto debe estar ACTIVO para responder.", "warning")
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto_id))

    # Validar el estado del exhorto
    if exh_exhorto.estado not in ("RECIBIDO", "RECIBIDO CON EXITO", "PROCESANDO", "RESPONDIDO", "CONTESTADO"):
        flash(f"El exhorto tiene el estado {exh_exhorto.estado}. No se puede responder.", "warning")
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto_id))

    # Crear el formulario
    form = ExhExhortoActualizacionForm()
    if form.validate_on_submit():
        exh_exhorto_actualizacion = ExhExhortoActualizacion(
            exh_exhorto=exh_exhorto,
            actualizacion_origen_id=safe_string(form.actualizacion_origen_id.data, max_len=64, to_uppercase=False),
            tipo_actualizacion=safe_string(form.tipo_actualizacion.data, max_len=64, to_uppercase=False),
            descripcion=safe_string(form.descripcion.data),
            fecha_hora=datetime.now(),
            remitente="INTERNO",
            estado="PENDIENTE",
        )
        exh_exhorto_actualizacion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Actualización {exh_exhorto_actualizacion.id}"),
            url=url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.actualizacion_origen_id.data = generar_identificador()  # Read only
    return render_template("exh_exhortos_actualizaciones/new_with_exh_exhorto.jinja2", form=form, exh_exhorto=exh_exhorto)


@exh_exhortos_actualizaciones.route(
    "/exh_exhortos_actualizaciones/edicion/<int:exh_exhorto_actualizacion_id>", methods=["GET", "POST"]
)
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_actualizacion_id):
    """Editar Actualización"""
    exh_exhorto_actualizacion = ExhExhortoActualizacion.query.get_or_404(exh_exhorto_actualizacion_id)

    # Si el estado del exhorto es CANCELADO o ARCHIVADO, no se puede editar
    if exh_exhorto_actualizacion.exh_exhorto.estado in ("CANCELADO", "ARCHIVADO"):
        flash("No se puede editar porque el estado del exhorto no es PENDIENTE.", "warning")
        return redirect(
            url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion_id)
        )

    # Crear formulario
    form = ExhExhortoActualizacionForm()
    if form.validate_on_submit():
        exh_exhorto_actualizacion.tipo_actualizacion = safe_string(form.tipo_actualizacion.data, max_len=64, to_uppercase=False)
        exh_exhorto_actualizacion.descripcion = safe_string(form.descripcion.data)
        exh_exhorto_actualizacion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Actualización {exh_exhorto_actualizacion.descripcion}"),
            url=url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Definir los valores del formulario
    form.tipo_actualizacion.data = exh_exhorto_actualizacion.tipo_actualizacion
    form.descripcion.data = exh_exhorto_actualizacion.descripcion

    # Entregar el formulario
    return render_template(
        "exh_exhortos_actualizaciones/edit.jinja2", form=form, exh_exhorto_actualizacion=exh_exhorto_actualizacion
    )


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/eliminar/<int:exh_exhorto_actualizacion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_actualizacion_id):
    """Eliminar Actualización"""
    exh_exhorto_actualizacion = ExhExhortoActualizacion.query.get_or_404(exh_exhorto_actualizacion_id)
    if exh_exhorto_actualizacion.estatus == "A":
        exh_exhorto_actualizacion.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Actualización {exh_exhorto_actualizacion.id}"),
            url=url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id))


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/recuperar/<int:exh_exhorto_actualizacion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_actualizacion_id):
    """Recuperar Actualización"""
    exh_exhorto_actualizacion = ExhExhortoActualizacion.query.get_or_404(exh_exhorto_actualizacion_id)
    if exh_exhorto_actualizacion.estatus == "B":
        exh_exhorto_actualizacion.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Actualización {exh_exhorto_actualizacion.id}"),
            url=url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id))


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/enviar/<int:exh_exhorto_actualizacion_id>")
@permission_required(MODULO, Permiso.CREAR)
def launch_task_send(exh_exhorto_actualizacion_id):
    """Lanzar tarea en el fondo para enviar una actualización al PJ Externo"""
    exh_exhorto_actualizacion = ExhExhortoActualizacion.query.get_or_404(exh_exhorto_actualizacion_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_actualizacion.estado not in ("POR ENVIAR", "RECHAZADO"):
        flash("No se puede enviar la actualización porque el estado debe ser POR ENVIAR o RECHAZADO.", "warning")
        es_valido = False
    # Validar el estado del exhorto
    if exh_exhorto_actualizacion.exh_exhorto.estado in ("ARCHIVADO", "CANCELADO"):
        flash("El exhorto está ARCHIVADO o CANCELADO. No se puede enviar la actualización.", "warning")
        es_valido = False
    # Si NO es válido, redirigir al detalle
    if es_valido is False:
        return redirect(
            url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion_id)
        )
    # Lanzar tarea en el fondo
    tarea = current_user.launch_task(
        comando="exh_exhortos_actualizaciones.tasks.task_enviar_actualizacion",
        mensaje="Enviando la actualización al PJ Externo",
        exh_exhorto_actualizacion_id=exh_exhorto_actualizacion_id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/cancelar/<int:exh_exhorto_actualizacion_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_cancel(exh_exhorto_actualizacion_id):
    """Cancelar una actualización al PJ Externo"""
    exh_exhorto_actualizacion = ExhExhortoActualizacion.query.get_or_404(exh_exhorto_actualizacion_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_actualizacion.estado == "CANCELADO":
        es_valido = False
        flash("Esta actualización ya está CANCELADA.", "warning")
    if exh_exhorto_actualizacion.estado == "ENVIADO":
        es_valido = False
        flash("Esta actualización ya fue ENVIADA. No puede ser cancelada.", "warning")
    if exh_exhorto_actualizacion.estado == "POR ENVIAR":
        es_valido = False
        flash("Esta actualización está POR ENVIAR. No puede ser cancelada.", "warning")
    if exh_exhorto_actualizacion.exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("El exhorto está ARCHIVADO. No se puede cancelar la actualización.", "warning")
    # Cambiar el estado
    if es_valido:
        exh_exhorto_actualizacion.estado = "CANCELADO"
        exh_exhorto_actualizacion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha CANCELADO la actualización"),
            url=url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id))


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/cambiar_a_pendiente/<int:exh_exhorto_actualizacion_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_pending(exh_exhorto_actualizacion_id):
    """Cambiar el estado de la actualización a PENDIENTE"""
    exh_exhorto_actualizacion = ExhExhortoActualizacion.query.get_or_404(exh_exhorto_actualizacion_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_actualizacion.estado == "PENDIENTE":
        es_valido = False
        flash("Esta actualización ya estaba PENDIENTE.", "warning")
    if exh_exhorto_actualizacion.estado == "ENVIADO":
        es_valido = False
        flash("Esta actualización ya fue ENVIADA. No puede se puede cambiar su estado.", "warning")
    if exh_exhorto_actualizacion.exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("El exhorto está ARCHIVADO. No se puede cambiar la actualización.", "warning")
    if exh_exhorto_actualizacion.exh_exhorto.estado == "CANCELADO":
        es_valido = False
        flash("El exhorto está CANCELADO. No se puede cambiar la actualización.", "warning")
    # Cambiar el estado
    if es_valido:
        exh_exhorto_actualizacion.estado = "PENDIENTE"
        exh_exhorto_actualizacion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha cambiado a PENDIENTE la actualización"),
            url=url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id))


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/cambiar_a_por_enviar/<int:exh_exhorto_actualizacion_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_send(exh_exhorto_actualizacion_id):
    """Cambiar el estado de la actualización a POR ENVIAR"""
    exh_exhorto_actualizacion = ExhExhortoActualizacion.query.get_or_404(exh_exhorto_actualizacion_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_actualizacion.estado == "POR ENVIAR":
        es_valido = False
        flash("Esta actualización ya estaba POR ENVIAR.", "warning")
    if exh_exhorto_actualizacion.estado == "ENVIADO":
        es_valido = False
        flash("Esta actualización ya fue ENVIADA. No puede se puede cambiar su estado.", "warning")
    if exh_exhorto_actualizacion.exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("El exhorto está ARCHIVADO. No se puede cambiar la actualización.", "warning")
    if exh_exhorto_actualizacion.exh_exhorto.estado == "CANCELADO":
        es_valido = False
        flash("El exhorto está CANCELADO. No se puede cambiar la actualización.", "warning")
    # Cambiar el estado
    if es_valido:
        exh_exhorto_actualizacion.estado = "POR ENVIAR"
        exh_exhorto_actualizacion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha cambiado a POR ENVIAR la actualización"),
            url=url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id))
