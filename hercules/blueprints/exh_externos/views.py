"""
Exh Externos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_externos.forms import ExhExternoForm
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string, safe_url

MODULO = "EXH EXTERNOS"

exh_externos = Blueprint("exh_externos", __name__, template_folder="templates")


@exh_externos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_externos.route("/exh_externos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Externos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExterno.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        clave = safe_clave(request.form["clave"])
        if clave != "":
            consulta = consulta.filter(ExhExterno.clave.contains(clave))
    # Ordenar y paginar
    registros = consulta.order_by(ExhExterno.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("exh_externos.detail", exh_externo_id=resultado.id),
                },
                "api_key": "Sí" if resultado.api_key != "" else "",
                "endpoint_consultar_materias": "Sí" if resultado.endpoint_consultar_materias != "" else "",
                "endpoint_recibir_exhorto": "Sí" if resultado.endpoint_recibir_exhorto != "" else "",
                "endpoint_recibir_exhorto_archivo": "Sí" if resultado.endpoint_recibir_exhorto_archivo != "" else "",
                "endpoint_consultar_exhorto": "Sí" if resultado.endpoint_consultar_exhorto != "" else "",
                "endpoint_recibir_respuesta_exhorto": "Sí" if resultado.endpoint_recibir_respuesta_exhorto != "" else "",
                "endpoint_recibir_respuesta_exhorto_archivo": (
                    "Sí" if resultado.endpoint_recibir_respuesta_exhorto_archivo != "" else ""
                ),
                "endpoint_actualizar_exhorto": "Sí" if resultado.endpoint_actualizar_exhorto != "" else "",
                "endpoint_recibir_promocion": "Sí" if resultado.endpoint_recibir_promocion != "" else "",
                "endpoint_recibir_promocion_archivo": "Sí" if resultado.endpoint_recibir_promocion_archivo != "" else "",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_externos.route("/exh_externos")
def list_active():
    """Listado de Externos activos"""
    return render_template(
        "exh_externos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Destinatarios-Remitentes",
        estatus="A",
    )


@exh_externos.route("/exh_externos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Externos inactivos"""
    return render_template(
        "exh_externos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Destinatarios-Remitentes inactivos",
        estatus="B",
    )


@exh_externos.route("/exh_externos/<int:exh_externo_id>")
def detail(exh_externo_id):
    """Detalle de un Externo"""
    exh_externo = ExhExterno.query.get_or_404(exh_externo_id)
    return render_template("exh_externos/detail.jinja2", exh_externo=exh_externo)


@exh_externos.route("/exh_externos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Externo"""
    form = ExhExternoForm()
    if form.validate_on_submit():
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data)
        if ExhExterno.query.filter_by(clave=clave).first():
            flash("La clave ya está en uso. Debe de ser única.", "warning")
            return render_template("exh_externos/new.jinja2", form=form)
        # Validar que el estado no se repita
        estado_id = form.estado.data
        if ExhExterno.query.filter_by(estado_id=estado_id).first():
            flash("El estado ya se encuentra ocupado por otro externo. Debe de ser único.", "warning")
            return render_template("exh_externos/new.jinja2", form=form)
        # Guardar
        exh_externo = ExhExterno(
            clave=clave,
            descripcion=safe_string(form.descripcion.data, save_enie=True),
            estado_id=estado_id,
            api_key=form.api_key.data.strip(),
            endpoint_consultar_materias=safe_url(form.endpoint_consultar_materias.data),
            endpoint_recibir_exhorto=safe_url(form.endpoint_recibir_exhorto.data),
            endpoint_recibir_exhorto_archivo=safe_url(form.endpoint_recibir_exhorto_archivo.data),
            endpoint_consultar_exhorto=safe_url(form.endpoint_consultar_exhorto.data),
            endpoint_recibir_respuesta_exhorto=safe_url(form.endpoint_recibir_respuesta_exhorto.data),
            endpoint_recibir_respuesta_exhorto_archivo=safe_url(form.endpoint_recibir_respuesta_exhorto_archivo.data),
            endpoint_actualizar_exhorto=safe_url(form.endpoint_actualizar_exhorto.data),
            endpoint_recibir_promocion=safe_url(form.endpoint_recibir_promocion.data),
            endpoint_recibir_promocion_archivo=safe_url(form.endpoint_recibir_promocion_archivo.data),
        )
        exh_externo.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Externo {exh_externo.clave}"),
            url=url_for("exh_externos.detail", exh_externo_id=exh_externo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("exh_externos/new.jinja2", form=form)


@exh_externos.route("/exh_externos/edicion/<int:exh_externo_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_externo_id):
    """Editar Externo"""
    exh_externo = ExhExterno.query.get_or_404(exh_externo_id)
    form = ExhExternoForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data)
        if exh_externo.clave != clave:
            exh_externo_existente = ExhExterno.query.filter_by(clave=clave).first()
            if exh_externo_existente and exh_externo_existente.id != exh_externo_id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si cambia de estado verificar que no este en uso
        estado_id = form.estado.data
        exh_externo_estado_existente = ExhExterno.query.filter_by(estado_id=estado_id).first()
        if exh_externo_estado_existente and exh_externo_estado_existente.id != exh_externo_id:
            es_valido = False
            flash("El estado ya se encuentra ocupado por otro externo. Debe de ser único.", "warning")
        # Si es valido actualizar
        if es_valido:
            exh_externo.clave = clave
            exh_externo.descripcion = safe_string(form.descripcion.data, save_enie=True)
            exh_externo.estado_id = estado_id
            exh_externo.api_key = form.api_key.data.strip()
            exh_externo.endpoint_consultar_materias = safe_url(form.endpoint_consultar_materias.data)
            exh_externo.endpoint_recibir_exhorto = safe_url(form.endpoint_recibir_exhorto.data)
            exh_externo.endpoint_recibir_exhorto_archivo = safe_url(form.endpoint_recibir_exhorto_archivo.data)
            exh_externo.endpoint_consultar_exhorto = safe_url(form.endpoint_consultar_exhorto.data)
            exh_externo.endpoint_recibir_respuesta_exhorto = safe_url(form.endpoint_recibir_respuesta_exhorto.data)
            exh_externo.endpoint_recibir_respuesta_exhorto_archivo = safe_url(
                form.endpoint_recibir_respuesta_exhorto_archivo.data
            )
            exh_externo.endpoint_actualizar_exhorto = safe_url(form.endpoint_actualizar_exhorto.data)
            exh_externo.endpoint_recibir_promocion = safe_url(form.endpoint_recibir_promocion.data)
            exh_externo.endpoint_recibir_promocion_archivo = safe_url(form.endpoint_recibir_promocion_archivo.data)
            exh_externo.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Externo {exh_externo.clave}"),
                url=url_for("exh_externos.detail", exh_externo_id=exh_externo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Cargar valores en el formulario
    form.clave.data = exh_externo.clave
    form.descripcion.data = exh_externo.descripcion
    form.estado.data = exh_externo.estado_id
    form.api_key.data = exh_externo.api_key
    form.endpoint_consultar_materias.data = exh_externo.endpoint_consultar_materias
    form.endpoint_recibir_exhorto.data = exh_externo.endpoint_recibir_exhorto
    form.endpoint_recibir_exhorto_archivo.data = exh_externo.endpoint_recibir_exhorto_archivo
    form.endpoint_consultar_exhorto.data = exh_externo.endpoint_consultar_exhorto
    form.endpoint_recibir_respuesta_exhorto.data = exh_externo.endpoint_recibir_respuesta_exhorto
    form.endpoint_recibir_respuesta_exhorto_archivo.data = exh_externo.endpoint_recibir_respuesta_exhorto_archivo
    form.endpoint_actualizar_exhorto.data = exh_externo.endpoint_actualizar_exhorto
    form.endpoint_recibir_promocion.data = exh_externo.endpoint_recibir_promocion
    form.endpoint_recibir_promocion_archivo.data = exh_externo.endpoint_recibir_promocion_archivo
    # Entregar
    return render_template("exh_externos/edit.jinja2", form=form, exh_externo=exh_externo)


@exh_externos.route("/exh_externos/eliminar/<int:exh_externo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_externo_id):
    """Eliminar Externo"""
    exh_externo = ExhExterno.query.get_or_404(exh_externo_id)
    if exh_externo.estatus == "A":
        exh_externo.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Externo {exh_externo.clave}"),
            url=url_for("exh_externos.detail", exh_externo_id=exh_externo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_externos.detail", exh_externo_id=exh_externo.id))


@exh_externos.route("/exh_externos/recuperar/<int:exh_externo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_externo_id):
    """Recuperar Externo"""
    exh_externo = ExhExterno.query.get_or_404(exh_externo_id)
    if exh_externo.estatus == "B":
        exh_externo.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Externo {exh_externo.clave}"),
            url=url_for("exh_externos.detail", exh_externo_id=exh_externo.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_externos.detail", exh_externo_id=exh_externo.id))


@exh_externos.route("/exh_externos/probar_endpoints/<int:exh_externo_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def test_endpoints(exh_externo_id):
    """Lanzar tarea en el fondo para probar los endpoints"""
    exh_externo = ExhExterno.query.get_or_404(exh_externo_id)
    tarea = current_user.launch_task(
        comando="exh_externos.tasks.lanzar_probar_endpoints",
        mensaje="Probando endpoints",
        clave=exh_externo.clave,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@exh_externos.route("/exh_externos/select_materias_json/<int:estado_id>", methods=["GET", "POST"])
def select_materias_json(estado_id=None):
    """Select JSON para usar en Select2 y elegir una materia de un ExhExterno"""
    # Si estado_id es None, entonces no se entrega nada
    if estado_id is None:
        return json.dumps([])
    # Consultar
    consulta = ExhExterno.query.filter_by(estado_id=estado_id, estatus="A")
    # Elaborar datos para Select
    data = []
    resultado = consulta.first()
    if resultado:
        data = resultado.materias
    # Entregar JSON
    return json.dumps(data)
