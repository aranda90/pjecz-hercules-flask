"""
Cid Areas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.cid_areas.forms import CIDAreaForm
from hercules.blueprints.cid_areas.models import CIDArea
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "CID AREAS"

cid_areas = Blueprint("cid_areas", __name__, template_folder="templates")

# Roles que deben estar en la base de datos
ROL_ADMINISTRADOR = "ADMINISTRADOR"


@cid_areas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@cid_areas.route("/cid_areas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de areas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = CIDArea.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"])
            if clave != "":
                consulta = consulta.filter(CIDArea.clave.contains(clave))
        except ValueError:
            pass
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(CIDArea.nombre.contains(nombre))
    # Ordenar y paginar
    registros = consulta.order_by(CIDArea.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("cid_areas.detail", cid_area_id=resultado.id),
                },
                "nombre": resultado.nombre,
                "descripcion": resultado.descripcion,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@cid_areas.route("/cid_areas")
def list_active():
    """Listado de Areas activos"""
    return render_template(
        "cid_areas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="SICGD Áreas",
        estatus="A",
    )


@cid_areas.route("/cid_areas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Áreas inactivos"""
    return render_template(
        "cid_areas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="SICGD Áreas inactivos",
        estatus="B",
    )


@cid_areas.route("/cid_areas/<int:cid_area_id>")
def detail(cid_area_id):
    """Detalle de un Area"""
    # Consultar los roles del usuario
    current_user_roles = current_user.get_roles()
    cid_area = CIDArea.query.get_or_404(cid_area_id)
    # Si es administrador, usar detail_admin.jinja2
    if current_user.can_admin(MODULO) or ROL_ADMINISTRADOR in current_user_roles:
        return render_template("cid_areas/detail_admin.jinja2", cid_area=cid_area)
    # De lo contrario, usar detail.jinja2
    return render_template("cid_areas/detail.jinja2", cid_area=cid_area)


@cid_areas.route("/cid_areas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva Area"""
    form = CIDAreaForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data)
        if CIDArea.query.filter_by(clave=clave).first():
            flash("La clave ya está en uso. Debe de ser única.", "warning")
            es_valido = False
        nombre = safe_string(form.nombre.data)
        # Si es válido, guardar
        if es_valido is True:
            cid_area = CIDArea(
                clave=clave,
                nombre=nombre,
                descripcion=safe_string(form.descripcion.data, save_enie=True),
            )
            cid_area.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo cid_area {cid_area.clave}"),
                url=url_for("cid_areas.detail", cid_area_id=cid_area.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("cid_areas/new.jinja2", form=form)


@cid_areas.route("/cid_areas/edicion/<int:cid_area_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(cid_area_id):
    """Editar Area"""
    cid_area = CIDArea.query.get_or_404(cid_area_id)
    form = CIDAreaForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data)
        if cid_area.clave != clave:
            cid_area_existente = CIDArea.query.filter_by(clave=clave).first()
            if cid_area_existente and cid_area_existente.id != cid_area.id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        nombre = safe_string(form.nombre.data)
        # Si es válido, actualizar
        if es_valido:
            cid_area.clave = clave
            cid_area.nombre = nombre
            cid_area.descripcion = safe_string(form.descripcion.data, save_enie=True)
            cid_area.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editada area {cid_area.clave}"),
                url=url_for("cid_areas.detail", cid_area_id=cid_area.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.clave.data = cid_area.clave
    form.nombre.data = cid_area.nombre
    form.descripcion.data = cid_area.descripcion
    return render_template("cid_areas/edit.jinja2", form=form, cid_area=cid_area)


@cid_areas.route("/cid_areas/eliminar/<int:cid_area_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(cid_area_id):
    """Eliminar Área"""
    cid_area = CIDArea.query.get_or_404(cid_area_id)
    if cid_area.estatus == "A":
        cid_area.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada área {cid_area.nombre}"),
            url=url_for("cid_areas.detail", cid_area_id=cid_area.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("cid_areas.detail", cid_area_id=cid_area.id))


@cid_areas.route("/cid_areas/recuperar/<int:cid_area_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(cid_area_id):
    """Recuperar Área"""
    cid_area = CIDArea.query.get_or_404(cid_area_id)
    if cid_area.estatus == "B":
        cid_area.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperada área {cid_area.nombre}"),
            url=url_for("cid_areas.detail", cid_area_id=cid_area.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("cid_areas.detail", cid_area_id=cid_area.id))
