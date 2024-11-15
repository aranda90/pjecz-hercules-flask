"""
Exh Exhortos Videos, vistas
"""

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_videos.forms import ExhExhortoVideoForm
from hercules.blueprints.exh_exhortos_videos.models import ExhExhortoVideo
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_message, safe_string, safe_url

MODULO = "EXH EXHORTOS VIDEOS"

exh_exhortos_videos = Blueprint("exh_exhortos_videos", __name__, template_folder="templates")


@exh_exhortos_videos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos_videos.route("/exh_exhortos_videos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Videos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhortoVideo.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "exh_exhorto_id" in request.form:
        consulta = consulta.filter_by(exh_exhorto_id=request.form["exh_exhorto_id"])
    # registros
    registros = consulta.order_by(ExhExhortoVideo.id).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "titulo": resultado.titulo,
                    "url": url_for("exh_exhortos_videos.detail", exh_exhorto_video_id=resultado.id),
                },
                "descripcion": resultado.descripcion,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
                "fecha": resultado.fecha.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos_videos.route("/exh_exhortos_videos")
def list_active():
    """Listado de Videos activos"""
    return "TODO: Listado de Videos activos"


@exh_exhortos_videos.route("/exh_exhortos_videos/<int:exh_exhorto_video_id>")
def detail(exh_exhorto_video_id):
    """Detalle de un Video"""
    exh_exhorto_video = ExhExhortoVideo.query.get_or_404(exh_exhorto_video_id)
    return render_template("exh_exhortos_videos/detail.jinja2", exh_exhorto_video=exh_exhorto_video)


@exh_exhortos_videos.route("/exh_exhortos_videos/nuevo_con_exhorto/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_with_exh_exhorto(exh_exhorto_id):
    """Nuevo Video con un Exhorto"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    form = ExhExhortoVideoForm()
    if form.validate_on_submit():
        # Insertar el registro ExhExhortoVideo
        exh_exhorto_video = ExhExhortoVideo(
            exh_exhorto=exh_exhorto,
            titulo=safe_string(form.titulo.data),
            descripcion=safe_message(form.descripcion.data, max_len=1024, default_output_str=None),
            fecha=datetime.now(),
            url_acceso=safe_url(form.url_acceso.data),
        )
        exh_exhorto_video.save()

        # Insertar en la Bitácora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Video {exh_exhorto_video.titulo}"),
            url=url_for("exh_exhortos_videos.detail", exh_exhorto_video_id=exh_exhorto_video.id),
        )
        bitacora.save()

        # Mostrar mensaje de éxito y redirigir a la página del detalle del ExhExhorto
        flash(bitacora.descripcion, "success")
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto_id))

    # Entregar el formulario
    return render_template("exh_exhortos_videos/new_with_exh_exhorto.jinja2", form=form, exh_exhorto=exh_exhorto)


@exh_exhortos_videos.route("/exh_exhortos_videos/edicion/<int:exh_exhorto_video_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_video_id):
    """Editar Exhorto Video"""
    exh_exhorto_video = ExhExhortoVideo.query.get_or_404(exh_exhorto_video_id)
    form = ExhExhortoVideoForm()
    if form.validate_on_submit():
        exh_exhorto_video.titulo = safe_string(form.titulo.data)
        exh_exhorto_video.descripcion = safe_message(form.descripcion.data, max_len=1024, default_output_str=None)
        exh_exhorto_video.url_acceso = safe_url(form.url_acceso.data)
        exh_exhorto_video.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Exhorto Video {exh_exhorto_video.titulo}"),
            url=url_for("exh_exhortos_videos.detail", exh_exhorto_video_id=exh_exhorto_video.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    form.titulo.data = exh_exhorto_video.titulo
    form.descripcion.data = exh_exhorto_video.descripcion
    form.url_acceso.data = exh_exhorto_video.url_acceso
    return render_template("exh_exhortos_videos/edit.jinja2", form=form, exh_exhorto_video=exh_exhorto_video)


@exh_exhortos_videos.route("/exh_exhortos_videos/eliminar/<int:exh_exhorto_video_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_video_id):
    """Eliminar Exhorto Video"""
    exh_exhorto_video = ExhExhortoVideo.query.get_or_404(exh_exhorto_video_id)
    if exh_exhorto_video.estatus == "A":
        exh_exhorto_video.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Exhorto Video {exh_exhorto_video.titulo}"),
            url=url_for("exh_exhortos_videos.detail", exh_exhorto_video_id=exh_exhorto_video.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_videos.detail", exh_exhorto_video_id=exh_exhorto_video.id))


@exh_exhortos_videos.route("/exh_exhortos_videos/recuperar/<int:exh_exhorto_video_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_video_id):
    """Recuperar Exhorto Video"""
    exh_exhorto_video = ExhExhortoVideo.query.get_or_404(exh_exhorto_video_id)
    if exh_exhorto_video.estatus == "B":
        exh_exhorto_video.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Exhorto Video {exh_exhorto_video.titulo}"),
            url=url_for("exh_exhortos_videos.detail", exh_exhorto_video_id=exh_exhorto_video.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos_videos.detail", exh_exhorto_video_id=exh_exhorto_video.id))
