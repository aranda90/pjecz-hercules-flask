"""
Exh Exhortos Promoventes, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_promoventes.forms import ExhExhortoPromoventeForm
from hercules.blueprints.exh_exhortos_promoventes.models import ExhExhortoPromovente
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_email, safe_message, safe_string, safe_telefono

MODULO = "EXH EXHORTOS PROMOVENTES"

exh_exhortos_promoventes = Blueprint("exh_exhortos_promoventes", __name__, template_folder="templates")


@exh_exhortos_promoventes.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_promoventes.route("/exh_exhortos_promoventes/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Promoventes"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoPromovente.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_id=request.form["exh_exhorto_id"])
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoPromovente.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "nombre": resultado.nombre_completo,
                    "url": url_for("exh_exhortos_promoventes.detail", exh_exhorto_promovente_id=resultado.id),
                },
                "genero_descripcion": resultado.genero_descripcion,
                "es_persona_moral": resultado.es_persona_moral,
                "tipo_parte_descripcion": resultado.tipo_parte_descripcion,
                "exhorto_origen_id": resultado.exh_exhorto.exhorto_origen_id,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_promoventes.route("/exh_exhortos_promoventes")
def list_active():
    """Listado de Promoventes activos"""
    return render_template(
        "exh_exhortos_promoventes/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos Promoventes",
        estatus="A",
    )


@exh_exhortos_promoventes.route("/exh_exhortos_promoventes/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Promoventes inactivos"""
    return render_template(
        "exh_exhortos_promoventes/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos Promoventes inactivos",
        estatus="B",
    )


@exh_exhortos_promoventes.route("/exh_exhortos_promoventes/<int:exh_exhorto_promovente_id>")
def detail(exh_exhorto_promovente_id):
    """Detalle de un Promovente"""
    exh_exhorto_promovente = ExhExhortoPromovente.query.get_or_404(exh_exhorto_promovente_id)
    return render_template("exh_exhortos_promoventes/detail.jinja2", exh_exhorto_promovente=exh_exhorto_promovente)


@exh_exhortos_promoventes.route("/exh_exhortos_promoventes/nuevo/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto(exh_exhorto_id):
    """Nuevo Promovente"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)

    # Crear formulario
    form = ExhExhortoPromoventeForm()
    if form.validate_on_submit():
        es_valido = True

        # Validar nombre
        nombre = safe_string(form.nombre.data, save_enie=True)
        if not nombre:
            flash("Debe especificar un 'Nombre'", "warning")
            es_valido = False

        # Si es persona moral no se necesitan los apellidos ni el genero
        es_persona_moral = form.es_persona_moral.data == True
        if es_persona_moral is False:
            apellido_paterno = safe_string(form.apellido_paterno.data, save_enie=True)
            apellido_materno = safe_string(form.apellido_materno.data, save_enie=True)
            genero = form.genero.data
        else:
            apellido_paterno = ""
            apellido_materno = ""
            genero = "-"  # No aplica

        # Si tipo_parte es NO DEFINIDO debe venir tipo_parte_nombre
        tipo_parte_nombre = ""
        if form.tipo_parte.data == 0:
            tipo_parte_nombre = safe_string(form.tipo_parte_nombre.data, save_enie=True)
            if not tipo_parte_nombre:
                flash("Debe especificar un 'Tipo Parte Nombre'", "warning")
                es_valido = False

        # Validad correo_electronico
        correo_electronico = ""
        if form.correo_electronico.data:
            try:
                correo_electronico = safe_email(form.correo_electronico.data)
            except ValueError:
                flash("El correo electrónico no es válido", "warning")
                es_valido = False

        # Si es válido, guardar
        if es_valido == True:
            exh_exhorto_promovente = ExhExhortoPromovente(
                exh_exhorto=exh_exhorto,
                nombre=nombre,
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno,
                genero=genero,
                es_persona_moral=es_persona_moral,
                tipo_parte=form.tipo_parte.data,
                tipo_parte_nombre=tipo_parte_nombre,
                correo_electronico=correo_electronico,
                telefono=safe_telefono(form.telefono.data),
            )
            exh_exhorto_promovente.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nueva Parte {exh_exhorto_promovente.nombre_completo}"),
                url=url_for("exh_exhortos_promoventes.detail", exh_exhorto_promovente_id=exh_exhorto_promovente.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))

    # Entregar formulario
    return render_template("exh_exhortos_promoventes/new_with_exh_exhorto.jinja2", form=form, exh_exhorto=exh_exhorto)


@exh_exhortos_promoventes.route("/exh_exhortos_promoventes/edicion/<int:exh_exhorto_promovente_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_promovente_id):
    """Editar Promovente"""
    exh_exhorto_promovente = ExhExhortoPromovente.query.get_or_404(exh_exhorto_promovente_id)

    # Si el estado del exhorto NO es PENDIENTE, no se puede editar
    if exh_exhorto_promovente.exh_exhorto.estado != "PENDIENTE":
        flash("No se puede editar porque el estado del exhorto no es PENDIENTE.", "warning")
        return redirect(url_for("exh_exhortos_promoventes.detail", exh_exhorto_promovente_id=exh_exhorto_promovente_id))

    # Crear formulario
    form = ExhExhortoPromoventeForm()
    if form.validate_on_submit():
        es_valido = True

        # Validar nombre
        nombre = safe_string(form.nombre.data, save_enie=True)
        if not nombre:
            flash("Debe especificar un 'Nombre'", "warning")
            es_valido = False

        # Si es persona moral no se necesitan los apellidos ni el genero
        es_persona_moral = form.es_persona_moral.data == True
        if es_persona_moral is False:
            apellido_paterno = safe_string(form.apellido_paterno.data, save_enie=True)
            apellido_materno = safe_string(form.apellido_materno.data, save_enie=True)
            genero = form.genero.data
        else:
            apellido_paterno = ""
            apellido_materno = ""
            genero = "-"  # No aplica

        # Si tipo_parte es NO DEFINIDO debe venir tipo_parte_nombre
        tipo_parte_nombre = ""
        if form.tipo_parte.data == 0:
            tipo_parte_nombre = safe_string(form.tipo_parte_nombre.data, save_enie=True)
            if not tipo_parte_nombre:
                flash("Debe especificar un 'Tipo Parte Nombre'", "warning")
                es_valido = False

        # Validad correo_electronico
        correo_electronico = ""
        if form.correo_electronico.data:
            try:
                correo_electronico = safe_email(form.correo_electronico.data)
            except ValueError:
                flash("El correo electrónico no es válido", "warning")
                es_valido = False

        # Si es válido, guardar
        if es_valido is True:
            exh_exhorto_promovente.nombre = nombre
            exh_exhorto_promovente.apellido_paterno = apellido_paterno
            exh_exhorto_promovente.apellido_materno = apellido_materno
            exh_exhorto_promovente.genero = genero
            exh_exhorto_promovente.es_persona_moral = es_persona_moral
            exh_exhorto_promovente.tipo_parte = form.tipo_parte.data
            exh_exhorto_promovente.tipo_parte_nombre = tipo_parte_nombre
            exh_exhorto_promovente.correo_electronico = correo_electronico
            exh_exhorto_promovente.telefono = safe_telefono(form.telefono.data)
            exh_exhorto_promovente.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Parte {exh_exhorto_promovente.nombre_completo}"),
                url=url_for("exh_exhortos_promoventes.detail", exh_exhorto_promovente_id=exh_exhorto_promovente.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto_promovente.exh_exhorto.id))

    # Definir los valores del formulario
    form.nombre.data = exh_exhorto_promovente.nombre
    form.apellido_paterno.data = exh_exhorto_promovente.apellido_paterno
    form.apellido_materno.data = exh_exhorto_promovente.apellido_materno
    form.genero.data = exh_exhorto_promovente.genero
    form.es_persona_moral.data = exh_exhorto_promovente.es_persona_moral
    form.tipo_parte.data = exh_exhorto_promovente.tipo_parte
    form.tipo_parte_nombre.data = exh_exhorto_promovente.tipo_parte_nombre
    form.correo_electronico.data = exh_exhorto_promovente.correo_electronico
    form.telefono.data = exh_exhorto_promovente.telefono

    # Entregar el formulario
    return render_template("exh_exhortos_promoventes/edit.jinja2", form=form, exh_exhorto_promovente=exh_exhorto_promovente)


@exh_exhortos_promoventes.route("/exh_exhortos_promoventes/eliminar/<int:exh_exhorto_promovente_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_promovente_id):
    """Eliminar Promovente"""
    exh_exhorto_promovente = ExhExhortoPromovente.query.get_or_404(exh_exhorto_promovente_id)
    if exh_exhorto_promovente.estatus == "A":
        exh_exhorto_promovente.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Promovente {exh_exhorto_promovente.nombre_completo}"),
            url=url_for("exh_exhortos_promoventes.detail", exh_exhorto_promovente_id=exh_exhorto_promovente.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto_promovente.exh_exhorto.id))
    return redirect(url_for("exh_exhortos_promoventes.detail", exh_exhorto_promovente_id=exh_exhorto_promovente.id))


@exh_exhortos_promoventes.route("/exh_exhortos_promoventes/recuperar/<int:exh_exhorto_promovente_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_promovente_id):
    """Recuperar Promovente"""
    exh_exhorto_promovente = ExhExhortoPromovente.query.get_or_404(exh_exhorto_promovente_id)
    if exh_exhorto_promovente.estatus == "B":
        exh_exhorto_promovente.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Promovente {exh_exhorto_promovente.nombre_completo}"),
            url=url_for("exh_exhortos_promoventes.detail", exh_exhorto_promovente_id=exh_exhorto_promovente.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto_promovente.exh_exhorto.id))
    return redirect(url_for("exh_exhortos_promoventes.detail", exh_exhorto_promovente_id=exh_exhorto_promovente.id))
