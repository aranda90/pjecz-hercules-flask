"""
Exh Exhortos Respuestas Videos, vistas
"""

import json
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos_respuestas.models import ExhExhortoRespuesta
from hercules.blueprints.exh_exhortos_respuestas_videos.forms import ExhExhortoRespuestaVideoForm
from hercules.blueprints.exh_exhortos_respuestas_videos.models import ExhExhortoRespuestaVideo
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string, safe_url

MODULO = "EXH EXHORTOS RESPUESTAS VIDEOS"

exh_exhortos_respuestas_videos = Blueprint("exh_exhortos_respuestas_videos", __name__, template_folder="templates")


@exh_exhortos_respuestas_videos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_respuestas_videos.route("/exh_exhortos_respuestas_videos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Videos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoRespuestaVideo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_respuesta_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_respuesta_id=request.form["exh_exhorto_respuesta_id"])
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhortoRespuestaVideo.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "titulo": resultado.titulo,
                    "url": url_for("exh_exhortos_respuestas_videos.detail", exh_exhorto_respuesta_video_id=resultado.id),
                },
                "hipervinculo": {
                    "descripcion": resultado.descripcion,
                    "url_acceso": resultado.url_acceso,
                },
                "fecha": resultado.fecha.strftime("%Y-%m-%d %H:%M:%S") if resultado.fecha != None else "",
                "respuesta_origen_id": resultado.exh_exhorto_respuesta.respuesta_origen_id,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_respuestas_videos.route("/exh_exhortos_respuestas_videos")
def list_active():
    """Listado de Videos activos"""
    return render_template(
        "exh_exhortos_respuestas_videos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos Respuestas Videos",
        estatus="A",
    )


@exh_exhortos_respuestas_videos.route("/exh_exhortos_respuestas_videos/<int:exh_exhorto_respuesta_video_id>")
def detail(exh_exhorto_respuesta_video_id):
    """Detalle de un Video"""
    exh_exhorto_respuesta_video = ExhExhortoRespuestaVideo.query.get_or_404(exh_exhorto_respuesta_video_id)
    return render_template(
        "exh_exhortos_respuestas_videos/detail.jinja2", exh_exhorto_respuesta_video=exh_exhorto_respuesta_video
    )


@exh_exhortos_respuestas_videos.route("/exh_exhortos_respuestas_videos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Videos inactivos"""
    return render_template(
        "exh_exhortos_respuestas_videos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos Respuestas Videos inactivos",
        estatus="B",
    )


@exh_exhortos_respuestas_videos.route(
    "/exh_exhortos_respuestas_videos/nuevo_con_exhorto_respuesta/<int:exh_exhorto_respuesta_id>", methods=["GET", "POST"]
)
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto_respuesta(exh_exhorto_respuesta_id):
    """Agregar Video a la Respuesta"""
    exh_exhorto_respuesta = ExhExhortoRespuesta.query.get_or_404(exh_exhorto_respuesta_id)
    form = ExhExhortoRespuestaVideoForm()
    if form.validate_on_submit():
        # Insertar el registro ExhExhortoRespuestaVideo
        exh_exhorto_respuesta_video = ExhExhortoRespuestaVideo(
            exh_exhorto_respuesta=exh_exhorto_respuesta,
            titulo=safe_string(form.titulo.data),
            descripcion=safe_string(form.descripcion.data, max_len=1024),
            fecha=datetime.now(),
            url_acceso=safe_url(form.url_acceso.data),
        )
        exh_exhorto_respuesta_video.save()
        # Insertar en la Bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Video a la Respuesta {exh_exhorto_respuesta_video.titulo}"),
            url=url_for("exh_exhortos_respuestas_videos.detail", exh_exhorto_respuesta_video_id=exh_exhorto_respuesta_video.id),
        )
        bitacora.save()
        # Mostrar mensaje de éxito y redirigir a la página del detalle del ExhExhorto
        flash(bitacora.descripcion, "success")
        return redirect(url_for("exh_exhortos_respuestas.detail", exh_exhorto_respuesta_id=exh_exhorto_respuesta_id))
    # Entregar el formulario
    return render_template(
        "exh_exhortos_respuestas_videos/new_with_exh_exhorto_respuesta.jinja2",
        form=form,
        exh_exhorto_respuesta=exh_exhorto_respuesta,
    )


@exh_exhortos_respuestas_videos.route(
    "/exh_exhortos_respuestas_videos/edicion/<int:exh_exhorto_respuesta_video_id>", methods=["GET", "POST"]
)
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_respuesta_video_id):
    """Editar Video"""
    exh_exhorto_respuesta_video = ExhExhortoRespuestaVideo.query.get_or_404(exh_exhorto_respuesta_video_id)
    # Si el estado la respuesta NO es PENDIENTE, no se puede editar
    if exh_exhorto_respuesta_video.exh_exhorto_respuesta.estado != "PENDIENTE":
        flash("No se puede editar porque la promoción que no está en estado PENDIENTE", "warning")
        return redirect(
            url_for("exh_exhortos_respuestas_videos.detail", exh_exhorto_respuesta_video_id=exh_exhorto_respuesta_video_id)
        )
    # Crear formulario
    form = ExhExhortoRespuestaVideoForm()
    if form.validate_on_submit():
        exh_exhorto_respuesta_video.titulo = safe_string(form.titulo.data)
        exh_exhorto_respuesta_video.descripcion = safe_string(form.descripcion.data, max_len=1024)
        exh_exhorto_respuesta_video.url_acceso = safe_url(form.url_acceso.data)
        exh_exhorto_respuesta_video.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Exhorto Video {exh_exhorto_respuesta_video.titulo}"),
            url=url_for("exh_exhortos_respuestas_videos.detail", exh_exhorto_respuesta_video_id=exh_exhorto_respuesta_video.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.titulo.data = exh_exhorto_respuesta_video.titulo
    form.descripcion.data = exh_exhorto_respuesta_video.descripcion
    form.url_acceso.data = exh_exhorto_respuesta_video.url_acceso
    return render_template(
        "exh_exhortos_respuestas_videos/edit.jinja2",
        form=form,
        exh_exhorto_respuesta_video=exh_exhorto_respuesta_video,
    )


@exh_exhortos_respuestas_videos.route("/exh_exhortos_respuestas_videos/eliminar/<int:exh_exhorto_respuesta_video_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_respuesta_video_id):
    """Eliminar Video"""
    exh_exhorto_respuesta_video = ExhExhortoRespuestaVideo.query.get_or_404(exh_exhorto_respuesta_video_id)
    if exh_exhorto_respuesta_video.estatus == "A":
        exh_exhorto_respuesta_video.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Exhorto Video {exh_exhorto_respuesta_video.id}"),
            url=url_for("exh_exhortos_respuestas_videos.detail", exh_exhorto_respuesta_video_id=exh_exhorto_respuesta_video.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(
        url_for("exh_exhortos_respuestas_videos.detail", exh_exhorto_respuesta_video_id=exh_exhorto_respuesta_video.id)
    )


@exh_exhortos_respuestas_videos.route("/exh_exhortos_respuestas_videos/recuperar/<int:exh_exhorto_respuesta_video_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_respuesta_video_id):
    """Recuperar Video"""
    exh_exhorto_respuesta_video = ExhExhortoRespuestaVideo.query.get_or_404(exh_exhorto_respuesta_video_id)
    if exh_exhorto_respuesta_video.estatus == "B":
        exh_exhorto_respuesta_video.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Exhorto Video {exh_exhorto_respuesta_video.id}"),
            url=url_for("exh_exhortos_respuestas_videos.detail", exh_exhorto_respuesta_video_id=exh_exhorto_respuesta_video.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(
        url_for("exh_exhortos_respuestas_videos.detail", exh_exhorto_respuesta_video_id=exh_exhorto_respuesta_video.id)
    )
