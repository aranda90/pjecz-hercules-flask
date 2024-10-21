"""
Funcionarios, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.centros_trabajos.models import CentroTrabajo
from hercules.blueprints.funcionarios.forms import FuncionarioAdminForm, FuncionarioDomicilioForm, FuncionarioEditForm
from hercules.blueprints.funcionarios.models import Funcionario
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_curp, safe_email, safe_message, safe_string

MODULO = "FUNCIONARIOS"

funcionarios = Blueprint("funcionarios", __name__, template_folder="templates")


@funcionarios.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@funcionarios.route("/funcionarios/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Funcionarios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Funcionario.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Funcionario.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Funcionario.estatus == "A")
    if "centro_trabajo_id" in request.form:
        consulta = consulta.filter(Funcionario.centro_trabajo_id == request.form["centro_trabajo_id"])
    if "email" in request.form:
        try:
            email = safe_email(request.form["email"], search_fragment=True)
            if email != "":
                consulta = consulta.filter(Funcionario.email.contains(email))
        except ValueError:
            pass
    if "nombres" in request.form:
        nombres = safe_string(request.form["nombres"], save_enie=True)
        if nombres != "":
            consulta = consulta.filter(Funcionario.nombres.contains(nombres))
    if "apellido_paterno" in request.form:
        apellido_paterno = safe_string(request.form["apellido_paterno"], save_enie=True)
        if apellido_paterno != "":
            consulta = consulta.filter(Funcionario.apellido_paterno.contains(apellido_paterno))
    if "puesto" in request.form:
        puesto = safe_string(request.form["puesto"])
        if puesto != "":
            consulta = consulta.filter(Funcionario.puesto.contains(puesto))
    if "en_funciones" in request.form and request.form["en_funciones"] == "true":
        consulta = consulta.filter(Funcionario.en_funciones is True)
    if "en_sentencias" in request.form and request.form["en_sentencias"] == "true":
        consulta = consulta.filter(Funcionario.en_sentencias is True)
    if "en_soportes" in request.form and request.form["en_soportes"] == "true":
        consulta = consulta.filter(Funcionario.en_soportes is True)
    if "en_tesis_jurisprudencias" in request.form and request.form["en_tesis_jurisprudencias"] == "true":
        consulta = consulta.filter(Funcionario.en_tesis_jurisprudencias is True)
    # Ordenar y paginar
    registros = consulta.order_by(Funcionario.email).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "email": resultado.email,
                    "url": url_for("funcionarios.detail", funcionario_id=resultado.id),
                },
                "curp": resultado.curp[:4] + "************",
                "nombre": resultado.nombre,
                "puesto": resultado.puesto,
                "centro_trabajo_clave": resultado.centro_trabajo.clave,
                "centro_trabajo_nombre": resultado.centro_trabajo.nombre,
                "telefono": resultado.telefono,
                "extension": resultado.extension,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@funcionarios.route("/funcionarios")
def list_active():
    """Listado de Funcionarios activos"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Directorio",
        estatus="A",
    )


@funcionarios.route("/funcionarios/en_funciones")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_active_en_funciones():
    """Listado de Funcionarios activos y en funciones"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A", "en_funciones": True}),
        titulo="Directorio (en funciones)",
        estatus="A",
        current_page="en_funciones",
    )


@funcionarios.route("/funcionarios/en_sentencias")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_active_en_sentencias():
    """Listado de Funcionarios activos y en sentencias"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A", "en_sentencias": True}),
        titulo="Directorio (en sentencias)",
        estatus="A",
        current_page="en_sentencias",
    )


@funcionarios.route("/funcionarios/en_soportes")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_active_en_soportes():
    """Listado de Funcionarios activos y en soportes"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A", "en_soportes": True}),
        titulo="Directorio (en soportes)",
        estatus="A",
        current_page="en_soportes",
    )


@funcionarios.route("/funcionarios/en_tesis_jurisprudencias")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_active_en_tesis_jurisprudencias():
    """Listado de Funcionarios activos y en tesis y jurisprudencias"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "A", "en_tesis_jurisprudencias": True}),
        titulo="Directorio (en tesis y jurisprudencias)",
        estatus="A",
        current_page="en_tesis_jurisprudencias",
    )


@funcionarios.route("/funcionarios/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Funcionarios inactivos"""
    return render_template(
        "funcionarios/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Funcionarios inactivos",
        estatus="B",
    )


@funcionarios.route("/funcionarios/<int:funcionario_id>")
def detail(funcionario_id):
    """Detalle de un Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    return render_template("funcionarios/detail.jinja2", funcionario=funcionario)


@funcionarios.route("/funcionarios/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def new():
    """Nuevo Funcionario"""
    form = FuncionarioAdminForm()
    if form.validate_on_submit():
        es_valido = True
        # Validar que el CURP no se repita
        curp = safe_string(form.curp.data)
        if Funcionario.query.filter_by(curp=curp).first():
            flash("La CURP ya está en uso. Debe de ser única.", "warning")
            es_valido = False
        # Validar que el e-mail no se repita
        email = safe_email(form.email.data)
        if Funcionario.query.filter_by(email=email).first():
            flash("El e-mail ya está en uso. Debe de ser único.", "warning")
            es_valido = False
        if es_valido:
            funcionario = Funcionario(
                nombres=safe_string(form.nombres.data),
                apellido_paterno=safe_string(form.apellido_paterno.data),
                apellido_materno=safe_string(form.apellido_materno.data),
                curp=curp,
                email=email,
                puesto=safe_string(form.puesto.data),
                telefono=safe_string(form.telefono.data),
                extension=safe_string(form.extension.data),
                en_funciones=form.en_funciones.data,
                en_sentencias=form.en_sentencias.data,
                en_soportes=form.en_soportes.data,
                en_tesis_jurisprudencias=form.en_tesis_jurisprudencias.data,
                centro_trabajo_id=form.centro_trabajo.data,
                ingreso_fecha=form.ingreso_fecha.data,
            )
            funcionario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo funcionario {funcionario.nombre}"),
                url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    centro_trabajo_no_definido = CentroTrabajo.query.filter_by(nombre="NO DEFINIDO").first()
    if centro_trabajo_no_definido is not None:
        form.centro_trabajo.data = centro_trabajo_no_definido
    return render_template("funcionarios/new.jinja2", form=form)


@funcionarios.route("/funcionarios/edicion/<int:funcionario_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(funcionario_id):
    """Editar Funcionario para administrador"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    form = FuncionarioAdminForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia el CURP verificar que no este en uso
        curp = safe_string(form.curp.data)
        if funcionario.curp != curp:
            funcionario_existente = Funcionario.query.filter_by(curp=curp).first()
            if funcionario_existente and funcionario_existente.id != funcionario.id:
                es_valido = False
                flash("El CURP ya está en uso. Debe de ser único.", "warning")
        # Si cambia el e-mail verificar que no este en uso
        email = safe_email(form.email.data)
        if funcionario.email != email:
            funcionario_existente = Funcionario.query.filter_by(email=email).first()
            if funcionario_existente and funcionario_existente.id != funcionario.id:
                es_valido = False
                flash("La e-mail ya está en uso. Debe de ser único.", "warning")
        # Si es valido actualizar
        if es_valido:
            funcionario.nombres = safe_string(form.nombres.data)
            funcionario.apellido_paterno = safe_string(form.apellido_paterno.data)
            funcionario.apellido_materno = safe_string(form.apellido_materno.data)
            funcionario.curp = curp
            funcionario.email = email
            funcionario.puesto = safe_string(form.puesto.data)
            funcionario.telefono = safe_string(form.telefono.data)
            funcionario.extension = safe_string(form.extension.data)
            funcionario.en_funciones = form.en_funciones.data
            funcionario.en_sentencias = form.en_sentencias.data
            funcionario.en_soportes = form.en_soportes.data
            funcionario.en_tesis_jurisprudencias = form.en_tesis_jurisprudencias.data
            funcionario.centro_trabajo_id = form.centro_trabajo.data
            funcionario.ingreso_fecha = form.ingreso_fecha.data
            funcionario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado funcionario {funcionario.nombre}"),
                url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.nombres.data = funcionario.nombres
    form.apellido_paterno.data = funcionario.apellido_paterno
    form.apellido_materno.data = funcionario.apellido_materno
    form.curp.data = funcionario.curp
    form.email.data = funcionario.email
    form.puesto.data = funcionario.puesto
    form.telefono.data = funcionario.telefono
    form.extension.data = funcionario.extension
    form.en_funciones.data = funcionario.en_funciones
    form.en_sentencias.data = funcionario.en_sentencias
    form.en_soportes.data = funcionario.en_soportes
    form.en_tesis_jurisprudencias.data = funcionario.en_tesis_jurisprudencias
    form.centro_trabajo.data = funcionario.centro_trabajo
    form.ingreso_fecha.data = funcionario.ingreso_fecha
    return render_template("funcionarios/edit.jinja2", form=form, funcionario=funcionario)


@funcionarios.route("/funcionarios/eliminar/<int:funcionario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(funcionario_id):
    """Eliminar Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    if funcionario.estatus == "A":
        funcionario.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Funcionario {funcionario.nombre}"),
            url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))


@funcionarios.route("/funcionarios/recuperar/<int:funcionario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(funcionario_id):
    """Recuperar Funcionario"""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    if funcionario.estatus == "B":
        funcionario.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Funcionario {funcionario.nombre}"),
            url=url_for("funcionarios.detail", funcionario_id=funcionario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))


@funcionarios.route("/funcionarios/limpiar_oficinas/<int:funcionario_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def clean(funcionario_id):
    """Limpiar funcionarios_oficinas"""
    # Validar el funcionario
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    # Salir si hay una tarea en el fondo
    if current_user.get_task_in_progress("funcionarios.tasks.limpiar_oficinas"):
        flash("Debe esperar porque hay una tarea en el fondo sin terminar.", "warning")
    else:
        # Lanzar tarea en el fondo
        current_user.launch_task(
            comando="funcionarios.tasks.limpiar_oficinas",
            mensaje=f"Limpiar oficinas del funcionario {funcionario.curp}",
            funcionario_id=funcionario.id,
        )
        flash("Se están limpiando las oficinas de este funcionario.. Esta página se va a recargar en 30 segundos...", "info")
    # Mostrar detalle del funcionario
    return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))


@funcionarios.route("/funcionarios/asignar_oficinas/<int:funcionario_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def insert_offices(funcionario_id):
    """Asignar funcionarios_oficinas a partir de una direccion"""
    # Validar el funcionario
    funcionario = Funcionario.query.get_or_404(funcionario_id)

    # Verificar si hay una tarea en progreso con el mismo nombre
    task_name = "funcionarios.tasks.asignar_oficina"

    # Salir si hay una tarea en el fondo
    if current_user.get_task_in_progress(task_name):
        flash("Debe esperar porque hay una tarea en el fondo sin terminar.", "warning")
        return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))
    # Si viene el formulario con el domicilio
    form = FuncionarioDomicilioForm()
    if form.validate_on_submit():
        # Lanzar tarea en el fondo
        current_user.launch_task(
            comando="funcionarios.tasks.asignar_oficinas",
            mensaje=f"Asignar oficinas para el funcionario {funcionario.curp}",
            funcionario_id=funcionario.id,
            domicilio_id=form.domicilio.data,
        )
        flash("Se están asignando las oficinas para este funcionario. Esta página se va a recargar en 30 segundos...", "info")
        return redirect(url_for("funcionarios.detail", funcionario_id=funcionario.id))
    # Mostrar el formulario para solicitar el domicilio
    form.funcionario_nombre.data = funcionario.nombre  # Read only
    form.funcionario_puesto.data = funcionario.puesto  # Read only
    form.funcionario_email.data = funcionario.email  # Read only
    return render_template("funcionarios/insert_offices.jinja2", form=form, funcionario=funcionario)
