"""
Exh Exhortos Promociones, vistas
"""

import json
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_promociones.forms import ExhExhortoPromocionForm
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
    """DataTable JSON para listado de promociones"""
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
    if "folio_origen_promocion" in request.form:
        folio_origen_promocion = safe_string(
            request.form["folio_origen_promocion"], max_len=64, do_unidecode=True, to_uppercase=False
        )
        if folio_origen_promocion != "":
            consulta = consulta.filter(ExhExhortoPromocion.folio_origen_promocion.contains(folio_origen_promocion))
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoPromocion.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "folio_origen_promocion": resultado.folio_origen_promocion,
                    "url": url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=resultado.id),
                },
                "fecha_origen": resultado.fecha_origen.strftime("%Y-%m-%d %H:%M"),
                "remitente": resultado.remitente,
                "fojas": resultado.fojas,
                "observaciones": resultado.observaciones,
                "estado": resultado.estado,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
                "exhorto_origen_id": resultado.exh_exhorto.exhorto_origen_id,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_promociones.route("/exh_exhortos_promociones")
def list_active():
    """Listado de promociones activas"""
    return render_template(
        "exh_exhortos_promociones/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos Promociones",
        remitentes=ExhExhortoPromocion.REMITENTES,
        estatus="A",
    )


@exh_exhortos_promociones.route("/exh_exhortos_promociones/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de promociones inactivas"""
    return render_template(
        "exh_exhortos_promociones/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos Promociones inactivas",
        remitentes=ExhExhortoPromocion.REMITENTES,
        estatus="B",
    )


@exh_exhortos_promociones.route("/exh_exhortos_promociones/<int:exh_exhorto_promocion_id>")
def detail(exh_exhorto_promocion_id):
    """Detalle de una promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    return render_template("exh_exhortos_promociones/detail.jinja2", exh_exhorto_promocion=exh_exhorto_promocion)


@exh_exhortos_promociones.route("/exh_exhortos_promociones/nuevo/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto(exh_exhorto_id):
    """Nueva promoción con el ID de un exhorto"""
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
    form = ExhExhortoPromocionForm()
    if form.validate_on_submit():
        # Insertar el registro ExhExhortoPromocion
        exh_exhorto_promocion = ExhExhortoPromocion(
            exh_exhorto=exh_exhorto,
            folio_origen_promocion=safe_string(form.folio_origen_promocion.data, max_len=64, to_uppercase=False),
            fecha_origen=datetime.now(),
            fojas=form.fojas.data,
            remitente="INTERNO",
            estado="PENDIENTE",
            observaciones=safe_string(form.observaciones.data, save_enie=True, max_len=1024),
        )
        exh_exhorto_promocion.save()

        # Insertar en la Bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva Promoción {exh_exhorto_promocion.folio_origen_promocion}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()

        # Mostrar mensaje de éxito y redirigir a la página del detalle del ExhExhorto
        flash(bitacora.descripcion, "success")
        return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))

    # Cargar valores por defecto al formulario
    form.folio_origen_promocion.data = generar_identificador()  # Read only

    # Entregar el formulario
    return render_template("exh_exhortos_promociones/new_with_exh_exhorto.jinja2", form=form, exh_exhorto=exh_exhorto)


@exh_exhortos_promociones.route("/exh_exhortos_promociones/edicion/<int:exh_exhorto_promocion_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_promocion_id):
    """Editar una promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)

    # Si el estado de la promoción NO es PENDIENTE, no se puede editar
    if exh_exhorto_promocion.estado != "PENDIENTE":
        flash("No se puede editar porque el estado de la promoción no es PENDIENTE.", "warning")
        return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion_id))

    # Si el estado del exhorto es CANCELADO o ARCHIVADO, no se puede editar
    if exh_exhorto_promocion.exh_exhorto.estado in ("CANCELADO", "ARCHIVADO"):
        flash("No se puede editar porque el estado del exhorto es CANCELADO o ARCHIVADO.", "warning")
        return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion_id))

    # Crear formulario
    form = ExhExhortoPromocionForm()
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

    # Definir los valores del formulario
    form.folio_origen_promocion.data = exh_exhorto_promocion.folio_origen_promocion  # Read only
    form.fojas.data = exh_exhorto_promocion.fojas
    form.observaciones.data = exh_exhorto_promocion.observaciones

    # Entregar el formulario
    return render_template("exh_exhortos_promociones/edit.jinja2", form=form, exh_exhorto_promocion=exh_exhorto_promocion)


@exh_exhortos_promociones.route("/exh_exhortos_promociones/eliminar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_promocion_id):
    """Eliminar una promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    if exh_exhorto_promocion.estatus == "A":
        exh_exhorto_promocion.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Promoción {exh_exhorto_promocion.id}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))


@exh_exhortos_promociones.route("/exh_exhortos_promociones/recuperar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_promocion_id):
    """Recuperar una promoción"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    if exh_exhorto_promocion.estatus == "B":
        exh_exhorto_promocion.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Promoción {exh_exhorto_promocion.id}"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))


@exh_exhortos_promociones.route("/exh_exhortos_promociones/enviar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.CREAR)
def launch_task_send(exh_exhorto_promocion_id):
    """Lanzar tarea en el fondo para enviar una promoción al PJ Externo"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_promocion.estado not in ("POR ENVIAR", "RECHAZADO"):
        flash("No se puede enviar la promoción porque el estado debe ser POR ENVIAR o RECHAZADO.", "warning")
        es_valido = False
    # Validar el estado del exhorto
    if exh_exhorto_promocion.exh_exhorto.estado in ("ARCHIVADO", "CANCELADO"):
        flash("El exhorto está ARCHIVADO o CANCELADO. No se puede enviar la promoción.", "warning")
        es_valido = False
    # Validar que tenga archivos
    archivos = []
    for archivo in exh_exhorto_promocion.exh_exhortos_promociones_archivos:
        if archivo.estatus == "A" and archivo.estado != "CANCELADO":
            archivos.append(archivo)
    if len(archivos) == 0:
        flash("No se pudo enviar la promoción. Debe incluir al menos un archivo.", "warning")
        es_valido = False
    # Validar que tenga promoventes
    promoventes = []
    for promovente in exh_exhorto_promocion.exh_exhortos_promociones_promoventes:
        if promovente.estatus == "A":
            promoventes.append(promovente)
    if len(promoventes) == 0:
        flash("No se pudo enviar la promoción. Debe incluir al menos un promovente.", "warning")
        es_valido = False
    # Si NO es válido, redirigir al detalle
    if es_valido is False:
        return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))
    # Insertar en la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Se ha ENVIADO la promoción {exh_exhorto_promocion.folio_origen_promocion}"),
        url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
    )
    bitacora.save()
    # Lanzar tarea en el fondo
    tarea = current_user.launch_task(
        comando="exh_exhortos_promociones.tasks.task_enviar_promocion",
        mensaje="Enviando la promoción al PJ externo",
        exh_exhorto_promocion_id=exh_exhorto_promocion_id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@exh_exhortos_promociones.route("/exh_exhortos_promociones/cancelar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_cancel(exh_exhorto_promocion_id):
    """Cambiar el estado de la promoción a CANCELADO"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_promocion.estado == "CANCELADO":
        es_valido = False
        flash("Esta promoción ya está CANCELADA.", "warning")
    if exh_exhorto_promocion.estado == "ENVIADO":
        es_valido = False
        flash("Esta promoción ya fue ENVIADA. No puede ser cancelada.", "warning")
    if exh_exhorto_promocion.estado == "POR ENVIAR":
        es_valido = False
        flash("Esta promoción está POR ENVIAR. No puede ser cancelada.", "warning")
    if exh_exhorto_promocion.exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("El exhorto está ARCHIVADO. No se puede cancelar la promoción.", "warning")
    # Cambiar el estado
    if es_valido:
        exh_exhorto_promocion.estado = "CANCELADO"
        exh_exhorto_promocion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha CANCELADO la promoción"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))


@exh_exhortos_promociones.route("/exh_exhortos_promociones/cambiar_a_pendiente/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_pending(exh_exhorto_promocion_id):
    """Cambiar el estado de la promoción a PENDIENTE"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_promocion.estado == "PENDIENTE":
        es_valido = False
        flash("Esta promoción ya estaba PENDIENTE.", "warning")
    if exh_exhorto_promocion.estado == "ENVIADO":
        es_valido = False
        flash("Esta promoción ya fue ENVIADA. No puede se puede cambiar su estado.", "warning")
    if exh_exhorto_promocion.exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("El exhorto está ARCHIVADO. No se puede cambiar la promoción.", "warning")
    if exh_exhorto_promocion.exh_exhorto.estado == "CANCELADO":
        es_valido = False
        flash("El exhorto está CANCELADO. No se puede cambiar la promoción.", "warning")
    # Cambiar el estado
    if es_valido:
        exh_exhorto_promocion.estado = "PENDIENTE"
        exh_exhorto_promocion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha cambiado a PENDIENTE la promoción"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))


@exh_exhortos_promociones.route("/exh_exhortos_promociones/cambiar_a_por_enviar/<int:exh_exhorto_promocion_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_send(exh_exhorto_promocion_id):
    """Cambiar el estado de la promoción a POR ENVIAR"""
    exh_exhorto_promocion = ExhExhortoPromocion.query.get_or_404(exh_exhorto_promocion_id)
    es_valido = True
    # Validar el estado
    if exh_exhorto_promocion.estado == "POR ENVIAR":
        es_valido = False
        flash("Esta promoción ya estaba POR ENVIAR.", "warning")
    if exh_exhorto_promocion.estado == "ENVIADO":
        es_valido = False
        flash("Esta promoción ya fue ENVIADA. No puede se puede cambiar su estado.", "warning")
    if exh_exhorto_promocion.exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("El exhorto está ARCHIVADO. No se puede cambiar la promoción.", "warning")
    if exh_exhorto_promocion.exh_exhorto.estado == "CANCELADO":
        es_valido = False
        flash("El exhorto está CANCELADO. No se puede cambiar la promoción.", "warning")
    # Validar que tenga archivos
    archivos = []
    for archivo in exh_exhorto_promocion.exh_exhortos_promociones_archivos:
        if archivo.estatus == "A" and archivo.estado != "CANCELADO":
            archivos.append(archivo)
    if len(archivos) == 0:
        flash("No se puede cambiar el estado de la promoción a POR ENVIAR. Debe incluir al menos un archivo.", "warning")
        es_valido = False
    # Validar que tenga promoventes
    promoventes = []
    for promovente in exh_exhorto_promocion.exh_exhortos_promociones_promoventes:
        if promovente.estatus == "A":
            promoventes.append(promovente)
    if len(promoventes) == 0:
        flash("No se puede cambiar el estado de la promoción a POR ENVIAR. Debe incluir al menos un promovente.", "warning")
        es_valido = False
    # Cambiar el estado
    if es_valido:
        exh_exhorto_promocion.estado = "POR ENVIAR"
        exh_exhorto_promocion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha cambiado a POR ENVIAR la promoción"),
            url=url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_promociones.detail", exh_exhorto_promocion_id=exh_exhorto_promocion.id))
