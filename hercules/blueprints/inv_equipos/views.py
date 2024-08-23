"""
Inventarios Equipos, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.inv_custodias.models import InvCustodia
from hercules.blueprints.inv_equipos.forms import InvEquipoForm
from hercules.blueprints.inv_equipos.models import InvEquipo
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_ip_address, safe_mac_address, safe_message, safe_string

MODULO = "INV EQUIPOS"

inv_equipos = Blueprint("inv_equipos", __name__, template_folder="templates")


@inv_equipos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@inv_equipos.route("/inv_equipos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de InvEquipo"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = InvEquipo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "inv_equipo_id" in request.form:
        try:
            consulta = consulta.filter_by(id=int(request.form["inv_equipo_id"]))
        except ValueError:
            pass
    else:
        if "inv_custodia_id" in request.form:
            consulta = consulta.filter_by(inv_custodia_id=request.form["inv_custodia_id"])
        if "inv_modelo_id" in request.form:
            consulta = consulta.filter_by(inv_modelo_id=request.form["inv_modelo_id"])
        if "inv_red_id" in request.form:
            consulta = consulta.filter_by(inv_red_id=request.form["inv_red_id"])
        if "numero_serie" in request.form:
            numero_serie = safe_string(request.form["numero_serie"])
            if numero_serie != "":
                consulta = consulta.filter(InvEquipo.numero_serie.contains(numero_serie))
        if "numero_inventario" in request.form:
            numero_inventario = safe_string(request.form["numero_inventario"])
            if numero_inventario != "":
                consulta = consulta.filter(InvEquipo.numero_inventario.contains(numero_inventario))
        if "descripcion" in request.form:
            descripcion = safe_string(request.form["descripcion"])
            if descripcion != "":
                consulta = consulta.filter(InvEquipo.descripcion.contains(descripcion))
        if "tipo" in request.form:
            tipo = safe_string(request.form["tipo"])
            if tipo != "":
                consulta = consulta.filter(InvEquipo.tipo == tipo)
        if "direccion_ip" in request.form:
            direccion_ip = safe_string(request.form["direccion_ip"])
            if direccion_ip != "":
                consulta = consulta.filter(InvEquipo.direccion_ip.contains(direccion_ip))
        if "direccion_mac" in request.form:
            direccion_mac = safe_string(request.form["direccion_mac"])
            if direccion_mac != "":
                consulta = consulta.filter(InvEquipo.direccion_mac.contains(direccion_mac))
    # Ordenar y paginar
    registros = consulta.order_by(InvEquipo.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("inv_equipos.detail", inv_equipo_id=resultado.id),
                },
                "tipo": resultado.tipo,
                "inv_marca_nombre": resultado.inv_modelo.inv_marca.nombre,
                "descripcion": resultado.descripcion,
                "fecha_fabricacion": (
                    resultado.fecha_fabricacion.strftime("%Y-%m-%d") if resultado.fecha_fabricacion is not None else ""
                ),
                "direccion_ip": resultado.direccion_ip,
                "direccion_mac": resultado.direccion_mac,
                "numero_serie": resultado.numero_serie,
                "numero_inventario": resultado.numero_inventario,
                "inv_modelo_descripcion": resultado.inv_modelo.descripcion,
                "inv_red_nombre": resultado.inv_red.nombre,
                "inv_custodia_nombre_completo": resultado.inv_custodia.nombre_completo,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@inv_equipos.route("/inv_equipos")
def list_active():
    """Listado de InvEquipo activos"""
    return render_template(
        "inv_equipos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Equipos",
        estatus="A",
    )


@inv_equipos.route("/inv_equipos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de InvEquipo inactivos"""
    return render_template(
        "inv_equipos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Equipos inactivos",
        estatus="B",
    )


@inv_equipos.route("/inv_equipos/<int:inv_equipo_id>")
def detail(inv_equipo_id):
    """Detalle de un InvEquipo"""
    inv_equipo = InvEquipo.query.get_or_404(inv_equipo_id)
    return render_template("inv_equipos/detail.jinja2", inv_equipo=inv_equipo)


@inv_equipos.route("/inv_equipos/tablero")
@permission_required(MODULO, Permiso.MODIFICAR)
def dashboard():
    """Tablero de InvEquipo"""
    return render_template("inv_equipos/dashboard.jinja2")


@inv_equipos.route("/inv_equipos/nuevo/<int:inv_custodia_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_inv_custodia_id(inv_custodia_id):
    """Nuevo InvEquipo"""
    inv_custodia = InvCustodia.query.get_or_404(inv_custodia_id)
    form = InvEquipoForm()
    if form.validate_on_submit():
        # Guardar
        inv_equipo = InvEquipo(
            inv_custodia_id=inv_custodia.id,
            inv_modelo_id=form.inv_modelo.data,
            descripcion=safe_string(form.descripcion.data, save_enie=True),
            tipo=form.tipo.data,
            fecha_fabricacion=form.fecha_fabricacion.data,
            numero_serie=safe_string(form.numero_serie.data),
            numero_inventario=form.numero_inventario.data,
            inv_red_id=form.inv_red.data,
            direccion_ip=safe_ip_address(form.direccion_ip.data),
            direccion_mac=safe_mac_address(form.direccion_mac.data),
            numero_nodo=form.numero_nodo.data,
            numero_switch=form.numero_switch.data,
            numero_puerto=form.numero_puerto.data,
        )
        inv_equipo.save()
        # Guardar bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo InvEquipo {inv_equipo.descripcion}"),
            url=url_for("inv_equipos.detail", inv_equipo_id=inv_equipo.id),
        )
        bitacora.save()
        # Entregar detalle
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("inv_equipos/new.jinja2", form=form, inv_custodia=inv_custodia)
