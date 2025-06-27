"""
Ofi Plantillas, vistas
"""

import json
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import String, cast


from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message, safe_uuid, safe_clave

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.ofi_plantillas.models import OfiPlantilla
from hercules.blueprints.ofi_plantillas.forms import OfiPlantillaForm
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.autoridades.models import Autoridad


MODULO = "OFI PLANTILLAS"

ofi_plantillas = Blueprint("ofi_plantillas", __name__, template_folder="templates")


@ofi_plantillas.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@ofi_plantillas.route("/ofi_plantillas/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Ofi Plantillas"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = OfiPlantilla.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(OfiPlantilla.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(OfiPlantilla.estatus == "A")
    if "id" in request.form:
        id = safe_string(request.form["id"])
        if id:
            consulta = consulta.filter(cast(OfiPlantilla.id, String).contains(id.lower()))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion:
            consulta = consulta.filter(OfiPlantilla.descripcion.contains(descripcion))
    # Luego filtrar por columnas de otras tablas
    tabla_usuario_incluida = False
    if "autor" in request.form:
        if tabla_usuario_incluida is False:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
        autor = request.form["autor"].lower()
        consulta = consulta.filter(Usuario.email.contains(autor))
    if "autoridad" in request.form:
        autoridad = safe_clave(request.form["autoridad"])
        if autoridad:
            if tabla_usuario_incluida is False:
                consulta = consulta.join(Usuario)
                tabla_usuario_incluida = True
            consulta = consulta.join(Autoridad, Usuario.autoridad_id == Autoridad.id)
            consulta = consulta.filter(Autoridad.clave.contains(autoridad))
    if "usuario_autoridad_id" in request.form:
        if tabla_usuario_incluida is False:
            consulta = consulta.join(Usuario)
            tabla_usuario_incluida = True
        consulta = consulta.filter(Usuario.autoridad_id == request.form["usuario_autoridad_id"])
    # Ordenar y paginar
    registros = consulta.order_by(OfiPlantilla.descripcion).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("ofi_plantillas.detail", ofi_plantilla_id=resultado.id),
                },
                "autor": {
                    "email": resultado.usuario.email,
                    "nombre": resultado.usuario.nombre,
                    "url": url_for("usuarios.detail", usuario_id=resultado.usuario.id),
                },
                "autoridad": {
                    "clave": resultado.usuario.autoridad.clave,
                    "nombre": resultado.usuario.autoridad.descripcion_corta,
                    "url": (
                        url_for("autoridades.detail", autoridad_id=resultado.usuario.autoridad.id)
                        if current_user.can_view("AUTORIDADES")
                        else ""
                    ),
                },
                "descripcion": resultado.descripcion,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M"),
                "esta_archivado": resultado.esta_archivado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@ofi_plantillas.route("/ofi_plantillas")
def list_active():
    """Listado de Ofi Plantillas activos"""
    if current_user.can_admin(MODULO):
        return render_template(
            "ofi_plantillas/list_admin.jinja2",
            filtros=json.dumps({"estatus": "A"}),
            titulo="Plantillas",
            estatus="A",
        )
    return render_template(
        "ofi_plantillas/list.jinja2",
        filtros=json.dumps({"estatus": "A", "usuario_autoridad_id": current_user.autoridad.id}),
        titulo="Plantillas",
        estatus="A",
    )


@ofi_plantillas.route("/ofi_plantillas/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Ofi Plantillas inactivos"""
    if current_user.can_admin(MODULO):
        return render_template(
            "ofi_plantillas/list_admin.jinja2",
            filtros=json.dumps({"estatus": "B"}),
            titulo="Plantillas inactivos",
            estatus="B",
        )
    return render_template(
        "ofi_plantillas/list.jinja2",
        filtros=json.dumps({"estatus": "B", "usuario_autoridad_id": current_user.autoridad.id}),
        titulo="Plantillas inactivos",
        estatus="B",
    )


@ofi_plantillas.route("/ofi_plantillas/<ofi_plantilla_id>")
def detail(ofi_plantilla_id):
    """Detalle de un Ofi Plantilla"""
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    form = OfiPlantillaForm()
    form.descripcion.data = ofi_plantilla.descripcion
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.esta_archivado.data = ofi_plantilla.esta_archivado
    # Si está definida la variable de entorno SYNCFUSION_LICENSE_KEY
    if current_app.config.get("SYNCFUSION_LICENSE_KEY"):
        # Entregar detail_syncfusion_document.jinja2
        return render_template(
            "ofi_plantillas/detail_syncfusion_document.jinja2",
            ofi_plantilla=ofi_plantilla,
            form=form,
            syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
        )
    # De lo contrario, entregar detail.jinja2
    return render_template(
        "ofi_plantillas/detail.jinja2",
        ofi_plantilla=ofi_plantilla,
        form=form,
    )


@ofi_plantillas.route("/ofi_plantillas/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Ofi Plantilla"""
    form = OfiPlantillaForm()
    if form.validate_on_submit():
        # Validar autor
        autor = Usuario.query.filter_by(id=form.autor.data).first()
        if not autor:
            flash("Autor inválido", "warning")
            return redirect(url_for("ofi_plantillas.new"))
        ofi_plantilla = OfiPlantilla(
            usuario=autor,
            descripcion=safe_string(form.descripcion.data, save_enie=True),
            contenido_md=form.contenido_md.data,
            contenido_html=form.contenido_html.data,
            contenido_sfdt=form.contenido_sfdt.data,
        )
        ofi_plantilla.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Ofi Plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Si está definida la variable de entorno SYNCFUSION_LICENSE_KEY
    if current_app.config.get("SYNCFUSION_LICENSE_KEY"):
        # Entregar new_syncfusion_document.jinja2
        return render_template(
            "ofi_plantillas/new_syncfusion_document.jinja2",
            form=form,
            syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
        )
    # De lo contrario, entregar new_ckeditor5.jinja2
    return render_template(
        "ofi_plantillas/new_ckeditor5.jinja2",
        form=form,
    )


@ofi_plantillas.route("/ofi_plantillas/edicion/<ofi_plantilla_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(ofi_plantilla_id):
    """Editar Ofi Plantilla"""
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    form = OfiPlantillaForm()
    if form.validate_on_submit():
        # Validar autor
        es_valido = True
        autor = Usuario.query.filter_by(id=form.autor.data).first()
        if not autor:
            flash("Autor inválido", "warning")
            es_valido = False
        if es_valido:
            ofi_plantilla.descripcion = safe_string(form.descripcion.data, save_enie=True)
            ofi_plantilla.usuario = autor
            ofi_plantilla.contenido_md = form.contenido_md.data
            ofi_plantilla.contenido_html = form.contenido_html.data
            ofi_plantilla.contenido_sfdt = form.contenido_sfdt.data
            ofi_plantilla.esta_archivado = form.esta_archivado.data
            ofi_plantilla.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Ofi Plantilla {ofi_plantilla.descripcion}"),
                url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.descripcion.data = ofi_plantilla.descripcion
    form.contenido_md.data = ofi_plantilla.contenido_md
    form.contenido_html.data = ofi_plantilla.contenido_html
    form.contenido_sfdt.data = ofi_plantilla.contenido_sfdt
    form.esta_archivado.data = ofi_plantilla.esta_archivado
    # Si está definida la variable de entorno SYNCFUSION_LICENSE_KEY
    if current_app.config.get("SYNCFUSION_LICENSE_KEY"):
        # Entregar edit_syncfusion_document.jinja2
        return render_template(
            "ofi_plantillas/edit_syncfusion_document.jinja2",
            form=form,
            ofi_plantilla=ofi_plantilla,
            syncfusion_license_key=current_app.config["SYNCFUSION_LICENSE_KEY"],
        )
    # De lo contrario, entregar edit_ckeditor5.jinja2
    return render_template(
        "ofi_plantillas/edit_ckeditor5.jinja2",
        form=form,
        ofi_plantilla=ofi_plantilla,
    )


@ofi_plantillas.route("/ofi_plantillas/eliminar/<ofi_plantilla_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(ofi_plantilla_id):
    """Eliminar Ofi Plantilla"""
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    if ofi_plantilla.estatus == "A":
        ofi_plantilla.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Ofi Plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id))


@ofi_plantillas.route("/ofi_plantillas/recuperar/<ofi_plantilla_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(ofi_plantilla_id):
    """Recuperar Ofi Plantilla"""
    ofi_plantilla_id = safe_uuid(ofi_plantilla_id)
    if not ofi_plantilla_id:
        flash("ID de plantilla inválido", "warning")
        return redirect(url_for("ofi_plantillas.list_active"))
    ofi_plantilla = OfiPlantilla.query.get_or_404(ofi_plantilla_id)
    if ofi_plantilla.estatus == "B":
        ofi_plantilla.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Ofi Plantilla {ofi_plantilla.descripcion}"),
            url=url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("ofi_plantillas.detail", ofi_plantilla_id=ofi_plantilla.id))
