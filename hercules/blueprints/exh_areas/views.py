"""
Exh Areas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_areas.forms import ExhAreaForm
from hercules.blueprints.exh_areas.models import ExhArea
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "EXH AREAS"

exh_areas = Blueprint("exh_areas", __name__, template_folder="templates")


@exh_areas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_areas.route("/exh_areas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Areas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhArea.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    # Ordenar y paginar
    registros = consulta.order_by(ExhArea.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("exh_areas.detail", exh_area_id=resultado.id),
                },
                "nombre": resultado.nombre,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_areas.route("/exh_areas")
def list_active():
    """Listado de Areas activos"""
    return render_template(
        "exh_areas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos Áreas",
        estatus="A",
    )


@exh_areas.route("/exh_areas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Areas inactivos"""
    return render_template(
        "exh_areas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos Áreas inactivas",
        estatus="B",
    )


@exh_areas.route("/exh_areas/<int:exh_area_id>")
def detail(exh_area_id):
    """Detalle de un Area"""
    exh_area = ExhArea.query.get_or_404(exh_area_id)
    return render_template("exh_areas/detail.jinja2", exh_area=exh_area)


@exh_areas.route("/exh_areas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva Área"""
    form = ExhAreaForm()
    if form.validate_on_submit():
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data)
        area_repetida = ExhArea.query.filter_by(clave=clave).first()
        if area_repetida:
            flash("La clave ya está en uso. Debe de ser única.", "warning")
            return render_template("exh_areas/new.jinja2", form=form)
        # Guardar
        exh_area = ExhArea(
            clave=clave,
            nombre=safe_string(form.nombre.data),
        )
        exh_area.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva Área {exh_area.clave}"),
            url=url_for("exh_areas.detail", exh_area_id=exh_area.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("exh_areas/new.jinja2", form=form)


@exh_areas.route("/exh_areas/edicion/<int:exh_area_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_area_id):
    """Editar Área"""
    exh_area = ExhArea.query.get_or_404(exh_area_id)
    form = ExhAreaForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data)
        if exh_area.clave != clave:
            exh_area_existente = ExhArea.query.filter_by(clave=clave).first()
            if exh_area_existente and exh_area_existente.id != exh_area_id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            exh_area.clave = clave
            exh_area.nombre = safe_string(form.nombre.data)
            exh_area.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editada Área {exh_area.clave}"),
                url=url_for("exh_areas.detail", exh_area_id=exh_area.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = exh_area.clave
    form.nombre.data = exh_area.nombre
    return render_template("exh_areas/edit.jinja2", form=form, exh_area=exh_area)


@exh_areas.route("/exh_areas/eliminar/<int:exh_area_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_area_id):
    """Eliminar Área"""
    exh_area = ExhArea.query.get_or_404(exh_area_id)
    if exh_area.estatus == "A":
        exh_area.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada Área {exh_area.clave}"),
            url=url_for("exh_areas.detail", exh_area_id=exh_area.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_areas.detail", exh_area_id=exh_area.id))


@exh_areas.route("/exh_areas/recuperar/<int:exh_area_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_area_id):
    """Recuperar Área"""
    exh_area = ExhArea.query.get_or_404(exh_area_id)
    if exh_area.estatus == "B":
        exh_area.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada Área {exh_area.clave}"),
            url=url_for("exh_areas.detail", exh_area_id=exh_area.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_areas.detail", exh_area_id=exh_area.id))
