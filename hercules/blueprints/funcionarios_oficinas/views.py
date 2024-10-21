"""
Funcionarios Oficnas, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.funcionarios.models import Funcionario
from hercules.blueprints.funcionarios_oficinas.forms import FuncionarioOficinaForm
from hercules.blueprints.funcionarios_oficinas.models import FuncionarioOficina
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.oficinas.models import Oficina
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "FUNCIONARIOS OFICINAS"

funcionarios_oficinas = Blueprint("funcionarios_oficinas", __name__, template_folder="templates")


@funcionarios_oficinas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@funcionarios_oficinas.route("/funcionarios_oficinas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Funcionarios Oficinas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = FuncionarioOficina.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "funcionario_id" in request.form:
        funcionario = Funcionario.query.get(request.form["funcionario_id"])
        if funcionario:
            consulta = consulta.filter(FuncionarioOficina.funcionario == funcionario)
    # Luego filtrar por columnas de otras tablas
    if "funcionario_nombre" in request.form:
        funcionario_nombre = safe_string(request.form["funcionario_nombre"], save_enie=True)
        if funcionario_nombre != "":
            consulta = consulta.join(Funcionario).filter(Funcionario.nombres.contains(funcionario_nombre))
    if "oficina_id" in request.form:
        oficina = Oficina.query.get(request.form["oficina_id"])
        if oficina:
            consulta = consulta.filter(FuncionarioOficina.oficina_id == oficina.id)
    if "oficina_clave" in request.form:
        try:
            oficina_clave = safe_clave(request.form["oficina_clave"])
            if oficina_clave != "":
                consulta = consulta.join(Oficina).filter(Oficina.clave.contains(oficina_clave))
                print(str(consulta))
        except ValueError:
            pass
    if "oficina_descripcion" in request.form:
        oficina_descripcion = safe_string(request.form["oficina_descripcion"], save_enie=True)
        if oficina_descripcion != "":
            consulta = consulta.join(Oficina).filter(Oficina.descripcion_corta.contains(oficina_descripcion))
            print(consulta)
    # Ordenar y paginar
    registros = consulta.order_by(FuncionarioOficina.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("funcionarios_oficinas.detail", funcionario_oficina_id=resultado.id),
                },
                "funcionario": {
                    "curp": resultado.funcionario.curp,
                    "url": (
                        url_for("funcionarios.detail", funcionario_id=resultado.funcionario.id)
                        if current_user.can_view("FUNCIONARIOS")
                        else ""
                    ),
                },
                "funcionario_nombre": resultado.funcionario.nombre,
                "oficina": {
                    "clave": resultado.oficina.clave,
                    "url": (
                        url_for("oficinas.detail", oficina_id=resultado.oficina.id) if current_user.can_view("OFICINAS") else ""
                    ),
                },
                "oficina_descripcion_corta": resultado.oficina.descripcion_corta,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@funcionarios_oficinas.route("/funcionarios_oficinas")
def list_active():
    """Listado de Funcionarios Oficinas activos"""
    return render_template(
        "funcionarios_oficinas/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Funcionarios Oficinas",
        estatus="A",
    )


@funcionarios_oficinas.route("/funcionarios_oficinas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Funcionarios Oficinas inactivos"""
    return render_template(
        "funcionarios_oficinas/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Funcionarios Oficinas inactivos",
        estatus="B",
    )


@funcionarios_oficinas.route("/funcionarios_oficinas/<int:funcionario_oficina_id>")
def detail(funcionario_oficina_id):
    """Detalle de un Funcionario Oficina"""
    funcionario_oficina = FuncionarioOficina.query.get_or_404(funcionario_oficina_id)
    return render_template("funcionarios_oficinas/detail.jinja2", funcionario_oficina=funcionario_oficina)


@funcionarios_oficinas.route("/funcionarios_oficinas/nuevo_con_funcionario/<int:funcionario_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_funcionario(funcionario_id):
    """Nuevo Funcionario Oficina"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    form = FuncionarioOficinaForm()
    if form.validate_on_submit():
        oficina_id = form.oficina.data
        oficina = Oficina.query.get(oficina_id)
        if oficina is None:
            flash("Oficina no encontrada", "error")
            return redirect(url_for("funcionarios_oficinas.new_with_funcionario", funcionario_id=funcionario_id))
        descripcion = f"Funcionario {funcionario.curp} en {oficina.clave}"
        if (
            FuncionarioOficina.query.filter(FuncionarioOficina.funcionario == funcionario)
            .filter(FuncionarioOficina.oficina == oficina)
            .first()
            is not None
        ):
            flash(f"CONFLICTO: Ya existe {descripcion}. Si está eliminado puede recuperarlo.", "warning")
            return redirect(url_for("funcionarios_oficinas.list_inactive"))
        funcionario_oficina = FuncionarioOficina(
            funcionario=funcionario,
            oficina=oficina,
            descripcion=descripcion,
        )
        funcionario_oficina.save()
        flash(f"Nuevo {descripcion}", "success")
        return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))
    form.funcionario.data = funcionario.nombre
    return render_template(
        "funcionarios_oficinas/new_with_funcionario.jinja2",
        form=form,
        funcionario=funcionario,
        titulo=f"Agregar oficina al funcionario {funcionario.nombre}",
    )


@funcionarios_oficinas.route("/funcionarios_oficinas/eliminar/<int:funcionario_oficina_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(funcionario_oficina_id):
    """Eliminar Funcionario-Oficina"""
    funcionario_oficina = FuncionarioOficina.query.get_or_404(funcionario_oficina_id)
    if funcionario_oficina.estatus == "A":
        funcionario_oficina.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Funcionario-Oficina {funcionario_oficina.descripcion}"),
            url=url_for("funcionarios_oficinas.detail", funcionario_oficina_id=funcionario_oficina.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("funcionarios_oficinas.detail", funcionario_oficina_id=funcionario_oficina.id))


@funcionarios_oficinas.route("/funcionarios_oficinas/recuperar/<int:funcionario_oficina_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(funcionario_oficina_id):
    """Recuperar Funcionario-Oficina"""
    funcionario_oficina = FuncionarioOficina.query.get_or_404(funcionario_oficina_id)
    if funcionario_oficina.estatus == "B":
        funcionario_oficina.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Funcionario-Oficina {funcionario_oficina.descripcion}"),
            url=url_for("funcionarios_oficinas.detail", funcionario_oficina_id=funcionario_oficina.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("funcionarios_oficinas.detail", funcionario_oficina_id=funcionario_oficina.id))
