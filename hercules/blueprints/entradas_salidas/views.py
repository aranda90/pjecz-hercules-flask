"""
Entradas-Salidas
"""

import json

from flask import Blueprint, render_template, request, url_for
from flask_login import login_required

from hercules.blueprints.entradas_salidas.models import EntradaSalida
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.usuarios.models import Usuario
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_email

MODULO = "ENTRADAS SALIDAS"

entradas_salidas = Blueprint("entradas_salidas", __name__, template_folder="templates")


@entradas_salidas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@entradas_salidas.route("/entradas_salidas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Entradas-Salidas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = EntradaSalida.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "usuario_id" in request.form:
        try:
            usuario_id = int(request.form["usuario_id"])
            consulta = consulta.filter_by(usuario_id=usuario_id)
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(EntradaSalida.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "creado": resultado.creado.strftime("%Y-%m-%dT%H:%M:%S"),
                "tipo": resultado.tipo,
                "usuario": {
                    "email": resultado.usuario.email,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario_id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@entradas_salidas.route("/entradas_salidas")
def list_active():
    """Listado de Entradas-Salidas activos"""

    # Definir filtros por defecto
    filtros = {"estatus": "A"}
    titulo = "Entradas-Salidas"

    # Si viene usuario_id en la URL, agregar a los filtros
    try:
        usuario_id = int(request.args.get("usuario_id"))
        usuario = Usuario.query.get_or_404(usuario_id)
        filtros = {"estatus": "A", "usuario_id": usuario_id}
        titulo = f"Entradas-Salidas de {usuario.nombre}"
    except (TypeError, ValueError):
        pass

    # Entregar
    return render_template(
        "entradas_salidas/list.jinja2",
        filtros=json.dumps(filtros),
        titulo=titulo,
    )
