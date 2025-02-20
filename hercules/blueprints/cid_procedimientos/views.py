"""
CID Procedimientos, vistas
"""

import json
from datetime import datetime, timezone

from delta import html
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.cid_areas.models import CIDArea
from hercules.blueprints.cid_areas_autoridades.models import CIDAreaAutoridad
from hercules.blueprints.cid_formatos.models import CIDFormato
from hercules.blueprints.cid_procedimientos.forms import (
    CIDProcedimientoAcceptRejectForm,
    CIDProcedimientoCambiarAreaForm,
    CIDProcedimientoEditForm,
    CIDProcedimientoForm,
    CIDProcedimientosNewReview,
)
from hercules.blueprints.cid_procedimientos.models import CIDProcedimiento
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.roles.models import Rol
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.usuarios_roles.models import UsuarioRol
from hercules.extensions import database
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_email, safe_message, safe_string

MODULO = "CID PROCEDIMIENTOS"

cid_procedimientos = Blueprint("cid_procedimientos", __name__, template_folder="templates")

# Roles que deben estar en la base de datos
ROL_ADMINISTRADOR = "ADMINISTRADOR"
ROL_COORDINADOR = "SICGD COORDINADOR"
ROL_DIRECTOR_JEFE = "SICGD DIRECTOR O JEFE"
ROL_DUENO_PROCESO = "SICGD DUENO DE PROCESO"
ROL_INVOLUCRADO = "SICGD INVOLUCRADO"
ROLES_CON_PROCEDIMIENTOS_PROPIOS = (ROL_DUENO_PROCESO, ROL_DIRECTOR_JEFE)
ROLES_NUEVA_REVISION = ("SICGD COORDINADOR", "SICGD DUENO DE PROCESO")


@cid_procedimientos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@cid_procedimientos.route("/cid_procedimientos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de CID Procedimientos"""

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = CIDProcedimiento.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "cid_area_id" in request.form:
        consulta = consulta.filter(CIDProcedimiento.cid_area_id == request.form["cid_area_id"])
    if "cid_area_clave" in request.form:
        cid_area_clave = safe_clave(request.form["cid_area_clave"])
        if cid_area_clave != "":
            consulta = consulta.join(CIDArea).filter(CIDArea.clave == cid_area_clave)
    if "usuario_id" in request.form:
        consulta = consulta.filter(CIDProcedimiento.usuario_id == request.form["usuario_id"])
    if "codigo" in request.form:
        codigo = safe_clave(request.form["codigo"])
        if codigo != "":
            consulta = consulta.filter(CIDProcedimiento.codigo.contains(codigo))
    if "titulo_procedimiento" in request.form:
        titulo_procedimiento = safe_string(request.form["titulo_procedimiento"], save_enie=True)
        if titulo_procedimiento != "":
            consulta = consulta.filter(CIDProcedimiento.titulo_procedimiento.contains(titulo_procedimiento))
    if "seguimiento" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento == request.form["seguimiento"])
    if "seguimiento_posterior" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento_posterior == request.form["seguimiento_posterior"])
    if "cid_areas_ids[]" in request.form:
        areas_a_filtrar = request.form.getlist("cid_areas_ids[]")
        listado_areas_ids = [int(area_id) for area_id in areas_a_filtrar]
        consulta = consulta.filter(CIDProcedimiento.cid_area_id.in_(listado_areas_ids))

    # Ordenar y paginar
    registros = consulta.order_by(CIDProcedimiento.titulo_procedimiento).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "codigo": resultado.codigo if resultado.codigo else "SIN CODIGO",
                    "url": url_for("cid_procedimientos.detail", cid_procedimiento_id=resultado.id),
                },
                "titulo_procedimiento": resultado.titulo_procedimiento,
                "revision": resultado.revision,
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "seguimiento": resultado.seguimiento,
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@cid_procedimientos.route("/cid_procedimientos/admin_datatable_json", methods=["GET", "POST"])
def admin_datatable_json():
    """DataTable JSON para listado de Cid Procedimientos"""

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = CIDProcedimiento.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(CIDProcedimiento.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(CIDProcedimiento.estatus == "A")
    if "cid_procedmiento_id" in request.form:
        try:
            cid_procedimiento_id = int(request.form["cid_procedmiento_id"])
            consulta = consulta.filter(CIDProcedimiento.id == cid_procedimiento_id)
        except ValueError:
            pass
    if "cid_area_id" in request.form:
        consulta = consulta.filter(CIDProcedimiento.cid_area_id == request.form["cid_area_id"])
    if "cid_area_clave" in request.form:
        cid_area_clave = safe_clave(request.form["cid_area_clave"])
        if cid_area_clave != "":
            consulta = consulta.join(CIDArea).filter(CIDArea.clave == cid_area_clave)
    if "usuario_id" in request.form:
        consulta = consulta.filter(CIDProcedimiento.usuario_id == request.form["usuario_id"])
    if "codigo" in request.form:
        codigo = safe_clave(request.form["codigo"])
        if codigo != "":
            consulta = consulta.filter(CIDProcedimiento.codigo.contains(codigo))
    if "titulo_procedimiento" in request.form:
        titulo_procedimiento = safe_string(request.form["titulo_procedimiento"], save_enie=True)
        if titulo_procedimiento != "":
            consulta = consulta.filter(CIDProcedimiento.titulo_procedimiento.contains(titulo_procedimiento))
    if "seguimiento" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento == request.form["seguimiento"])
    if "seguimiento_posterior" in request.form:
        consulta = consulta.filter(CIDProcedimiento.seguimiento_posterior == request.form["seguimiento_posterior"])
    if "cid_areas_ids[]" in request.form:
        areas_a_filtrar = request.form.getlist("cid_areas_ids[]")
        listado_areas_ids = [int(area_id) for area_id in areas_a_filtrar]
        consulta = consulta.filter(CIDProcedimiento.cid_area_id.in_(listado_areas_ids))

    # Ordenar y paginar
    registros = consulta.order_by(CIDProcedimiento.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("cid_procedimientos.detail", cid_procedimiento_id=resultado.id),
                },
                "codigo": resultado.codigo,
                "titulo_procedimiento": resultado.titulo_procedimiento,
                "revision": resultado.revision,
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "seguimiento": resultado.seguimiento,
                "seguimiento_posterior": resultado.seguimiento_posterior,
                "usuario_email": resultado.usuario.email,
                "cid_area_clave": resultado.cid_area.clave,
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@cid_procedimientos.route("/cid_procedimientos")
def list_active():
    """Listado de CID Procedimientos activos"""

    # Definir valores por defecto
    current_user_cid_areas_ids = []
    current_user_roles = set(current_user.get_roles())
    filtros = None
    mostrar_boton_listado_por_defecto = False
    mostrar_boton_procedimientos_de_mis_areas = False
    plantilla = "cid_procedimientos/list.jinja2"
    titulo = None

    # Si es administrador, usar la plantilla es list_admin.jinja2
    if current_user.can_admin(MODULO):
        plantilla = "cid_procedimientos/list_admin.jinja2"

    # Si viene cid_area_id, cid_areas_ids, cid_area_clave, seguimiento o usuario_id en la URL, agregar a los filtros
    try:
        if "cid_area_id" in request.args:
            cid_area_id = int(request.args["cid_area_id"])
            cid_area = CIDArea.query.get(cid_area_id)
            filtros = {
                "estatus": "A",
                "cid_area_id": cid_area_id,
                "seguimiento": "AUTORIZADO",
            }
            titulo = f"Procedimientos autorizados del área {cid_area.nombre}"
            mostrar_boton_listado_por_defecto = True
        elif "cid_area_clave" in request.args:
            cid_area_clave = safe_clave(request.args["cid_area_clave"])
            cid_area = CIDArea.query.filter_by(clave=cid_area_clave).first()
            if cid_area:
                filtros = {
                    "estatus": "A",
                    "cid_area_clave": cid_area_clave,
                    "seguimiento": "AUTORIZADO",
                }
                titulo = f"Procedimientos autorizados del área {cid_area.nombre}"
                mostrar_boton_listado_por_defecto = True
        elif "cid_areas_ids" in request.args:
            cid_areas_ids = [int(id) for id in request.args["cid_areas_ids"].split(",")]
            filtros = {
                "estatus": "A",
                "cid_areas_ids": cid_areas_ids,
                "seguimiento": "AUTORIZADO",
            }
            titulo = "Procedimientos autorizados de mis áreas"
            mostrar_boton_listado_por_defecto = True
        elif "usuario_id" in request.args:
            usuario_id = int(request.args["usuario_id"])
            filtros = {"estatus": "A", "usuario_id": usuario_id}
            titulo = f"Procedimientos del usuario {Usuario.query.get(usuario_id).nombre}"
            mostrar_boton_listado_por_defecto = True
        elif "seguimiento" in request.args:
            seguimiento = safe_string(request.args["seguimiento"])
            filtros = {"estatus": "A", "seguimiento": seguimiento}
            titulo = f"Procedimientos con seguimiento {seguimiento}"
            mostrar_boton_listado_por_defecto = True
    except (TypeError, ValueError):
        pass

    # Si titulo es None y es administrador, mostrar todos los procedimientos
    if titulo is None and current_user.can_admin(MODULO):
        titulo = "Todos los procedimientos (admin)"
        filtros = {"estatus": "A"}

    # Si titulo es none y tiene el rol "SICGD AUDITOR", mostrar los procedimientos
    if titulo is None and "SICGD AUDITOR" in current_user_roles:
        titulo = "Todos los procedimientos (auditor)"
        filtros = {"estatus": "A"}

    # Si titulo es None y tiene el rol "SICGD COORDINADOR", mostrar todos los procedimientos
    if titulo is None and "SICGD COORDINADOR" in current_user_roles:
        titulo = "Todos los procedimientos (coordinador)"
        filtros = {"estatus": "A"}

    # Obtener los IDs de las áreas del usuario
    current_user_cid_areas_ids = [
        cid_area.id
        for cid_area in (
            CIDArea.query.join(CIDAreaAutoridad).filter(CIDAreaAutoridad.autoridad_id == current_user.autoridad.id).all()
        )
    ]

    # Si titulo es None y tiene ROLES_CON_PROCEDIMIENTOS_PROPIOS, mostrar los procedimientos propios
    if (
        titulo is None
        and current_user_roles.intersection(ROLES_CON_PROCEDIMIENTOS_PROPIOS)
        and len(current_user_cid_areas_ids) > 0
    ):
        titulo = "Procedimientos propios"
        filtros = {"estatus": "A", "usuario_id": current_user.id, "cid_areas_ids": current_user_cid_areas_ids}
        mostrar_boton_procedimientos_de_mis_areas = True

    # Si el titulo es None y tiene áreas, mostrar los procedimientos autorizados de mis áreas
    if titulo is None and len(current_user_cid_areas_ids) > 0:
        titulo = "Procedimientos autorizados de mis áreas (involucrado)"
        filtros = {
            "estatus": "A",
            "seguimiento": "AUTORIZADO",
            "cid_areas_ids": current_user_cid_areas_ids,
        }

    # Por defecto, mostrar los procedimientos autorizados
    if titulo is None:
        titulo = "Procedimientos autorizados de todas las áreas"
        filtros = {"estatus": "A", "seguimiento": "AUTORIZADO"}

    # Entregar
    return render_template(
        plantilla,
        current_user_cid_areas_ids=",".join([str(id) for id in current_user_cid_areas_ids]),
        estatus="A",
        filtros=json.dumps(filtros),
        mostrar_boton_listado_por_defecto=mostrar_boton_listado_por_defecto,
        mostrar_boton_procedimientos_de_mis_areas=mostrar_boton_procedimientos_de_mis_areas,
        titulo=titulo,
    )


@cid_procedimientos.route("/cid_procedimientos/eliminados")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de procedimientos eliminados, solo para administrador"""
    return render_template(
        "cid_procedimientos/list_admin.jinja2",
        titulo="Todos los procedimientos eliminados",
        filtros=json.dumps({"estatus": "B"}),
        estatus="B",
    )


@cid_procedimientos.route("/cid_procedimientos/<int:cid_procedimiento_id>")
def detail(cid_procedimiento_id):
    """Detalle de un CID Procedimiento"""
    # Consultar los roles del usuario
    current_user_roles = set(current_user.get_roles())
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    cid_formatos = (
        CIDFormato.query.filter(CIDFormato.procedimiento == cid_procedimiento)
        .filter(CIDFormato.estatus == "A")
        .order_by(CIDFormato.id)
        .all()
    )
    # Habilitar o deshabilitar poder cambiar área
    mostrar_cambiar_area = (ROL_ADMINISTRADOR in current_user_roles) or (ROL_COORDINADOR in current_user_roles)

    # Condición para mostrar botón de nueva revisión:
    # El procedimiento debe estar autorizado y el usuario debe tener los roles adecuados o ser el creador.
    show_buttom_new_revision = cid_procedimiento.seguimiento == "AUTORIZADO" and (
        current_user_roles.intersection(ROLES_NUEVA_REVISION)
    )
    # mostrar alerta para formatos revisiones mayores a 1
    mostrar_alerta_formatos = (
        cid_procedimiento.revision != 1
        and cid_procedimiento.seguimiento != "AUTORIZADO"
        and cid_procedimiento.seguimiento != "ARCHIVADO"
    )
    # mostrar boton para mandar a archivar porcedimiento
    mostrar_boton_archivado = cid_procedimiento.seguimiento == "AUTORIZADO" and (
        ROL_COORDINADOR in current_user_roles or ROL_ADMINISTRADOR in current_user_roles
    )
    return render_template(
        "cid_procedimientos/detail.jinja2",
        cid_procedimiento=cid_procedimiento,
        firma_al_vuelo=cid_procedimiento.elaborar_firma(),
        objetivo=str(html.render(cid_procedimiento.objetivo["ops"])),
        alcance=str(html.render(cid_procedimiento.alcance["ops"])),
        documentos=str(html.render(cid_procedimiento.documentos["ops"])),
        definiciones=str(html.render(cid_procedimiento.definiciones["ops"])),
        responsabilidades=str(html.render(cid_procedimiento.responsabilidades["ops"])),
        desarrollo=str(html.render(cid_procedimiento.desarrollo["ops"])),
        registros=cid_procedimiento.registros,
        control_cambios=cid_procedimiento.control_cambios,
        cid_formatos=cid_formatos,
        show_button_edit_admin=current_user.can_admin(MODULO) or ROL_COORDINADOR in current_user.get_roles(),
        mostrar_cambiar_area=mostrar_cambiar_area,
        show_buttom_new_revision=show_buttom_new_revision,
        mostrar_alerta_formatos=mostrar_alerta_formatos,
        mostrar_boton_archivado=mostrar_boton_archivado,
    )


@cid_procedimientos.route("/cid_procedimientos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo CID Procedimiento"""
    form = CIDProcedimientoForm()
    if form.validate_on_submit():
        # Obtener la autoridad del usuario actual
        autoridad = current_user.autoridad
        # Consultar la tabla CIDAreaAutoridad para obtener las relación entre la autoridad y el área correspondiente
        area_autoridad = CIDAreaAutoridad.query.filter_by(autoridad_id=autoridad.id).first()
        # Obtener el área "NO DEFINIDO" desde la base de datos
        area_no_definida = CIDArea.query.filter_by(nombre="NO DEFINIDO").first()

        # Verificar si se encontró un registro válido en la tabla CIDAreaAutoridad y si el área relacionada está definida
        if not area_autoridad:
            area_autoridad = CIDAreaAutoridad(autoridad_id=autoridad.id, cid_area=area_no_definida)
        else:
            # Si el área asociada está definida, verificar si es válida
            if not area_autoridad.cid_area:
                # Mostrar un mensaje de error si no se encontró un área asociada a la autoridad del usuario
                flash("No se encontró un área asociada a la autoridad del usuario.", "warning")
                # Redirigir al usuario a la página para crear un nuevo procedimiento
                return redirect(url_for("cid_procedimientos.new"))
        area = area_autoridad.cid_area  # Obtener el área relacionada
        elaboro_email = form.elaboro_email.data
        elaboro_nombre = form.elaboro_nombre.data
        if elaboro_email:
            try:
                elaboro_email = safe_email(elaboro_email)
            except ValueError:
                flash(f"El email '{elaboro_email}' no es válido.", "error")
                return redirect(url_for("cid_procedimientos.edit", cid_procedimiento_id=cid_procedimiento.id))
        else:
            elaboro_email = ""  # Si no se proporciona email, dejar vacío

        reviso_email = form.reviso_email.data
        reviso_nombre = form.reviso_nombre.data

        if reviso_email:  # Validar si se proporciona un email
            try:
                reviso_email = safe_email(reviso_email)
            except ValueError:
                flash(f"El email '{reviso_email}' no es válido.", "error")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id))
        else:
            reviso_email = ""

        aprobo_email = form.aprobo_email.data
        aprobo_nombre = form.aprobo_nombre.data

        if aprobo_email:  # Validar si se proporciona un email
            try:
                aprobo_email = safe_email(aprobo_email)
            except ValueError:
                flash(f"El email '{aprobo_email}' no es válido.", "error")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id))
        else:
            aprobo_email = ""
        registros_data = form.registros.data
        if registros_data is None:
            registros = {}
        else:
            registros = registros_data
        control = form.control_cambios.data
        if control is None:
            control_cambios = {}
        else:
            control_cambios = control
        cid_procedimiento = CIDProcedimiento(
            autoridad=current_user.autoridad,
            usuario=current_user,
            titulo_procedimiento=safe_string(form.titulo_procedimiento.data, to_uppercase=True),
            codigo=safe_clave(form.codigo.data),
            revision=form.revision.data,
            fecha=form.fecha.data,
            objetivo=form.objetivo.data,
            alcance=form.alcance.data,
            documentos=form.documentos.data,
            definiciones=form.definiciones.data,
            responsabilidades=form.responsabilidades.data,
            desarrollo=form.desarrollo.data,
            registros=registros,
            elaboro_nombre=safe_string(elaboro_nombre, save_enie=True),
            elaboro_puesto=safe_string(form.elaboro_puesto.data),
            elaboro_email=elaboro_email,
            reviso_nombre=safe_string(reviso_nombre, save_enie=True),
            reviso_puesto=safe_string(form.reviso_puesto.data),
            reviso_email=reviso_email,
            aprobo_nombre=safe_string(aprobo_nombre, save_enie=True),
            aprobo_puesto=safe_string(form.aprobo_puesto.data),
            aprobo_email=aprobo_email,
            control_cambios=control_cambios,
            cadena=0,
            seguimiento="EN ELABORACION",
            seguimiento_posterior="EN ELABORACION",
            anterior_id=0,
            firma="",
            archivo="",
            url="",
            cid_area_id=area.id,  # Asignar el área obtenida
            procedimiento_anterior_autorizado_id=None,
        )
        cid_procedimiento.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Procedimiento {cid_procedimiento.titulo_procedimiento}"),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    return render_template("cid_procedimientos/new.jinja2", form=form, help_quill=help_quill("new"))


@cid_procedimientos.route("/cid_procedimientos/edicion/<int:cid_procedimiento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(cid_procedimiento_id):
    """Editar CID Procedimiento"""
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    if not (current_user.can_admin(MODULO) or cid_procedimiento.usuario_id == current_user.id):
        abort(403)  # Acceso no autorizado, solo administradores o el propietario puede editarlo
    if cid_procedimiento.seguimiento not in ["EN ELABORACION", "EN REVISION", "EN AUTORIZACION"]:
        flash(f"No puede editar porque su seguimiento es {cid_procedimiento.seguimiento} y ha sido FIRMADO. ", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento_id))
    # Cargar procedimiento anterior si existe y calcula el número de revisión anterior restando 1 a la revisión actual del procedimiento
    revision_anterior = cid_procedimiento.revision - 1
    # Busca en la base de datos un procedimiento que coincida con la revisión anterior y que esté en estado "AUTORIZADO" tanto en el seguimiento actual como en el seguimiento posterior
    procedimiento_anterior = CIDProcedimiento.query.filter(
        CIDProcedimiento.revision == revision_anterior,
        CIDProcedimiento.seguimiento == "AUTORIZADO",
        CIDProcedimiento.seguimiento_posterior == "AUTORIZADO",
    ).first()
    form = CIDProcedimientoEditForm()
    if form.validate_on_submit():
        # Solo validar si se proporcionó un email
        elaboro_email = form.elaboro_email.data
        elaboro_nombre = form.elaboro_nombre.data
        if elaboro_email:  # Validar solo si hay algo en el campo
            try:
                elaboro = safe_email(elaboro_email)
            except ValueError:
                flash(f"El email '{elaboro_email}' no es válido.", "error")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id))
        else:
            elaboro = ""  # Si no se proporciona email, dejar vacío
        # Solo validar si se proporcionó un email
        reviso_email = form.reviso_email.data
        reviso_nombre = form.reviso_nombre.data
        if reviso_email:
            try:
                reviso = safe_email(reviso_email)
            except ValueError:
                flash(f"El email '{reviso_email}' no es válido.", "error")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id))
        else:
            reviso = ""  # Si no se proporciona email, dejar vacío
        # Solo validar si se proporcionó un email
        aprobo_email = form.aprobo_email.data
        aprobo_nombre = form.aprobo_nombre.data
        if aprobo_email:
            try:
                aprobo = safe_email(aprobo_email)
            except ValueError:
                flash(f"El email '{aprobo_email}' no es válido.", "error")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id))
        else:
            aprobo = ""  # Si no se proporciona email, dejar vacío
        registro = form.registros.data
        if registro is None:
            registros = {}
        else:
            registros = registro
        control = form.control_cambios.data
        if control is None:
            control_cambios = {}
        else:
            control_cambios = control
        # Obtener el valor del campo 'revision' del formulario
        revision = form.revision.data
        # Verificar si el campo 'revision' del formulario está vacío o es None.
        # Si es None, asignar el valor de la revisión actual del procedimiento (cid_procedimiento.revision).
        if revision is None:
            revision = cid_procedimiento.revision
        # Si el valor de la revisión del procedimiento también es None, asignar un valor predeterminado de 1.
        if revision is None:
            revision = 1
        # Asegurar que el campo codigo tenga un valor válido
        codigo = form.codigo.data
        if not codigo:  # Verificar si es None o una cadena vacía
            codigo = cid_procedimiento.codigo  # Mantener el valor original si no se envió uno nuevo
        cid_procedimiento.titulo_procedimiento = safe_string(form.titulo_procedimiento.data)
        cid_procedimiento.codigo = safe_clave(codigo)
        cid_procedimiento.revision = revision
        cid_procedimiento.fecha = form.fecha.data
        cid_procedimiento.objetivo = form.objetivo.data
        cid_procedimiento.alcance = form.alcance.data
        cid_procedimiento.documentos = form.documentos.data
        cid_procedimiento.definiciones = form.definiciones.data
        cid_procedimiento.responsabilidades = form.responsabilidades.data
        cid_procedimiento.desarrollo = form.desarrollo.data
        cid_procedimiento.registros = registros
        cid_procedimiento.elaboro_nombre = safe_string(elaboro_nombre, save_enie=True)
        cid_procedimiento.elaboro_puesto = safe_string(form.elaboro_puesto.data)
        cid_procedimiento.elaboro_email = elaboro_email if elaboro else ""
        cid_procedimiento.reviso_nombre = safe_string(reviso_nombre, save_enie=True)
        cid_procedimiento.reviso_puesto = safe_string(form.reviso_puesto.data)
        cid_procedimiento.reviso_email = reviso_email if reviso else ""
        cid_procedimiento.aprobo_nombre = safe_string(aprobo_nombre, save_enie=True)
        cid_procedimiento.aprobo_puesto = safe_string(form.aprobo_puesto.data)
        cid_procedimiento.aprobo_email = aprobo_email if aprobo else ""
        cid_procedimiento.control_cambios = control_cambios
        cid_procedimiento.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Procedimiento {cid_procedimiento.titulo_procedimiento}."),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Definir los valores de los campos del formulario
    form.titulo_procedimiento.data = cid_procedimiento.titulo_procedimiento
    form.codigo.data = cid_procedimiento.codigo
    form.revision.data = cid_procedimiento.revision
    form.cid_area.data = cid_procedimiento.cid_area
    form.fecha.data = cid_procedimiento.fecha
    form.objetivo.data = cid_procedimiento.objetivo
    form.alcance.data = cid_procedimiento.alcance
    form.documentos.data = cid_procedimiento.documentos
    form.definiciones.data = cid_procedimiento.definiciones
    form.responsabilidades.data = cid_procedimiento.responsabilidades
    form.desarrollo.data = cid_procedimiento.desarrollo
    form.registros.data = cid_procedimiento.registros
    form.elaboro_nombre.data = cid_procedimiento.elaboro_nombre
    form.elaboro_puesto.data = cid_procedimiento.elaboro_puesto
    form.elaboro_email.data = cid_procedimiento.elaboro_email
    form.reviso_nombre.data = cid_procedimiento.reviso_nombre
    form.reviso_puesto.data = cid_procedimiento.reviso_puesto
    form.reviso_email.data = cid_procedimiento.reviso_email
    form.aprobo_nombre.data = cid_procedimiento.aprobo_nombre
    form.aprobo_puesto.data = cid_procedimiento.aprobo_puesto
    form.aprobo_email.data = cid_procedimiento.aprobo_email
    form.control_cambios.data = cid_procedimiento.control_cambios
    # Para cargar el contenido de los QuillJS hay que convertir a JSON válido (por ejemplo, cambia True por true)
    objetivo_json = json.dumps(cid_procedimiento.objetivo)
    alcance_json = json.dumps(cid_procedimiento.alcance)
    documentos_json = json.dumps(cid_procedimiento.documentos)
    definiciones_json = json.dumps(cid_procedimiento.definiciones)
    responsabilidades_json = json.dumps(cid_procedimiento.responsabilidades)
    desarrollo_json = json.dumps(cid_procedimiento.desarrollo)
    registros_json = json.dumps(cid_procedimiento.registros)
    control_cambios_json = json.dumps(cid_procedimiento.control_cambios)
    return render_template(
        "cid_procedimientos/edit.jinja2",
        form=form,
        cid_procedimiento=cid_procedimiento,
        objetivo_json=objetivo_json,
        alcance_json=alcance_json,
        documentos_json=documentos_json,
        definiciones_json=definiciones_json,
        responsabilidades_json=responsabilidades_json,
        desarrollo_json=desarrollo_json,
        registros_json=registros_json,
        control_cambios_json=control_cambios_json,
        help_quill=help_quill("edit"),
        procedimiento_anterior=procedimiento_anterior,
    )


@cid_procedimientos.route("/cid_procedimientos/copiar_revision/<int:cid_procedimiento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def copiar_procedimiento_con_revision(cid_procedimiento_id):
    """Copiar CID Procedimiento con nueva revisión"""
    # Obtener el CID Procedimiento correspondiente o devolver error 404 si no existe
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    # Estados de seguimiento que no permiten crear una nueva revisión
    seguimientos_no_permitidos = ["EN ELABORACION", "ELABORADO", "EN REVISION", "REVISADO", "EN AUTORIZACION"]
    # Consultar las revisiones relacionadas con el procedimiento actual
    revisiones_relacionadas = CIDProcedimiento.query.filter(
        CIDProcedimiento.anterior_id == cid_procedimiento.id, CIDProcedimiento.seguimiento.in_(seguimientos_no_permitidos)
    ).all()
    # Asegurarse de que revisiones_relacionadas es una lista antes de intentar procesar
    if revisiones_relacionadas and not all(revision.estatus == "B" for revision in revisiones_relacionadas):
        flash("No se puede crear una nueva revisión porque ya hay una revisión en proceso.", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id))
    # Verificar que tanto seguimiento como seguimiento_posterior sean AUTORIZADO
    if cid_procedimiento.seguimiento != "AUTORIZADO" or cid_procedimiento.seguimiento_posterior != "AUTORIZADO":
        flash("No se puede copiar el procedimiento hasta que ambos seguimientos estén en 'AUTORIZADO'.", "danger")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id))
    # Obtener la última revisión
    ultima_revision = (
        CIDProcedimiento.query.filter_by(id=cid_procedimiento.id).order_by(CIDProcedimiento.revision.desc()).first()
    )
    # Crear un formulario para la nueva revisión
    form = CIDProcedimientosNewReview()
    # Si el formulario ha sido enviado y es válido
    if form.validate_on_submit():
        now = datetime.now(timezone.utc)

        # Manejo de emails
        try:
            reviso_email = safe_email(form.reviso_email.data) if form.reviso_email.data else ""
            aprobo_email = safe_email(form.aprobo_email.data) if form.aprobo_email.data else ""
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id))

        # Crear una nueva copia del procedimiento con los datos actualizados
        nueva_copia = CIDProcedimiento(
            autoridad=cid_procedimiento.autoridad,
            usuario=current_user,
            titulo_procedimiento=safe_string(form.titulo_procedimiento.data),
            codigo=cid_procedimiento.codigo,
            revision=ultima_revision.revision + 1,
            fecha=form.fecha.data or now,
            objetivo=cid_procedimiento.objetivo,
            alcance=cid_procedimiento.alcance,
            documentos=cid_procedimiento.documentos,
            definiciones=cid_procedimiento.definiciones,
            responsabilidades=cid_procedimiento.responsabilidades,
            desarrollo=cid_procedimiento.desarrollo,
            registros=cid_procedimiento.registros,
            elaboro_nombre=cid_procedimiento.elaboro_nombre,
            elaboro_puesto=cid_procedimiento.elaboro_puesto,
            elaboro_email=cid_procedimiento.elaboro_email,
            reviso_nombre=form.reviso_nombre.data,
            reviso_puesto=cid_procedimiento.reviso_puesto,
            reviso_email=reviso_email,
            aprobo_nombre=form.aprobo_nombre.data,
            aprobo_puesto=cid_procedimiento.aprobo_puesto,
            aprobo_email=aprobo_email,
            control_cambios=cid_procedimiento.control_cambios,
            seguimiento="EN ELABORACION",
            seguimiento_posterior="EN ELABORACION",
            cadena=cid_procedimiento.cadena + 1,
            anterior_id=cid_procedimiento.id,
            firma="",
            archivo="",
            url="",
            cid_area=cid_procedimiento.cid_area,
            procedimiento_anterior_autorizado_id=cid_procedimiento.id,
        )
        # Guardar la nueva copia en la base de datos
        nueva_copia.save()
        # Bitácora y redirección a la vista de detalle
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva revisión del procedimiento {cid_procedimiento.titulo_procedimiento}."),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=nueva_copia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        # Redireccionar a la edicion del nuevo id
        return redirect(url_for("cid_procedimientos.edit", cid_procedimiento_id=nueva_copia.id))
    # Llenar el formulario con los datos del procedimiento original
    form.titulo_procedimiento.data = cid_procedimiento.titulo_procedimiento
    form.codigo.data = cid_procedimiento.codigo
    form.revision.data = (ultima_revision.revision + 1) if ultima_revision else 1
    form.fecha.data = datetime.now(timezone.utc)
    form.reviso_nombre.data = cid_procedimiento.reviso_nombre
    form.reviso_puesto.data = cid_procedimiento.reviso_puesto
    form.reviso_email.data = cid_procedimiento.reviso_email
    form.aprobo_nombre.data = cid_procedimiento.aprobo_nombre
    form.aprobo_puesto.data = cid_procedimiento.aprobo_puesto
    form.aprobo_email.data = cid_procedimiento.aprobo_email
    # Renderizar la plantilla con el formulario y la información del procedimiento
    return render_template("cid_procedimientos/new_revision.jinja2", form=form, cid_procedimiento=cid_procedimiento)


# Cambiar el Área del procedimiento
@cid_procedimientos.route("/cid_procedimientos/cambiar_area/<int:cid_procedimiento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def cambiar_area(cid_procedimiento_id):
    """Cambiar Área Procedimiento"""
    # Consultar el procedimiento
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    form = CIDProcedimientoCambiarAreaForm()
    if form.validate_on_submit():
        cid_procedimiento.cid_area_id = form.cid_area.data
        cid_procedimiento.save()
        # Registrar en bitacora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Cambiada el Área del Procedimiento {cid_procedimiento_id}."),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Mostrar
    form.titulo_procedimiento.data = cid_procedimiento.titulo_procedimiento
    form.codigo.data = cid_procedimiento.codigo
    form.cid_area_original.data = cid_procedimiento.cid_area.nombre
    form.cid_area.data = cid_procedimiento.cid_area_id
    return render_template("cid_procedimientos/cambiar_area.jinja2", form=form, cid_procedimiento=cid_procedimiento)


def validate_json_quill_not_empty(data):
    """Validar que un JSON de Quill no esté vacío"""
    if not isinstance(data, dict):
        return False
    if not "ops" in data:
        return False
    try:
        if data["ops"][0]["insert"].strip() == "":
            return False
        return True
    except KeyError:
        return False


@cid_procedimientos.route("/cid_procedimientos/firmar/<int:cid_procedimiento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def sign_for_maker(cid_procedimiento_id):
    """Firmar"""
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    if cid_procedimiento.usuario_id != current_user.id:
        abort(403)  # Acceso no autorizado, solo el propietario puede firmarlo
    # Validar objetivo
    objetivo_es_valido = validate_json_quill_not_empty(cid_procedimiento.objetivo)
    # Validar alcance
    alcance_es_valido = validate_json_quill_not_empty(cid_procedimiento.alcance)
    # Validar documentos
    documentos_es_valido = validate_json_quill_not_empty(cid_procedimiento.documentos)
    # Validar definiciones
    definiciones_es_valido = validate_json_quill_not_empty(cid_procedimiento.definiciones)
    # Validar responsabilidades
    responsabilidades_es_valido = validate_json_quill_not_empty(cid_procedimiento.responsabilidades)
    # Validar desarrollo
    desarrollo_es_valido = validate_json_quill_not_empty(cid_procedimiento.desarrollo)
    # Validar registros
    registros_es_valido = cid_procedimiento.registros
    # Validar control_cambios
    control_cambios_es_valido = cid_procedimiento.control_cambios
    # Validar elaboro
    elaboro_es_valido = False
    if cid_procedimiento.elaboro_email != "":
        elaboro = Usuario.query.filter_by(email=cid_procedimiento.elaboro_email).first()
        # Validar que tenga el rol SICGD DUENO DEL PROCESO
        elaboro_es_valido = elaboro is not None  # TODO: Validar que tenga el rol SICGD DUENO DE PROCESO
    # Validar reviso
    reviso_es_valido = False
    if cid_procedimiento.reviso_email != "":
        reviso = Usuario.query.filter_by(email=cid_procedimiento.reviso_email).first()
        reviso_es_valido = reviso is not None  # TODO: Validar que tenga el rol SICGD DIRECTOR O JEFE
    # Validar autorizo
    aprobo_es_valido = False
    if cid_procedimiento.aprobo_email != "":
        aprobo = Usuario.query.filter_by(email=cid_procedimiento.aprobo_email).first()
        aprobo_es_valido = aprobo is not None  # TODO: Validar que tenga el rol SICGD DIRECTOR O JEFE
    # Poner barreras para prevenir que se firme si está incompleto
    if cid_procedimiento.firma != "":
        flash("Este procedimiento ya ha sido firmado.", "warning")
    elif not objetivo_es_valido:
        flash("Objetivo no pasa la validación.", "warning")
    elif not alcance_es_valido:
        flash("Alcance no pasa la validación.", "warning")
    elif not documentos_es_valido:
        flash("Documentos no pasa la validación.", "warning")
    elif not definiciones_es_valido:
        flash("Definiciones no pasa la validación.", "warning")
    elif not responsabilidades_es_valido:
        flash("Responsabilidades no pasa la validación.", "warning")
    elif not desarrollo_es_valido:
        flash("Desarrollo no pasa la validación.", "warning")
    elif not registros_es_valido:
        flash("Registros no pasa la validación.", "warning")
    elif not control_cambios_es_valido:
        flash("Control de Cambios no pasa la validación.", "warning")
    elif not elaboro_es_valido:
        flash("Quien elabora no pasa la validación.", "warning")
    elif not reviso_es_valido:
        flash("Quien revisa no pasa la validación.", "warning")
    elif not aprobo_es_valido:
        flash("Quien aprueba no pasa la validación.", "warning")
    else:
        tarea = current_user.launch_task(
            comando="cid_procedimientos.tasks.crear_pdf",
            mensaje=f"Se esta creando PDF de {cid_procedimiento.titulo_procedimiento}",
            usuario_id=current_user.id,
            cid_procedimiento_id=cid_procedimiento.id,
            accept_reject_url=url_for("cid_procedimientos.accept_reject", cid_procedimiento_id=cid_procedimiento.id),
        )
        flash(f"{tarea.mensaje} y esta corriendo en el fondo. Esta página se va recargar en 10 segundos...", "info")
    return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id))


@cid_procedimientos.route("/cid_procedimientos/aceptar_rechazar/<int:cid_procedimiento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def accept_reject(cid_procedimiento_id):
    """Aceptar o Rechazar un Procedimiento"""
    original = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    # Validar que NO haya sido eliminado
    if original.estatus != "A":
        flash("Este procedimiento no es activo.", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
    # Validar que este procedimiento este elaborado o revisado
    if not original.seguimiento in ["ELABORADO", "REVISADO"]:
        flash("Este procedimiento no puede ser aceptado.", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
    # Validar que NO haya sido YA aceptado
    if original.seguimiento_posterior in ["EN REVISION", "EN AUTORIZACION"]:
        flash(
            "Este procedimiento ya fue aceptado. Por favor vaya al listado de procedimientos PROPIOS para que pueda continuar con su revisión o autorización.",
            "warning",
        )
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
    # Validación para procedimientos AUTORIZADO y no poder aceptar de nuevo
    if original.seguimiento == "REVISADO" and original.seguimiento_posterior == "AUTORIZADO":
        flash("Este procedimiento ya ha sido AUTORIZADO y no puede ser aceptado nuevamente.", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))

    form = CIDProcedimientoAcceptRejectForm()
    if form.validate_on_submit():
        # Si fue aceptado
        if form.aceptar.data is True:
            # Deberian definirse estos campos
            nuevo_seguimiento = None
            nuevo_seguimiento_posterior = None
            nuevo_usuario = None
            # Si este procedimiento fue elaborado, sigue revisarlo
            if original.seguimiento == "ELABORADO":
                usuario = Usuario.query.filter_by(email=original.reviso_email).first()
                if usuario is None:
                    flash(f"No fue encontrado el usuario con e-mail {original.reviso_email}", "danger")
                    return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
                nuevo_seguimiento = "EN REVISION"
                nuevo_seguimiento_posterior = "EN REVISION"
                nuevo_usuario = usuario
            # Si este procedimiento fue revisado, sigue autorizarlo
            if original.seguimiento == "REVISADO":
                usuario = Usuario.query.filter_by(email=original.aprobo_email).first()
                if usuario is None:
                    flash(f"No fue encontrado el usuario con e-mail {original.aprobo_email}", "danger")
                    return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
                nuevo_seguimiento = "EN AUTORIZACION"
                nuevo_seguimiento_posterior = "EN AUTORIZACION"
                nuevo_usuario = usuario
            # Validar que se hayan definido estos campos
            if nuevo_seguimiento is None:
                flash("No se definio el seguimiento.", "danger")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
            if nuevo_seguimiento_posterior is None:
                flash("No se definio el seguimiento posterior.", "danger")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
            if nuevo_usuario is None:
                flash("No se definio el usuario.", "danger")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
            # Validar que NO haya sido YA aceptado
            if original.seguimiento_posterior in ["EN REVISION", "EN AUTORIZACION"]:
                flash("Este procedimiento ya fue aceptado.", "warning")
                return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
            # Crear un nuevo registro
            nuevo = CIDProcedimiento(
                autoridad=original.autoridad,
                usuario=nuevo_usuario,
                titulo_procedimiento=safe_string(original.titulo_procedimiento),
                codigo=original.codigo,
                revision=original.revision,
                fecha=original.fecha,
                objetivo=original.objetivo,
                alcance=original.alcance,
                documentos=original.documentos,
                definiciones=original.definiciones,
                responsabilidades=original.responsabilidades,
                desarrollo=original.desarrollo,
                registros=original.registros,
                elaboro_nombre=original.elaboro_nombre,
                elaboro_puesto=original.elaboro_puesto,
                elaboro_email=original.elaboro_email,
                reviso_nombre=original.reviso_nombre,
                reviso_puesto=original.reviso_puesto,
                reviso_email=original.reviso_email,
                aprobo_nombre=original.aprobo_nombre,
                aprobo_puesto=original.aprobo_puesto,
                aprobo_email=original.aprobo_email,
                control_cambios=original.control_cambios,
                seguimiento=nuevo_seguimiento,
                seguimiento_posterior=nuevo_seguimiento_posterior,
                cadena=original.cadena + 1,
                anterior_id=original.id,
                firma="",
                archivo="",
                url="",
                cid_area=original.cid_area,
                procedimiento_anterior_autorizado_id=original.procedimiento_anterior_autorizado_id,
            ).save()
            # Actualizar el anterior
            if original.seguimiento == "ELABORADO":
                # Cambiar el seguimiento posterior del procedimiento elaborado
                anterior = CIDProcedimiento.query.get(cid_procedimiento_id)
                anterior.seguimiento_posterior = "EN REVISION"
                anterior.save()
            if original.seguimiento == "REVISADO":
                # Cambiar el seguimiento posterior del procedimiento revisado
                anterior = CIDProcedimiento.query.get(cid_procedimiento_id)
                anterior.seguimiento_posterior = "EN AUTORIZACION"
                anterior.save()
            # Mover los formatos del procedimiento anterior al nuevo
            if original.seguimiento == "ELABORADO" or original.seguimiento == "REVISADO":
                for cid_formato in anterior.cid_formatos:
                    cid_formato.procedimiento_id = nuevo.id
                    cid_formato.save()

            # Bitacora
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Aceptado el Procedimiento {nuevo.titulo_procedimiento}."),
                url=url_for("cid_procedimientos.detail", cid_procedimiento_id=nuevo.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
        # Fue rechazado
        if form.rechazar.data is True:
            # Preguntar porque fue rechazado
            flash("Usted ha rechazado revisar/autorizar este procedimiento.", "success")
        # Ir al detalle del procedimiento
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=original.id))
    # Mostrar el formulario
    form.titulo_procedimiento.data = original.titulo_procedimiento
    form.codigo.data = original.codigo
    form.revision.data = original.revision
    form.seguimiento.data = original.seguimiento
    form.seguimiento_posterior.data = original.seguimiento_posterior
    form.elaboro_nombre.data = original.elaboro_nombre
    form.reviso_nombre.data = original.reviso_nombre
    form.url.data = original.url
    return render_template(
        "cid_procedimientos/accept_reject.jinja2",
        form=form,
        cid_procedimiento=original,
    )


def help_quill(seccion: str):
    """Cargar archivo de ayuda"""
    archivo_ayuda = open("hercules/static/json/quill_help.json", "r")
    data = json.load(archivo_ayuda)
    archivo_ayuda.close()
    return render_template(
        "quill_help.jinja2",
        titulo=data["titulo"],
        descripcion=data["descripcion"],
        secciones=data["secciones"],
        seccion_id=seccion,
    )


@cid_procedimientos.route("/cid_procedimientos/revisores_autorizadores_json", methods=["POST"])
def query_revisores_autorizadores_json():
    """Proporcionar el JSON de revisores para elegir con un Select2"""
    usuarios = (
        Usuario.query.join(UsuarioRol, Usuario.id == UsuarioRol.usuario_id)
        .join(Rol, UsuarioRol.rol_id == Rol.id)
        .filter(or_(Rol.nombre == ROL_DIRECTOR_JEFE, Rol.nombre == ROL_COORDINADOR))
    )
    # Filtrar por email si se proporciona searchString
    search_string = request.form.get("searchString", "")
    if search_string:
        usuarios = usuarios.filter(Usuario.email.contains(safe_email(search_string, search_fragment=True)))
    # Filtrar solo usuarios activos
    usuarios = usuarios.filter(Usuario.estatus == "A")
    # Preparar los resultados
    results = [
        {"id": usuario.email, "text": usuario.email, "nombre": usuario.nombre}
        for usuario in usuarios.order_by(Usuario.email).limit(10).all()
    ]
    return {"results": results, "pagination": {"more": False}}


@cid_procedimientos.route("/cid_procedimientos/eliminar/<int:cid_procedimiento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(cid_procedimiento_id):
    """Eliminar CID Procedimiento"""
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    # Verificación de permisos
    if not (current_user.can_admin(MODULO) or cid_procedimiento.usuario_id == current_user.id):
        abort(403)  # Acceso no autorizado, solo administradores o el propietario puede eliminarlo

    # Restricciones basadas en seguimiento y estatus
    elif not (
        current_user.can_admin(MODULO) or cid_procedimiento.seguimiento in ["EN ELABORACION", "EN REVISION", "EN AUTORIZACION"]
    ):
        flash(f"No puede eliminarlo porque su seguimiento es {cid_procedimiento.seguimiento}.")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento_id))
    elif cid_procedimiento.estatus == "A":
        # Cambia el estado a 'CANCELADO' según el seguimiento
        if cid_procedimiento.seguimiento == "EN ELABORACION":
            cid_procedimiento.seguimiento = "CANCELADO POR ELABORADOR"
        elif cid_procedimiento.seguimiento == "EN REVISION":
            cid_procedimiento.seguimiento = "CANCELADO POR REVISOR"
        elif cid_procedimiento.seguimiento == "EN AUTORIZACION":
            cid_procedimiento.seguimiento = "CANCELADO POR AUTORIZADOR"
        cid_procedimiento.delete()

        # Eliminar los cif_formatos de cada cid_procedimiento
        for cid_formato in cid_procedimiento.cid_formatos:
            cid_formato.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Procedimiento {cid_procedimiento.titulo_procedimiento}."),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento_id))


@cid_procedimientos.route("/cid_procedimientos/recuperar/<int:cid_procedimiento_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(cid_procedimiento_id):
    """Recuperar CID Procedimiento"""
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    if not (current_user.can_admin(MODULO) or cid_procedimiento.usuario_id == current_user.id):
        abort(403)  # Acceso no autorizado, solo administradores o el propietario puede recuperarlo
    if not (
        current_user.can_admin(MODULO)
        or cid_procedimiento.seguimiento in ["CANCELADO POR ELABORADOR", "CANCELADO POR REVISOR", "CANCELADO POR AUTORIZADOR"]
    ):
        flash(f"No puede recuperarlo porque su seguimiento es {cid_procedimiento.seguimiento}.")
    elif cid_procedimiento.estatus == "B":
        if cid_procedimiento.seguimiento == "CANCELADO POR ELABORADOR":
            cid_procedimiento.seguimiento = "EN ELABORACION"
        elif cid_procedimiento.seguimiento == "CANCELADO POR REVISOR":
            cid_procedimiento.seguimiento = "EN REVISION"
        elif cid_procedimiento.seguimiento == "CANCELADO POR AUTORIZADOR":
            cid_procedimiento.seguimiento = "EN AUTORIZACION"
        cid_procedimiento.recover()
        # Recuperar los cid_formatos de cada cid_procedimiento
        for cid_formato in cid_procedimiento.cid_formatos:
            cid_formato.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Procedimiento {cid_procedimiento.titulo_procedimiento}."),
            url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento_id))


@cid_procedimientos.route("/cid_procedimientos/exportar_lista_maestra_xlsx")
@permission_required(MODULO, Permiso.VER)
def exportar_xlsx():
    """Lanzar tarea en el fondo para exportar la Lista Maestra a un archivo XLSX"""
    tarea = current_user.launch_task(
        comando="cid_procedimientos.tasks.lanzar_exportar_xlsx",
        mensaje="Exportando la Lista Maestra a un archivo XLSX...",
    )
    flash("Se ha lanzado esta tarea en el fondo. Esta página se va a recargar en 30 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@cid_procedimientos.route("/cid_procedimientos/tablero")
@permission_required(MODULO, Permiso.VER)
def dashboard():
    """Tablero de Procedimientos"""

    # Definir valores por defecto
    current_user_roles = set(current_user.get_roles())
    mostrar_boton_exportar_lista_maestra_xlsx = False

    # Si es administrador o tiene el rol SICGD AUDITOR o el rol SICGD COORDINADOR, mostrar el botón de exportar lista maestra
    if current_user.can_admin(MODULO) or current_user_roles.intersection(("SICGD AUDITOR", "SICGD COORDINADOR")):
        mostrar_boton_exportar_lista_maestra_xlsx = True

    # Consultar las cantidades de procedimientos con seguimiento AUTORIZADO por área
    consulta = (
        database.session.query(
            CIDArea.clave,
            CIDArea.nombre,
            func.count(CIDProcedimiento.id).label("cantidad"),
        )
        .select_from(CIDProcedimiento)
        .join(CIDArea)
        .filter(CIDProcedimiento.seguimiento == "AUTORIZADO")
        .filter(CIDProcedimiento.estatus == "A")
        .group_by(CIDArea.clave, CIDArea.nombre)
        .order_by(CIDArea.nombre)
        .all()
    )

    # Crear un listado de tuplas con el nombre del área y la cantidad de procedimientos
    cantidad_procedimientos_por_area = [(clave, nombre, cantidad) for clave, nombre, cantidad in consulta]

    # Entregar
    return render_template(
        "cid_procedimientos/dashboard.jinja2",
        cantidad_procedimientos_por_area=cantidad_procedimientos_por_area,
        titulo="Tablero de Procedimientos autorizados",
        mostrar_boton_exportar_lista_maestra_xlsx=mostrar_boton_exportar_lista_maestra_xlsx,
    )


@cid_procedimientos.route("/cid_procedimientos/baja/<int:cid_procedimiento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def archivar_procedimiento(cid_procedimiento_id):
    """Archivar un procedimiento y cambiara su seguimiento a ARCHIVADO"""
    if ROL_COORDINADOR not in current_user.get_roles() and ROL_ADMINISTRADOR not in current_user.get_roles():
        flash(f"Solo puede archivar el rol {ROL_ADMINISTRADOR} o {ROL_COORDINADOR}.", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento_id))
    # Validar procedimientos
    cid_procedimiento = CIDProcedimiento.query.get_or_404(cid_procedimiento_id)
    if cid_procedimiento.estatus != "A":
        flash("El procedimiento seleccionado está eliminado.", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento_id))
    if cid_procedimiento.seguimiento == "ARCHIVADO" or cid_procedimiento.seguimiento_posterior == "ARCHIVADO":
        flash("El procedimiento se encuentra ARCHIVADO.", "warning")
        return redirect(url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento_id))

    # Archivar el procedimiento actual y todos sus seguimientos anteriores
    procedimiento_actual = cid_procedimiento
    # Cambiamos el seguimiento del procedimiento actual a "ARCHIVADO"
    procedimiento_actual.seguimiento = "ARCHIVADO"
    # Iniciamos un bucle para recorrer y archivar todos los procedimientos anteriores
    while procedimiento_actual:
        # Cambiamos el seguimiento_posterior del procedimiento actual a "ARCHIVADO"
        procedimiento_actual.seguimiento_posterior = "ARCHIVADO"
        # Guardamos los cambios en la base de datos
        procedimiento_actual.save()
        # Obtenemos el procedimiento anterior mediante el campo `anterior_id` para seguir recorriendo la cadena de procedimientos anteriores
        procedimiento_actual = CIDProcedimiento.query.filter_by(id=procedimiento_actual.anterior_id).first()
    # Guardado de acciones en bitacora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(
            f"Se archiva el procedimiento {cid_procedimiento.codigo}  {cid_procedimiento.titulo_procedimiento} y sus procedimientos anteriores."
        ),
        url=url_for("cid_procedimientos.detail", cid_procedimiento_id=cid_procedimiento.id),
    ).save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("cid_procedimientos.list_active"))
