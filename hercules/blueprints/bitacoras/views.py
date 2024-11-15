"""
Bitácoras
"""

import json

from flask import Blueprint, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.usuarios.models import Usuario
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_email, safe_string

MODULO = "BITACORAS"

bitacoras = Blueprint("bitacoras", __name__, template_folder="templates")


@bitacoras.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@bitacoras.route("/bitacoras/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Bitacoras"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Bitacora.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Bitacora.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Bitacora.estatus == "A")
    if "modulo_id" in request.form:
        try:
            modulo_id = int(request.form["modulo_id"])
            consulta = consulta.filter(Bitacora.modulo_id == modulo_id)
        except ValueError:
            pass
    if "usuario_id" in request.form:
        try:
            usuario_id = int(request.form["usuario_id"])
            consulta = consulta.filter(Bitacora.usuario_id == usuario_id)
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Bitacora.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "creado": resultado.creado.strftime("%Y-%m-%dT%H:%M:%S"),
                "usuario": {
                    "email": resultado.usuario.email,
                    "url": (
                        url_for("usuarios.detail", usuario_id=resultado.usuario_id) if current_user.can_view("USUARIOS") else ""
                    ),
                },
                "modulo": {
                    "nombre": resultado.modulo.nombre,
                    "url": url_for("modulos.detail", modulo_id=resultado.modulo_id) if current_user.can_view("MODULOS") else "",
                },
                "vinculo": {
                    "descripcion": resultado.descripcion,
                    "url": resultado.url,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@bitacoras.route("/bitacoras")
def list_active():
    """Listado de Bitácoras activas"""
    # Valores por defecto
    filtros = {"estatus": "A"}
    titulo = "Bitácoras"
    # Si viene usuario_id en la URL, agregar a los filtros
    try:
        usuario_id = int(request.args.get("usuario_id"))
        usuario = Usuario.query.get_or_404(usuario_id)
        filtros = {"estatus": "A", "usuario_id": usuario_id}
        titulo = f"Bitácoras de {usuario.nombre}"
    except (TypeError, ValueError):
        pass
    # Entregar
    return render_template(
        "bitacoras/list.jinja2",
        filtros=json.dumps(filtros),
        titulo=titulo,
    )
