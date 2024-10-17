"""
Autoridades, vistas
"""

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.autoridades.forms import AutoridadEditForm, AutoridadNewForm
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.distritos.models import Distrito
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_message, safe_string

MODULO = "AUTORIDADES"

autoridades = Blueprint("autoridades", __name__, template_folder="templates")


@autoridades.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@autoridades.route("/autoridades/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Autoridades"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Autoridad.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Autoridad.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Autoridad.estatus == "A")
    if "distrito_id" in request.form:
        consulta = consulta.filter(Autoridad.distrito_id == request.form["distrito_id"])
    if "materia_id" in request.form:
        consulta = consulta.filter(Autoridad.materia_id == request.form["materia_id"])
    if "municipio_id" in request.form:
        consulta = consulta.filter(Autoridad.municipio_id == request.form["municipio_id"])
    if "clave" in request.form:
        try:
            clave = safe_clave(request.form["clave"])
            if clave != "":
                consulta = consulta.filter(Autoridad.clave.contains(clave))
        except ValueError:
            pass
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Autoridad.descripcion.contains(descripcion))
    # Luego filtrar por columnas de otras tablas
    if "distrito_nombre" in request.form:
        distrito_nombre = safe_string(request.form["distrito_nombre"], save_enie=True)
        if distrito_nombre != "":
            consulta = consulta.join(Distrito).filter(Distrito.nombre.contains(distrito_nombre))
    # Ordenar y paginar
    registros = consulta.order_by(Autoridad.clave).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "clave": resultado.clave,
                    "url": url_for("autoridades.detail", autoridad_id=resultado.id),
                },
                "descripcion_corta": resultado.descripcion_corta,
                "distrito": {
                    "nombre_corto": resultado.distrito.nombre_corto,
                    "url": (
                        url_for("distritos.detail", distrito_id=resultado.distrito_id)
                        if current_user.can_view("DISTRITOS")
                        else ""
                    ),
                },
                "municipio": {
                    "nombre": f"{resultado.municipio.clave} {resultado.municipio.nombre}",
                    "url": (
                        url_for("municipios.detail", municipio_id=resultado.municipio_id)
                        if current_user.can_view("MUNICIPIOS")
                        else ""
                    ),
                },
                "es_extinto": "EXTINTO" if resultado.es_extinto else "",
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@autoridades.route("/autoridades")
def list_active():
    """Listado de Autoridades activas"""
    return render_template(
        "autoridades/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Autoridades",
        estatus="A",
    )


@autoridades.route("/autoridades/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Autoridades inactivas"""
    return render_template(
        "autoridades/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Autoridades inactivas",
        estatus="B",
    )


@autoridades.route("/autoridades/<int:autoridad_id>")
def detail(autoridad_id):
    """Detalle de una Autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    return render_template("autoridades/detail.jinja2", autoridad=autoridad)


@autoridades.route("/autoridades/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva Autoridad"""
    form = AutoridadNewForm()
    if form.validate_on_submit():
        # Validar que la clave no se repita
        clave = safe_clave(form.clave.data)
        if Autoridad.query.filter_by(clave=clave).first():
            flash("La clave ya está en uso. Debe de ser única.", "warning")
            return render_template("autoridades/new.jinja2", form=form)
        # Guardar
        autoridad = Autoridad(
            distrito_id=form.distrito.data,
            materia_id=form.materia.data,
            municipio_id=form.municipio.data,
            clave=clave,
            descripcion=safe_string(form.descripcion.data, save_enie=True),
            descripcion_corta=safe_string(form.descripcion_corta.data, save_enie=True),
            organo_jurisdiccional=form.organo_jurisdiccional.data,
            sede=form.sede.data,
            es_archivo_solicitante=form.es_archivo_solicitante.data,
            es_cemasc=form.es_cemasc.data,
            es_defensoria=form.es_defensoria.data,
            es_extinto=form.es_extinto.data,
            es_jurisdiccional=form.es_jurisdiccional.data,
            es_notaria=form.es_notaria.data,
            es_organo_especializado=form.es_organo_especializado.data,
            es_revisor_escrituras=form.es_revisor_escrituras.data,
        )
        autoridad.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva Autoridad {autoridad.clave}"),
            url=url_for("autoridades.detail", autoridad_id=autoridad.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("autoridades/new.jinja2", form=form)


@autoridades.route("/autoridades/edicion/<int:autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(autoridad_id):
    """Editar Autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    form = AutoridadEditForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia la clave verificar que no este en uso
        clave = safe_clave(form.clave.data)
        if autoridad.clave != clave:
            oficina_existente = Autoridad.query.filter_by(clave=clave).first()
            if oficina_existente and oficina_existente.id != autoridad_id:
                es_valido = False
                flash("La clave ya está en uso. Debe de ser única.", "warning")
        # Si es valido actualizar
        if es_valido:
            autoridad.distrito_id = form.distrito.data
            autoridad.materia_id = form.materia.data
            autoridad.municipio_id = form.municipio.data
            autoridad.clave = clave
            autoridad.descripcion = safe_string(form.descripcion.data, save_enie=True)
            autoridad.descripcion_corta = safe_string(form.descripcion_corta.data, save_enie=True)
            autoridad.es_archivo_solicitante = form.es_archivo_solicitante.data
            autoridad.es_cemasc = form.es_cemasc.data
            autoridad.es_defensoria = form.es_defensoria.data
            autoridad.es_extinto = form.es_extinto.data
            autoridad.es_jurisdiccional = form.es_jurisdiccional.data
            autoridad.es_notaria = form.es_notaria.data
            autoridad.es_organo_especializado = form.es_organo_especializado.data
            autoridad.es_revisor_escrituras = form.es_revisor_escrituras.data
            autoridad.organo_jurisdiccional = form.organo_jurisdiccional.data
            autoridad.sede = form.sede.data
            autoridad.directorio_edictos = form.directorio_edictos.data
            autoridad.directorio_glosas = form.directorio_glosas.data
            autoridad.directorio_listas_de_acuerdos = form.directorio_listas_de_acuerdos.data
            autoridad.directorio_sentencias = form.directorio_sentencias.data
            autoridad.limite_dias_listas_de_acuerdos = form.limite_dias_listas_de_acuerdos.data
            autoridad.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editada Autoridad {autoridad.clave}"),
                url=url_for("autoridades.detail", autoridad_id=autoridad.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.distrito.data = autoridad.distrito_id  # Usa id porque es un SelectField
    form.materia.data = autoridad.materia_id  # Usa id porque es un SelectField
    form.municipio.data = autoridad.municipio_id  # Usa id porque es un SelectField
    form.clave.data = autoridad.clave
    form.descripcion.data = autoridad.descripcion
    form.descripcion_corta.data = autoridad.descripcion_corta
    form.es_archivo_solicitante.data = autoridad.es_archivo_solicitante
    form.es_cemasc.data = autoridad.es_cemasc
    form.es_defensoria.data = autoridad.es_defensoria
    form.es_extinto.data = autoridad.es_extinto
    form.es_jurisdiccional.data = autoridad.es_jurisdiccional
    form.es_notaria.data = autoridad.es_notaria
    form.es_organo_especializado.data = autoridad.es_organo_especializado
    form.es_revisor_escrituras.data = autoridad.es_revisor_escrituras
    form.organo_jurisdiccional.data = autoridad.organo_jurisdiccional
    form.sede.data = autoridad.sede
    form.directorio_edictos.data = autoridad.directorio_edictos
    form.directorio_glosas.data = autoridad.directorio_glosas
    form.directorio_listas_de_acuerdos.data = autoridad.directorio_listas_de_acuerdos
    form.directorio_sentencias.data = autoridad.directorio_sentencias
    form.limite_dias_listas_de_acuerdos.data = autoridad.limite_dias_listas_de_acuerdos
    return render_template("autoridades/edit.jinja2", form=form, autoridad=autoridad)


@autoridades.route("/autoridades/eliminar/<int:autoridad_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(autoridad_id):
    """Eliminar Autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if autoridad.estatus == "A":
        autoridad.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Autoridad {autoridad.clave}"),
            url=url_for("autoridades.detail", autoridad_id=autoridad.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))


@autoridades.route("/autoridades/recuperar/<int:autoridad_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(autoridad_id):
    """Recuperar Autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if autoridad.estatus == "B":
        autoridad.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Autoridad {autoridad.clave}"),
            url=url_for("autoridades.detail", autoridad_id=autoridad.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))


@autoridades.route("/autoridades/select_json/<int:distrito_id>", methods=["GET", "POST"])
def query_autoridades_json(distrito_id):
    """Proporcionar el JSON de autoridades para elegir con un Select"""
    # Consultar
    consulta = Autoridad.query.filter_by(estatus="A").filter_by(distrito_id=distrito_id)
    # Si viene es_archivo_solicitante como parametro en el URL como true o false
    if "es_archivo_solicitante" in request.args:
        es_archivo_solicitante = request.args["es_archivo_solicitante"] == "true"
        consulta = consulta.filter_by(es_archivo_solicitante=es_archivo_solicitante)
    # Si viene es_cemasc como parametro en el URL como true o false
    if "es_cemasc" in request.args:
        es_cemasc = request.args["es_cemasc"] == "true"
        consulta = consulta.filter_by(es_cemasc=es_cemasc)
    # Si viene es_defensoria como parametro en el URL como true o false
    if "es_defensoria" in request.args:
        es_defensoria = request.args["es_defensoria"] == "true"
        consulta = consulta.filter_by(es_defensoria=es_defensoria)
    # Si viene es_extinto como parametro en el URL como true o false
    if "es_extinto" in request.args:
        es_extinto = request.args["es_extinto"] == "true"
        consulta = consulta.filter_by(es_extinto=es_extinto)
    # Si viene es_jurisdiccional como parametro en el URL como true o false
    if "es_jurisdiccional" in request.args:
        es_jurisdiccional = request.args["es_jurisdiccional"] == "true"
        consulta = consulta.filter_by(es_jurisdiccional=es_jurisdiccional)
    # Si viene es_notaria como parametro en el URL como true o false
    if "es_notaria" in request.args:
        es_notaria = request.args["es_notaria"] == "true"
        consulta = consulta.filter_by(es_notaria=es_notaria)
    # Si viene es_revisor_escrituras como parametro en el URL como true o false
    if "es_revisor_escrituras" in request.args:
        es_revisor_escrituras = request.args["es_revisor_escrituras"] == "true"
        consulta = consulta.filter_by(es_revisor_escrituras=es_revisor_escrituras)
    # Si viene es_organo_especializado como parametro en el URL como true o false
    if "es_organo_especializado" in request.args:
        es_organo_especializado = request.args["es_organo_especializado"] == "true"
        consulta = consulta.filter_by(es_organo_especializado=es_organo_especializado)
    # Ordenar
    consulta = consulta.order_by(Autoridad.descripcion_corta)
    # Elaborar datos para Select
    data = []
    for resultado in consulta.all():
        data.append(
            {
                "id": resultado.id,
                "descripcion_corta": resultado.descripcion_corta,
            }
        )
    # Entregar JSON
    return json.dumps(data)


@autoridades.route("/autoridades/select_json", methods=["GET", "POST"])
def select_autoridades_json():
    """Proporcionar el JSON de autoridades para elegir con un Select"""
    # Consultar
    consulta = Autoridad.query.filter(Autoridad.estatus == "A")
    if "es_archivo_solicitante" in request.form:
        consulta = consulta.filter_by(es_archivo_solicitante=request.form["es_archivo_solicitante"] == "true")
    if "es_extinto" in request.form:
        consulta = consulta.filter_by(es_extinto=request.form["es_extinto"] == "true")
    if "es_jurisdiccional" in request.form:
        consulta = consulta.filter_by(es_jurisdiccional=request.form["es_jurisdiccional"] == "true")
    if "clave" in request.form:
        clave = safe_clave(request.form["clave"])
        if clave != "":
            consulta = consulta.filter(Autoridad.clave.contains(clave))
    results = []
    for autoridad in consulta.order_by(Autoridad.id).limit(15).all():
        results.append(
            {
                "id": autoridad.id,
                "text": autoridad.clave + "  : " + autoridad.descripcion_corta,
            }
        )
    return {"results": results, "pagination": {"more": False}}
