"""
Exh Exhortos Respuestas, vistas
"""

import json

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_areas.models import ExhArea
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_respuestas.forms import ExhExhortoRespuestaForm
from hercules.blueprints.exh_exhortos_respuestas.models import ExhExhortoRespuesta
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.municipios.models import Municipio
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.pwgen import generar_identificador
from lib.safe_string import safe_expediente, safe_message, safe_string

MODULO = "EXH EXHORTOS RESPUESTAS"

ESTADO_TURNADO_CLAVE = "05"  # Clave INEGI del estado por defecto, 05 es COAHUILA DE ZARAGOZA
MUNICIPIO_TURNADO_CLAVE = "030"  # Clave INEGI del municipio por defecto, 030 es SALTILLO
AREA_TURNADO_CLAVE = "SLT-OCP"  # Clave de Área Turnado por defecto

exh_exhortos_respuestas = Blueprint("exh_exhortos_respuestas", __name__, template_folder="templates")


@exh_exhortos_respuestas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de respuestas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoRespuesta.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_id=request.form["exh_exhorto_id"])
    if "respuesta_origen_id" in request.form:
        respuesta_origen_id = safe_string(
            request.form["respuesta_origen_id"], max_len=64, do_unidecode=True, to_uppercase=False
        )
        if respuesta_origen_id != "":
            consulta = consulta.filter(ExhExhortoRespuesta.respuesta_origen_id.contains(respuesta_origen_id))
    if "numero_exhorto" in request.form:
        try:
            numero_exhorto = safe_expediente(request.form["numero_exhorto"])
            consulta = consulta.filter(ExhExhortoRespuesta.numero_exhorto == numero_exhorto)
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoRespuesta.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "respuesta_origen_id": resultado.respuesta_origen_id,
                    "url": url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=resultado.id),
                },
                "municipio_turnado_id": resultado.municipio_turnado_id if resultado.municipio_turnado_id else "",
                "area_turnado_id": resultado.area_turnado_id if resultado.area_turnado_id else "",
                "area_turnado_nombre": resultado.area_turnado_nombre if resultado.area_turnado_nombre else "",
                "numero_exhorto": resultado.numero_exhorto if resultado.numero_exhorto else "",
                "tipo_diligenciado_nombre": resultado.tipo_diligenciado_nombre,
                "remitente": resultado.remitente,
                "estado": resultado.estado,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
                "exhorto_origen_id": resultado.exh_exhorto.exhorto_origen_id,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas")
def list_active():
    """Listado de respuestas activas"""
    return render_template(
        "exh_exhortos_respuestas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos Respuestas",
        estatus="A",
    )


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de respuestas inactivas"""
    return render_template(
        "exh_exhortos_respuestas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos Respuestas inactivas",
        estatus="B",
    )


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/<int:exh_exhorto_respuesta_id>")
def detail(exh_exhorto_respuesta_id):
    """Detalle de una respuesta"""
    exh_exhorto_respuesta = ExhExhortoRespuesta.query.get_or_404(exh_exhorto_respuesta_id)
    return render_template("exh_exhortos_respuestas/detail.jinja2", exh_exhorto_respuesta=exh_exhorto_respuesta)


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/nuevo/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto(exh_exhorto_id):
    """Nueva respuesta con el ID de un exhorto"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)

    # Crear el formulario
    form = ExhExhortoRespuestaForm()
    if form.validate_on_submit():
        # Si no se eligió un área, se usan valores nulos
        area_turnado_id = None
        area_turnado_nombre = None
        exh_area = ExhArea.query.get(form.area_turnado.data)
        if exh_area:
            area_turnado_id = exh_area.clave
            area_turnado_nombre = exh_area.nombre

        # Si no se eligió un municipio, se usa un valor nulo
        municipio_turnado_id = None
        municipio = Municipio.query.get(form.municipio_turnado.data)
        if municipio:
            municipio_turnado_id = int(municipio.clave)  # Identificador INEGI del municipio

        # Si no se eligió un tipo_diligenciado, se usa un valor nulo
        tipo_diligenciado = None
        if form.tipo_diligenciado.data:
            tipo_diligenciado = form.tipo_diligenciado.data

        # Insertar el registro ExhExhortoRespuesta
        exh_exhorto_respuesta = ExhExhortoRespuesta(
            exh_exhorto=exh_exhorto,
            respuesta_origen_id=safe_string(form.respuesta_origen_id.data, max_len=64, to_uppercase=False),
            municipio_turnado_id=municipio_turnado_id,
            area_turnado_id=area_turnado_id,
            area_turnado_nombre=area_turnado_nombre,
            numero_exhorto=safe_expediente(form.numero_exhorto.data),
            tipo_diligenciado=tipo_diligenciado,
            observaciones=form.observaciones.data,
            remitente="INTERNO",
            estado="PENDIENTE",
        )
        exh_exhorto_respuesta.save()

        # Insertar en la Bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva Respuesta {exh_exhorto_respuesta.respuesta_origen_id}"),
            url=url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id),
        )
        bitacora.save()

        # Mostrar mensaje de éxito y redirigir a la página del detalle del ExhExhorto
        flash(bitacora.descripcion, "success")
        return redirect(url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id))

    # Consultar el municipio turnado por defecto
    municipio = (
        Municipio.query.join(Estado)
        .filter(Estado.clave == ESTADO_TURNADO_CLAVE)
        .filter(Municipio.clave == MUNICIPIO_TURNADO_CLAVE)
        .first()
    )

    # Consultar el área turnado por defecto
    area_turnado = ExhArea.query.filter_by(clave=AREA_TURNADO_CLAVE).first()

    # Definir los valores por defecto del formulario
    form.respuesta_origen_id.data = generar_identificador()  # Read only
    form.municipio_turnado.data = municipio.id
    form.area_turnado.data = area_turnado.id
    form.tipo_diligenciado.data = 0  # Cero es "NO DILIGENCIADO"

    # Entregar el formulario
    return render_template("exh_exhortos_respuestas/new_with_exh_exhorto.jinja2", form=form, exh_exhorto=exh_exhorto)


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/edicion/<int:exh_exhorto_respuesta_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_respuesta_id):
    """Editar una respuesta"""
    exh_exhorto_respuesta = ExhExhortoRespuesta.query.get_or_404(exh_exhorto_respuesta_id)

    # Crear el formulario
    form = ExhExhortoRespuestaForm()
    if form.validate_on_submit():
        # Si no se eligió un área, se usan valores nulos
        area_turnado_id = None
        area_turnado_nombre = None
        exh_area = ExhArea.query.get(form.area_turnado.data)
        if exh_area:
            area_turnado_id = exh_area.clave
            area_turnado_nombre = exh_area.nombre

        # Si no se eligió un municipio, se usa un valor nulo
        municipio_turnado_id = None
        municipio = Municipio.query.get(form.municipio_turnado.data)
        if municipio:
            municipio_turnado_id = int(municipio.clave)

        # Si no se eligió un tipo_diligenciado, se usa un valor nulo
        tipo_diligenciado = None
        if form.tipo_diligenciado.data:
            tipo_diligenciado = form.tipo_diligenciado.data

        # Actualizar la respuesta
        exh_exhorto_respuesta.municipio_turnado_id = municipio_turnado_id
        exh_exhorto_respuesta.area_turnado_id = area_turnado_id
        exh_exhorto_respuesta.area_turnado_nombre = area_turnado_nombre
        exh_exhorto_respuesta.numero_exhorto = safe_expediente(form.numero_exhorto.data)
        exh_exhorto_respuesta.tipo_diligenciado = tipo_diligenciado
        exh_exhorto_respuesta.observaciones = safe_string(form.observaciones.data, save_enie=True, max_len=1024)
        exh_exhorto_respuesta.save()

        # Insertar en la Bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editada Respuesta {exh_exhorto_respuesta.origen_id}"),
            url=url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Consultar el municipio a partir del identificador INEGI del mismo
    municipio_turnado = None
    if exh_exhorto_respuesta.municipio_turnado_id:
        municipio_turnado = (
            Municipio.query.join(Estado)
            .filter(Estado.clave == current_app.config["ESTADO_CLAVE"])
            .filter(Municipio.clave == exh_exhorto_respuesta.municipio_turnado_id)
            .first()
        )

    # Definir los valores del formulario
    form.respuesta_origen_id.data = exh_exhorto_respuesta.respuesta_origen_id  # Read only
    if municipio_turnado:
        form.municipio_turnado.data = municipio_turnado.id
    else:
        form.municipio_turnado.data = 0
    if exh_exhorto_respuesta.area_turnado_id:
        form.area_turnado.data = exh_exhorto_respuesta.area_turnado_id
    else:
        form.area_turnado.data = 0
    if exh_exhorto_respuesta.tipo_diligenciado:
        form.tipo_diligenciado.data = exh_exhorto_respuesta.tipo_diligenciado
    else:
        form.tipo_diligenciado.data = 0

    # Entregar el formulario
    return render_template("exh_exhortos_respuestas/edit.jinja2", form=form, exh_exhorto_respuesta=exh_exhorto_respuesta)


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/eliminar/<int:exh_exhorto_respuesta_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_respuesta_id):
    """Eliminar una respuesta"""
    exh_exhorto_respuesta = ExhExhortoRespuesta.query.get_or_404(exh_exhorto_respuesta_id)
    if exh_exhorto_respuesta.estatus == "A":
        exh_exhorto_respuesta.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado respuesta {exh_exhorto_respuesta.id}"),
            url=url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id))


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/recuperar/<int:exh_exhorto_respuesta_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_respuesta_id):
    """Recuperar una respuesta"""
    exh_exhorto_respuesta = ExhExhortoRespuesta.query.get_or_404(exh_exhorto_respuesta_id)
    if exh_exhorto_respuesta.estatus == "B":
        exh_exhorto_respuesta.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado respuesta {exh_exhorto_respuesta.id}"),
            url=url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id))


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/enviar/<int:exh_exhorto_respuesta_id>")
@permission_required(MODULO, Permiso.CREAR)
def launch_task_send(exh_exhorto_respuesta_id):
    """Lanzar tarea en el fondo para enviar una respuesta al PJ Externo"""
    exh_exhorto_respuesta = ExhExhortoRespuesta.query.get_or_404(exh_exhorto_respuesta_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_respuesta.estado != "POR ENVIAR":
        es_valido = False
        flash("El estado de la respuesta debe ser POR ENVIAR.", "warning")
    if exh_exhorto_respuesta.exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("El exhorto está ARCHIVADO. No se puede enviar la respuesta.", "warning")
    if exh_exhorto_respuesta.exh_exhorto.estado == "CANCELADO":
        es_valido = False
        flash("El exhorto está CANCELADO. No se puede enviar la respuesta.", "warning")
    # Lanzar tarea en el fondo
    if es_valido:
        tarea = current_user.launch_task(
            comando="exh_exhortos_respuestas.tasks.task_enviar_respuesta",
            mensaje="Enviando la respuesta al PJ externo",
            exh_exhorto_respuesta_id=exh_exhorto_respuesta_id,
        )
        flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
        return redirect(url_for("tareas.detail", tarea_id=tarea.id))
    # Redirigir al detalle porque NO se lanzó la tarea
    return redirect(url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id))


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/cancelar/<int:exh_exhorto_respuesta_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_cancel(exh_exhorto_respuesta_id):
    """Cambiar el estado de la respuesta a CANCELADO"""
    exh_exhorto_respuesta = ExhExhortoRespuesta.query.get_or_404(exh_exhorto_respuesta_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_respuesta.estado == "CANCELADO":
        es_valido = False
        flash("Esta respuesta ya está CANCELADA.", "warning")
    if exh_exhorto_respuesta.estado == "ENVIADO":
        es_valido = False
        flash("Esta respuesta ya fue ENVIADA. No puede ser cancelada.", "warning")
    if exh_exhorto_respuesta.estado == "POR ENVIAR":
        es_valido = False
        flash("Esta respuesta está POR ENVIAR. No puede ser cancelada.", "warning")
    if exh_exhorto_respuesta.exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("El exhorto está ARCHIVADO. No se puede cancelar la respuesta.", "warning")
    # Cambiar el estado
    if es_valido:
        exh_exhorto_respuesta.estado = "CANCELADO"
        exh_exhorto_respuesta.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha CANCELADO la respuesta"),
            url=url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id))


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/cambiar_a_pendiente/<int:exh_exhorto_respuesta_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_pending(exh_exhorto_respuesta_id):
    """Cambiar el estado de la respuesta a PENDIENTE"""
    exh_exhorto_respuesta = ExhExhortoRespuesta.query.get_or_404(exh_exhorto_respuesta_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_respuesta.estado == "PENDIENTE":
        es_valido = False
        flash("Esta respuesta ya estaba PENDIENTE.", "warning")
    if exh_exhorto_respuesta.estado == "ENVIADO":
        es_valido = False
        flash("Esta respuesta ya fue ENVIADA. No puede se puede cambiar su estado.", "warning")
    if exh_exhorto_respuesta.exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("El exhorto está ARCHIVADO. No se puede cambiar la promoción.", "warning")
    if exh_exhorto_respuesta.exh_exhorto.estado == "CANCELADO":
        es_valido = False
        flash("El exhorto está CANCELADO. No se puede cambiar la promoción.", "warning")
    # Cambiar el estado
    if es_valido:
        exh_exhorto_respuesta.estado = "PENDIENTE"
        exh_exhorto_respuesta.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha cambiado a PENDIENTE la respuesta"),
            url=url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id))


@exh_exhortos_respuestas.route("/exh_exhortos_respuestas/cambiar_a_por_enviar/<int:exh_exhorto_respuesta_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_send(exh_exhorto_respuesta_id):
    """Cambiar el estado de la respuesta a POR ENVIAR"""
    exh_exhorto_respuesta = ExhExhortoRespuesta.query.get_or_404(exh_exhorto_respuesta_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_respuesta.estado == "POR ENVIAR":
        es_valido = False
        flash("Esta respuesta ya estaba POR ENVIAR.", "warning")
    if exh_exhorto_respuesta.estado == "ENVIADO":
        es_valido = False
        flash("Esta respuesta ya fue ENVIADA. No puede se puede cambiar su estado.", "warning")
    if exh_exhorto_respuesta.exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("El exhorto está ARCHIVADO. No se puede cambiar la promoción.", "warning")
    if exh_exhorto_respuesta.exh_exhorto.estado == "CANCELADO":
        es_valido = False
        flash("El exhorto está CANCELADO. No se puede cambiar la promoción.", "warning")
    # Cambiar el estado
    if es_valido:
        exh_exhorto_respuesta.estado = "POR ENVIAR"
        exh_exhorto_respuesta.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha cambiado a POR ENVIAR la respuesta"),
            url=url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta.id))
