"""
Roles, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.roles.forms import RolForm
from hercules.blueprints.roles.models import Rol
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "ROLES"

roles = Blueprint("roles", __name__, template_folder="templates")


@roles.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@roles.route("/roles/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Roles"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Rol.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "nombre" in request.form:
        nombre = safe_string(request.form["nombre"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(Rol.nombre.contains(nombre))
    # Ordenar y paginar
    registros = consulta.order_by(Rol.nombre).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre,
                    "url": url_for("roles.detail", rol_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@roles.route("/roles")
def list_active():
    """Listado de Roles activos"""
    return render_template(
        "roles/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Roles",
        estatus="A",
    )


@roles.route("/roles/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Roles inactivos"""
    return render_template(
        "roles/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Roles inactivos",
        estatus="B",
    )


@roles.route("/roles/<int:rol_id>")
def detail(rol_id):
    """Detalle de un Rol"""
    rol = Rol.query.get_or_404(rol_id)
    return render_template("roles/detail.jinja2", rol=rol)


@roles.route("/roles/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Rol"""
    form = RolForm()
    if form.validate_on_submit():
        # Validar que el nombre no se repita
        nombre = safe_string(form.nombre.data, save_enie=True)
        if Rol.query.filter_by(nombre=nombre).first():
            flash("El nombre ya está en uso. Debe de ser único.", "warning")
            return render_template("roles/new.jinja2", form=form)
        # Guardar
        rol = Rol(nombre=nombre)
        rol.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Rol {rol.nombre}"),
            url=url_for("roles.detail", rol_id=rol.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("roles/new.jinja2", form=form)


@roles.route("/roles/edicion/<int:rol_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(rol_id):
    """Editar Rol"""
    rol = Rol.query.get_or_404(rol_id)
    form = RolForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia el nombre verificar que no este en uso
        nombre = safe_string(form.nombre.data, save_enie=True)
        if rol.nombre != nombre:
            rol_existente = Rol.query.filter_by(nombre=nombre).first()
            if rol_existente and rol_existente.id != rol.id:
                es_valido = False
                flash("El nombre ya está en uso. Debe de ser único.", "warning")
        # Si es valido actualizar
        if es_valido:
            rol.nombre = nombre
            rol.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Rol {rol.nombre}"),
                url=url_for("roles.detail", rol_id=rol.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.nombre.data = rol.nombre
    return render_template("roles/edit.jinja2", form=form, rol=rol)


@roles.route("/roles/eliminar/<int:rol_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(rol_id):
    """Eliminar Rol"""
    rol = Rol.query.get_or_404(rol_id)
    if rol.estatus == "A":
        # Dar de baja el rol
        rol.delete()
        # Dar de baja los permisos del rol
        for permiso in rol.permisos:
            permiso.delete()
        # Dar de baja los usuarios del rol
        for usuario_rol in rol.usuarios_roles:
            usuario_rol.delete()
        # Guardar en la bitacora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Rol {rol.nombre}"),
            url=url_for("roles.detail", rol_id=rol.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("roles.detail", rol_id=rol.id))


@roles.route("/roles/recuperar/<int:rol_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(rol_id):
    """Recuperar Rol"""
    rol = Rol.query.get_or_404(rol_id)
    if rol.estatus == "B":
        # Dar de alta el rol
        rol.recover()
        # Dar de alta los permisos del rol
        for permiso in rol.permisos:
            permiso.recover()
        # Dar de alta los usuarios del rol
        for usuario_rol in rol.usuarios_roles:
            usuario_rol.recover()
        # Guardar en la bitacora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Rol {rol.nombre}"),
            url=url_for("roles.detail", rol_id=rol.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("roles.detail", rol_id=rol.id))


@roles.route("/roles/select2_json", methods=["POST"])
def select2_json():
    """Proporcionar el JSON de roles para elegir con un Select2, se usa para filtrar en DataTables"""
    consulta = Rol.query.filter(Rol.estatus == "A")
    if "searchString" in request.form:
        nombre = safe_string(request.form["searchString"], save_enie=True)
        if nombre != "":
            consulta = consulta.filter(Rol.nombre.contains(nombre))
    resultados = []
    for rol in consulta.order_by(Rol.nombre).limit(10).all():
        resultados.append({"id": rol.id, "text": rol.nombre})
    return {"results": resultados, "pagination": {"more": False}}
