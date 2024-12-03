"""
Exhorto - Actualizaciones, vistas
"""

import json
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.exh_exhortos_actualizaciones.models import ExhExhortoActualizacion
from hercules.blueprints.exh_exhortos_actualizaciones.forms import ExhExhortoActualizacionNewForm
from hercules.blueprints.exh_exhortos.models import ExhExhorto

MODULO = "EXH EXHORTOS ACTUALIZACIONES"

exh_exhortos_actualizaciones = Blueprint("exh_exhortos_actualizaciones", __name__, template_folder="templates")


@exh_exhortos_actualizaciones.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Actualizaciones"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoActualizacion.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_id=request.form["exh_exhorto_id"])
    # Luego filtrar por columnas de otras tablas
    # if "persona_rfc" in request.form:
    #     consulta = consulta.join(Persona)
    #     consulta = consulta.filter(Persona.rfc.contains(safe_rfc(request.form["persona_rfc"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoActualizacion.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "origen_id": {
                    "origen_id": resultado.actualizacion_origen_id,
                    "url": url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=resultado.id),
                },
                "fecha_hora": resultado.fecha_hora.strftime("%Y/%m/%d %H:%M"),
                "tipo_actualizacion": resultado.tipo_actualizacion,
                "descripcion": resultado.descripcion,
                "remitente": resultado.remitente,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/<int:exh_exhorto_actualizacion_id>")
def detail(exh_exhorto_actualizacion_id):
    """Detalle de un Actualización"""
    exh_exhorto_actualizacion = ExhExhortoActualizacion.query.get_or_404(exh_exhorto_actualizacion_id)
    return render_template("exh_exhortos_actualizaciones/detail.jinja2", exh_exhorto_actualizacion=exh_exhorto_actualizacion)


@exh_exhortos_actualizaciones.route("/exh_exhortos_actualizaciones/nuevo/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto(exh_exhorto_id):
    """Nuevo Actualización"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    form = ExhExhortoActualizacionNewForm()
    if form.validate_on_submit():
        exh_exhorto_actualizacion = ExhExhortoActualizacion(
            exh_exhorto=exh_exhorto,
            actualizacion_origen_id=safe_string(form.origen_id.data),
            tipo_actualizacion=safe_string(form.tipo_actualizacion.data),
            descripcion=safe_string(form.descripcion.data),
            fecha_hora=datetime.now(),
            remitente="INTERNO",
        )
        exh_exhorto_actualizacion.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Actualización {exh_exhorto_actualizacion.id}"),
            url=url_for("exh_exhortos_actualizaciones.detail", exh_exhorto_actualizacion_id=exh_exhorto_actualizacion.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("exh_exhortos_actualizaciones/new_with_exh_exhorto.jinja2", form=form, exh_exhorto=exh_exhorto)
