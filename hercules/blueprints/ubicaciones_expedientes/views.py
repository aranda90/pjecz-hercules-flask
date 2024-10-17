"""
Ubicaciones de Expedientes, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.ubicaciones_expedientes.forms import UbicacionExpedienteEditForm, UbicacionExpedienteNewForm
from hercules.blueprints.ubicaciones_expedientes.models import UbicacionExpediente
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_expediente, safe_message, safe_string

MODULO = "UBICACIONES EXPEDIENTES"

ubicaciones_expedientes = Blueprint("ubicaciones_expedientes", __name__, template_folder="templates")


@ubicaciones_expedientes.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ubicaciones_expedientes.route("/ubicaciones_expedientes/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Ubicaciones de Expedientes"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = UbicacionExpediente.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(UbicacionExpediente.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(UbicacionExpediente.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(UbicacionExpediente.autoridad == autoridad)
    elif "autoridad_clave" in request.form:
        consulta = consulta.join(Autoridad)
        consulta = consulta.filter(Autoridad.clave.contains(safe_clave(request.form["autoridad_clave"])))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(UbicacionExpediente.expediente == expediente)
        except (IndexError, ValueError):
            pass
    if "ubicacion" in request.form:
        ubicacion = safe_string(request.form["ubicacion"])
        if ubicacion != "":
            consulta = consulta.filter(UbicacionExpediente.ubicacion == ubicacion)
    # Ordenar y paginar
    registros = consulta.order_by(UbicacionExpediente.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "id": resultado.id,
                "creado": resultado.creado.strftime("%Y-%m-%dT%H:%M:%S"),
                "autoridad": resultado.autoridad.clave,
                "detalle": {
                    "expediente": resultado.expediente,
                    "url": url_for("ubicaciones_expedientes.detail", ubicacion_expediente_id=resultado.id),
                },
                "ubicacion": resultado.ubicacion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ubicaciones_expedientes.route("/ubicaciones_expedientes")
def list_active():
    """Listado de Ubicaciones de Expedientes activos"""
    # Si es administrador ve todo
    if current_user.can_admin("UBICACIONES EXPEDIENTES"):
        return render_template(
            "ubicaciones_expedientes/list_admin.jinja2",
            ubicaciones=UbicacionExpediente.UBICACIONES,
            filtros=json.dumps({"estatus": "A"}),
            titulo="Todas las Ubicaciones de Expedientes",
            estatus="A",
        )
    autoridad = current_user.autoridad
    return render_template(
        "ubicaciones_expedientes/list.jinja2",
        ubicaciones=UbicacionExpediente.UBICACIONES,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
        titulo=f"Ubicaciones de Expedientes de {autoridad.descripcion_corta}",
        estatus="A",
    )


@ubicaciones_expedientes.route("/ubicaciones_expedientes/inactivos")
@permission_required(MODULO, Permiso.MODIFICAR)
def list_inactive():
    """Listado de Ubicaciones de Expedientes inactivos"""
    # Si es administrador ve todo
    if current_user.can_admin("UBICACIONES EXPEDIENTES"):
        return render_template(
            "ubicaciones_expedientes/list_admin.jinja2",
            ubicaciones=UbicacionExpediente.UBICACIONES,
            filtros=json.dumps({"estatus": "B"}),
            titulo="Todas las Ubicaciones de Expedientes",
            estatus="B",
        )
    autoridad = current_user.autoridad
    return render_template(
        "ubicaciones_expedientes/list.jinja2",
        ubicaciones=UbicacionExpediente.UBICACIONES,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "B"}),
        titulo=f"Ubicaciones de Expedientes inactivos de {autoridad.descripcion_corta}",
        estatus="B",
    )


@ubicaciones_expedientes.route("/ubicaciones_expedientes/<int:ubicacion_expediente_id>")
def detail(ubicacion_expediente_id):
    """Detalle de un Ubicación de Expediente"""
    ubicacion_expediente = UbicacionExpediente.query.get_or_404(ubicacion_expediente_id)
    return render_template("ubicaciones_expedientes/detail.jinja2", ubicacion_expediente=ubicacion_expediente)


@ubicaciones_expedientes.route("/ubicaciones_expedientes/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Ubicación de Expediente"""
    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad is None or autoridad.estatus != "A":
        flash("El juzgado/autoridad no existe o no es activa.", "warning")
        return redirect(url_for("ubicaciones_expedientes.list_active"))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("ubicaciones_expedientes.list_active"))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("ubicaciones_expedientes.list_active"))
    # Formulario
    form = UbicacionExpedienteNewForm()
    if form.validate_on_submit():
        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            return render_template("ubicaciones_expedientes/new.jinja2", form=form)
        # Insertar registro
        ubicacion_expediente = UbicacionExpediente(
            autoridad=autoridad,
            expediente=expediente,
            ubicacion=form.ubicacion.data,
        )
        ubicacion_expediente.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Ubicación de Expediente {ubicacion_expediente.expediente}"),
            url=url_for("ubicaciones_expedientes.detail", ubicacion_expediente_id=ubicacion_expediente.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Prellenado del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    return render_template("ubicaciones_expedientes/new.jinja2", form=form)


@ubicaciones_expedientes.route("/ubicaciones_expedientes/edicion/<int:ubicacion_expediente_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ubicacion_expediente_id):
    """Editar Ubicacion de Expediente"""
    ubicacion_expediente = UbicacionExpediente.query.get_or_404(ubicacion_expediente_id)
    form = UbicacionExpedienteEditForm()
    if form.validate_on_submit():
        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            return render_template("ubicaciones_expedientes/new.jinja2", form=form)
        # Guardar cambios
        ubicacion_expediente.expediente = expediente
        ubicacion_expediente.ubicacion = form.ubicacion.data
        ubicacion_expediente.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Ubicacion de Expediente {ubicacion_expediente.expediente}"),
            url=url_for("ubicaciones_expedientes.detail", ubicacion_expediente_id=ubicacion_expediente.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Prellenado del formulario
    form.expediente.data = ubicacion_expediente.expediente
    form.ubicacion.data = ubicacion_expediente.ubicacion
    return render_template("ubicaciones_expedientes/edit.jinja2", form=form, ubicacion_expediente=ubicacion_expediente)


@ubicaciones_expedientes.route("/ubicaciones_expedientes/eliminar/<int:ubicacion_expediente_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def delete(ubicacion_expediente_id):
    """Eliminar Ubicación de Expediente"""
    ubicacion_expediente = UbicacionExpediente.query.get_or_404(ubicacion_expediente_id)
    if ubicacion_expediente.estatus == "A":
        ubicacion_expediente.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Ubicación de Expediente {ubicacion_expediente.expediente}"),
            url=url_for("ubicaciones_expedientes.detail", ubicacion_expediente_id=ubicacion_expediente.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ubicaciones_expedientes.detail", ubicacion_expediente_id=ubicacion_expediente.id))


@ubicaciones_expedientes.route("/ubicaciones_expedientes/recuperar/<int:ubicacion_expediente_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def recover(ubicacion_expediente_id):
    """Recuperar Ubicación de Expediente"""
    ubicacion_expediente = UbicacionExpediente.query.get_or_404(ubicacion_expediente_id)
    if ubicacion_expediente.estatus == "B":
        ubicacion_expediente.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Ubicación de Expediente {ubicacion_expediente.expediente}"),
            url=url_for("ubicaciones_expedientes.detail", ubicacion_expediente_id=ubicacion_expediente.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ubicaciones_expedientes.detail", ubicacion_expediente_id=ubicacion_expediente.id))
