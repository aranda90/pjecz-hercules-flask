"""
Exh Exhortos Partes, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_partes.forms import ExhExhortoParteForm
from hercules.blueprints.exh_exhortos_partes.models import ExhExhortoParte
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string

MODULO = "EXH EXHORTOS PARTES"

exh_exhortos_partes = Blueprint("exh_exhortos_partes", __name__, template_folder="templates")


@exh_exhortos_partes.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_partes.route("/exh_exhortos_partes/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Partes"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoParte.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_id=request.form["exh_exhorto_id"])
    # if "columna_clave" in request.form:
    #     try:
    #         columna_clave = safe_clave(request.form["columna_clave"])
    #         if clave != "":
    #             consulta = consulta.filter(ExhExhortoParte.clave.contains(columna_clave))
    #     except ValueError:
    #         pass
    # if "columna_descripcion" in request.form:
    #     columna_descripcion = safe_string(request.form["columna_descripcion"], save_enie=True)
    #     if columna_descripcion != "":
    #         consulta = consulta.filter(ExhExhortoParte.descripcion.contains(columna_descripcion))
    # Luego filtrar por columnas de otras tablas
    # if "otra_columna_descripcion" in request.form:
    #     otra_columna_descripcion = safe_string(request.form["otra_columna_descripcion"], save_enie=True)
    #     consulta = consulta.join(OtroModelo)
    #     consulta = consulta.filter(OtroModelo.rfc.contains(otra_columna_descripcion))
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoParte.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        # Quitar genero si es persona moral
        genero_str = resultado.genero
        if resultado.es_persona_moral == True:
            genero_str = "-"
        # Si tipo_parte es NO DEFINIDO se remplaza por el tipo_parte_nombre
        tipo_parte_str = resultado.tipo_parte
        if tipo_parte_str == 0:
            tipo_parte_str = resultado.tipo_parte_nombre
        elif tipo_parte_str == 1:
            tipo_parte_str = "ACTOR"
        elif tipo_parte_str == 2:
            tipo_parte_str = "DEMANDADO"
        else:
            tipo_parte_str = "-"
        # Añadir registro al listado
        data.append(
            {
                "detalle": {
                    "url": url_for("exh_exhortos_partes.detail", exh_exhorto_parte_id=resultado.id),
                    "nombre": resultado.nombre_completo,
                },
                "nombre": resultado.nombre,
                "apellido_paterno": resultado.apellido_paterno,
                "apellido_materno": resultado.apellido_materno,
                "genero": genero_str,
                "es_persona_moral": resultado.es_persona_moral,
                "tipo_parte": tipo_parte_str,
                "tipo_parte_nombre": resultado.tipo_parte_nombre,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_partes.route("/exh_exhortos_partes")
def list_active():
    """Listado de Partes activos"""
    return render_template(
        "exh_exhortos_partes/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos Partes",
        estatus="A",
    )


@exh_exhortos_partes.route("/exh_exhortos_partes/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Partes inactivos"""
    return render_template(
        "exh_exhortos_partes/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos Partes inactivos",
        estatus="B",
    )


@exh_exhortos_partes.route("/exh_exhortos_partes/nuevo_con_exhorto/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto(exh_exhorto_id):
    """Nueva Parte"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    form = ExhExhortoParteForm()
    if form.validate_on_submit():
        # Si es persona moral no se necesitan los apellidos ni el genero
        es_persona_moral = True
        apellido_paterno = None
        apellido_materno = None
        genero = "M"
        if form.es_persona_moral.data == False:
            es_persona_moral = False
            apellido_paterno = safe_string(form.apellido_paterno.data)
            apellido_materno = safe_string(form.apellido_materno.data)
            genero = safe_string(form.genero.data)
        # Si tipo_parte es NO DEFINIDO pedir un nombre para el tipo_parte_nombre
        pedir_tipo_parte_nombre = False
        tipo_parte_nombre = ""
        if form.tipo_parte.data == 0:
            pedir_tipo_parte_nombre = True
            tipo_parte_nombre = safe_string(form.tipo_parte_nombre.data)
        # Validación de campos necesarios
        if pedir_tipo_parte_nombre == True and tipo_parte_nombre == "":
            flash("Debe especificar un 'Tipo Parte Nombre'", "warning")
        else:
            exh_exhorto_parte = ExhExhortoParte(
                exh_exhorto=exh_exhorto,
                es_persona_moral=es_persona_moral,
                nombre=safe_string(form.nombre.data),
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno,
                genero=genero,
                tipo_parte=form.tipo_parte.data,
                tipo_parte_nombre=tipo_parte_nombre,
            )
            exh_exhorto_parte.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nueva Parte {exh_exhorto_parte.nombre}"),
                url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    return render_template("exh_exhortos_partes/new_with_exh_exhorto.jinja2", form=form, exh_exhorto=exh_exhorto)


@exh_exhortos_partes.route("/exh_exhortos_partes/<int:exh_exhorto_parte_id>")
def detail(exh_exhorto_parte_id):
    """Detalle de un Parte"""
    exh_exhorto_parte = ExhExhortoParte.query.get_or_404(exh_exhorto_parte_id)
    return render_template("exh_exhortos_partes/detail.jinja2", exh_exhorto_parte=exh_exhorto_parte)


@exh_exhortos_partes.route("/exh_exhortos_partes/edicion/<int:exh_exhorto_parte_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_parte_id):
    """Editar Parte"""
    exh_exhorto_parte = ExhExhortoParte.query.get_or_404(exh_exhorto_parte_id)
    form = ExhExhortoParteForm()
    if form.validate_on_submit():
        # Si es persona moral no se necesita definir apellidos o genero
        es_persona_moral = form.es_persona_moral.data
        if es_persona_moral == True:
            exh_exhorto_parte.nombre = safe_string(form.nombre.data)
            exh_exhorto_parte.apellido_paterno = None
            exh_exhorto_parte.apellido_materno = None
        else:
            exh_exhorto_parte.nombre = safe_string(form.nombre.data)
            exh_exhorto_parte.apellido_paterno = safe_string(form.apellido_paterno.data)
            exh_exhorto_parte.apellido_materno = safe_string(form.apellido_materno.data)
        exh_exhorto_parte.es_persona_moral = es_persona_moral
        exh_exhorto_parte.genero = safe_string(form.genero.data)
        # Si tipo_parte es NO DEFINIDO pedir un nombre para el tipo_parte_nombre
        pedir_tipo_parte_nombre = False
        tipo_parte_nombre = ""
        if form.tipo_parte.data == 0:
            pedir_tipo_parte_nombre = True
            tipo_parte_nombre = safe_string(form.tipo_parte_nombre.data)
        else:
            tipo_parte_nombre = None
        # Validación de campos necesarios
        if pedir_tipo_parte_nombre == True and tipo_parte_nombre == "":
            flash("Debe especificar un 'Tipo Parte Nombre'", "warning")
        else:
            exh_exhorto_parte.tipo_parte = form.tipo_parte.data
            exh_exhorto_parte.tipo_parte_nombre = tipo_parte_nombre
            exh_exhorto_parte.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Parte {exh_exhorto_parte.nombre}"),
                url=url_for("exh_exhortos_partes.detail", exh_exhorto_parte_id=exh_exhorto_parte.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.nombre.data = exh_exhorto_parte.nombre
    form.apellido_paterno.data = exh_exhorto_parte.apellido_paterno
    form.apellido_materno.data = exh_exhorto_parte.apellido_materno
    form.es_persona_moral.data = exh_exhorto_parte.es_persona_moral
    form.genero.data = exh_exhorto_parte.genero
    form.tipo_parte.data = exh_exhorto_parte.tipo_parte
    form.tipo_parte_nombre.data = exh_exhorto_parte.tipo_parte_nombre
    return render_template("exh_exhortos_partes/edit.jinja2", form=form, exh_exhorto_parte=exh_exhorto_parte)


@exh_exhortos_partes.route("/exh_exhortos_partes/eliminar/<int:exh_exhorto_parte_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_parte_id):
    """Eliminar Parte"""
    exh_exhorto_parte = ExhExhortoParte.query.get_or_404(exh_exhorto_parte_id)
    if exh_exhorto_parte.estatus == "A":
        exh_exhorto_parte.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Parte {exh_exhorto_parte.nombre_completo}"),
            url=url_for("exh_exhortos_partes.detail", exh_exhorto_parte_id=exh_exhorto_parte.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_partes.detail", exh_exhorto_parte_id=exh_exhorto_parte.id))


@exh_exhortos_partes.route("/exh_exhortos_partes/recuperar/<int:exh_exhorto_parte_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_parte_id):
    """Recuperar Parte"""
    exh_exhorto_parte = ExhExhortoParte.query.get_or_404(exh_exhorto_parte_id)
    if exh_exhorto_parte.estatus == "B":
        exh_exhorto_parte.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Parte {exh_exhorto_parte.nombre_completo}"),
            url=url_for("exh_exhortos_partes.detail", exh_exhorto_parte_id=exh_exhorto_parte.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_partes.detail", exh_exhorto_parte_id=exh_exhorto_parte.id))
