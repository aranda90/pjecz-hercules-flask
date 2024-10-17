"""
Financieros Vales, vistas
"""

import json
import re
from datetime import datetime, time

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pytz import timezone

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.fin_vales.forms import (
    FinValeCancel2RequestForm,
    FinValeCancel3AuthorizeForm,
    FinValeEditForm,
    FinValeStep1CreateForm,
    FinValeStep2RequestForm,
    FinValeStep3AuthorizeForm,
    FinValeStep4DeliverForm,
    FinValeStep5AttachmentsForm,
    FinValeStep6ArchiveForm,
)
from hercules.blueprints.fin_vales.models import FinVale
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.roles.models import Rol
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.usuarios_roles.models import UsuarioRol
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_email, safe_message, safe_string

# Roles que deben estar en la base de datos
ROL_SOLICITANTES = "FINANCIEROS SOLICITANTES"
ROL_AUTORIZANTES = "FINANCIEROS AUTORIZANTES"
ROL_ASISTENTES = "FINANCIEROS ASISTENTES"
ROLES_PUEDEN_VER = (ROL_SOLICITANTES, ROL_AUTORIZANTES, ROL_ASISTENTES)
ROLES_PUEDEN_IMPRIMIR = (ROL_AUTORIZANTES, ROL_ASISTENTES)

# Zona horaria
TIMEZONE = "America/Mexico_City"
local_tz = timezone(TIMEZONE)
medianoche = time.min

MODULO = "FIN VALES"

fin_vales = Blueprint("fin_vales", __name__, template_folder="templates")


@fin_vales.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@fin_vales.route("/fin_vales/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de FinVale"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = FinVale.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(FinVale.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(FinVale.estatus == "A")
    if "fin_vale_id" in request.form:
        try:
            consulta = consulta.filter(FinVale.id == int(request.form["fin_vale_id"]))
        except ValueError:
            pass
    else:
        if "usuario_id" in request.form:
            consulta = consulta.filter(FinVale.usuario_id == request.form["usuario_id"])
        if "estado" in request.form:
            consulta = consulta.filter(FinVale.estado == request.form["estado"])
        if "justificacion" in request.form:
            justificacion = safe_string(request.form["justificacion"], do_unidecode=False, save_enie=True, to_uppercase=False)
            if justificacion != "":
                consulta = consulta.filter(FinVale.justificacion.ilike(f"%{justificacion}%"))
        creado_desde = None
        creado_hasta = None
        if "creado_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["creado_desde"]):
            creado_desde = request.form["creado_desde"]
        if "creado_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["creado_hasta"]):
            creado_hasta = request.form["creado_hasta"]
        if creado_desde and creado_hasta and creado_desde > creado_hasta:
            creado_desde, creado_hasta = creado_hasta, creado_desde
        if creado_desde:
            year, month, day = map(int, creado_desde.split("-"))
            creado_desde_dt = datetime(year=year, month=month, day=day, hour=0, minute=0, second=0)
            consulta = consulta.filter(FinVale.creado >= creado_desde_dt)
        if creado_hasta:
            year, month, day = map(int, creado_hasta.split("-"))
            creado_hasta_dt = datetime(year=year, month=month, day=day, hour=23, minute=59, second=59)
            consulta = consulta.filter(FinVale.creado <= creado_hasta_dt)
    # Ordenar y paginar
    registros = consulta.order_by(FinVale.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("fin_vales.detail", fin_vale_id=resultado.id),
                },
                "creado": resultado.creado.strftime("%Y-%m-%dT%H:%M:%S"),
                "usuario": {
                    "email": resultado.usuario.email,
                    "nombre": resultado.usuario.nombre,
                },
                "justificacion": resultado.justificacion,
                "monto": resultado.monto,
                "estado": resultado.estado,
                "acciones": {
                    "editar_url": url_for("fin_vales.edit", fin_vale_id=resultado.id) if resultado.estado == "CREADO" else None,
                    "imprimir_url": (
                        url_for("fin_vales.print", fin_vale_id=resultado.id)
                        if resultado.estado in ["SOLICITADO", "AUTORIZADO"]
                        else None
                    ),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@fin_vales.route("/fin_vales")
def list_active():
    """Listado de FinVale activos"""

    # Definir filtros por defecto, solo para el usuario actual
    filtros = {"usuario_id": current_user.id, "estatus": "A"}
    titulo = f"Vales de Gasolina de {current_user.nombre}"

    # Si es ADMINISTRADOR y viene usuario_id en la URL, agregar a los filtros
    if current_user.can_admin(MODULO):
        try:
            usuario_id = int(request.args.get("usuario_id"))
            usuario = Usuario.query.get_or_404(usuario_id)
            filtros = {"estatus": "A", "usuario_id": usuario_id}
            titulo = f"Administar los Vales de Gasolina de {usuario.nombre}"
        except (TypeError, ValueError):
            filtros = {"estatus": "A"}
            titulo = "Administrar todos los Vales de Gasolina"

    # Si es ROL_ASISTENTES, mostrar TODOS los vales de su oficina
    elif ROL_ASISTENTES in current_user.get_roles():
        filtros = {"estatus": "A"}
        titulo = "Asistir en Vales de Gasolina"

    # Si es ROL_AUTORIZANTES, mostrar Vales con estado SOLICITADO
    elif ROL_AUTORIZANTES in current_user.get_roles():
        filtros = {"estatus": "A", "estado": "SOLICITADO"}
        titulo = "Vales de Gasolina por autorizar"

    # Si es ROL_SOLICITANTES, mostrar Vales con estado CREADO
    elif ROL_SOLICITANTES in current_user.get_roles():
        filtros = {"estatus": "A", "estado": "CREADO"}
        titulo = "Vales de Gasolina por solicitar"

    # Entregar
    return render_template(
        "fin_vales/list.jinja2",
        filtros=json.dumps(filtros),
        titulo=titulo,
        estatus="A",
    )


@fin_vales.route("/fin_vales/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de FinVale inactivos"""
    return render_template(
        "fin_vales/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Vales inactivos",
        estatus="B",
    )


@fin_vales.route("/fin_vales/<int:fin_vale_id>")
def detail(fin_vale_id):
    """Detalle de un FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)

    # Inicializar las variables de la efirma por defecto
    efirma_sello_digital = None
    efirma_url = None
    efirma_qr_url = None

    # Si el estado es SOLICITADO
    if fin_vale.estado == "SOLICITADO":
        efirma_sello_digital = fin_vale.solicito_efirma_sello_digital
        efirma_url = fin_vale.solicito_efirma_url
        efirma_qr_url = fin_vale.solicito_efirma_qr_url

    # Si el estado es AUTORIZADO
    if fin_vale.estado == "AUTORIZADO":
        efirma_sello_digital = fin_vale.autorizo_efirma_sello_digital
        efirma_url = fin_vale.autorizo_efirma_url
        efirma_qr_url = fin_vale.autorizo_efirma_qr_url

    # Inicializar la variable de si puede verlo
    puede_verlo = False

    # Si es administrador, puede verlo
    if current_user.can_admin(MODULO):
        puede_verlo = True

    # Si tiene uno de los roles que pueden verlo y esta activo, puede verlo
    if set(current_user.get_roles()).intersection(ROLES_PUEDEN_VER) and fin_vale.estatus == "A":
        puede_verlo = True

    # Si es el usuario que lo creo y esta activo, puede verlo
    if fin_vale.usuario_id == current_user.id and fin_vale.estatus == "A":
        puede_verlo = True

    # Si puede verlo
    if puede_verlo:
        return render_template(
            "fin_vales/detail.jinja2",
            fin_vale=fin_vale,
            efirma_sello_digital=efirma_sello_digital,
            efirma_url=efirma_url,
            efirma_qr_url=efirma_qr_url,
        )

    # No puede verlo
    flash("No tiene permiso para ver este vale.", "warning")
    return redirect(url_for("fin_vales.list_active"))


@fin_vales.route("/fin_vales/imprimir/<int:fin_vale_id>")
def print(fin_vale_id):
    """Imprimir un FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)

    # Determinar el sello digital y la URL de la firma electronica
    efirma_sello_digital = None
    efirma_url = None
    efirma_qr_url = None
    efirma_motivo = None

    # Si el estado es...
    if fin_vale.estado == "SOLICITADO":
        efirma_sello_digital = fin_vale.solicito_efirma_sello_digital
        efirma_url = fin_vale.solicito_efirma_url
        efirma_qr_url = fin_vale.solicito_efirma_qr_url
    elif fin_vale.estado == "CANCELADO POR SOLICITANTE":
        efirma_sello_digital = fin_vale.solicito_efirma_sello_digital
        efirma_url = fin_vale.solicito_efirma_url
        efirma_qr_url = fin_vale.solicito_efirma_qr_url
        efirma_motivo = fin_vale.solicito_cancelo_motivo
    elif fin_vale.estado == "AUTORIZADO":
        efirma_sello_digital = fin_vale.autorizo_efirma_sello_digital
        efirma_url = fin_vale.autorizo_efirma_url
        efirma_qr_url = fin_vale.autorizo_efirma_qr_url
    elif fin_vale.estado == "CANCELADO POR AUTORIZANTE":
        efirma_sello_digital = fin_vale.autorizo_efirma_sello_digital
        efirma_url = fin_vale.autorizo_efirma_url
        efirma_qr_url = fin_vale.autorizo_efirma_qr_url
        efirma_motivo = fin_vale.autorizo_cancelo_motivo

    # Validar que pueda verlo
    puede_imprimirlo = False

    # Si es administrador, puede imprimirlo
    if current_user.can_admin(MODULO):
        puede_imprimirlo = True

    # Si tiene uno de los roles que pueden imprimir y esta activo, puede imprimirlo
    if set(current_user.get_roles()).intersection(ROLES_PUEDEN_IMPRIMIR) and fin_vale.estatus == "A":
        puede_imprimirlo = True

    # Si es el usuario que lo creo y esta activo, puede imprimirlo
    if fin_vale.usuario_id == current_user.id and fin_vale.estatus == "A":
        puede_imprimirlo = True

    # Si puede imprimirlo
    if puede_imprimirlo:
        # Cortar las lineas del sello digital insertando saltos de linea cada 40 caracteres
        if efirma_sello_digital is not None:
            efirma_sello_digital = "<br>".join(
                [efirma_sello_digital[i : i + 40] for i in range(0, len(efirma_sello_digital), 40)]
            )
        # Mostrar la plantilla para imprimir
        return render_template(
            "fin_vales/print.jinja2",
            fin_vale=fin_vale,
            efirma_sello_digital=efirma_sello_digital,
            efirma_url=efirma_url,
            efirma_qr_url=efirma_qr_url,
            efirma_motivo=efirma_motivo,
        )

    # No puede imprimirlo
    flash("No tiene permiso para imprimir este Vale", "warning")
    return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))


@fin_vales.route("/fin_vales/usuarios_json", methods=["POST"])
def query_usuarios_json():
    """Proporcionar el JSON de usuarios para elegir con un Select2"""
    usuarios = Usuario.query.filter(Usuario.estatus == "A")
    if "searchString" in request.form:
        email = safe_email(request.form["searchString"], search_fragment=True)
        if email != "":
            usuarios = usuarios.filter(Usuario.email.contains(email))
    resultados = []
    for usuario in usuarios.order_by(Usuario.email).limit(10).all():
        resultados.append({"id": usuario.email, "text": usuario.email})
    return {"results": resultados, "pagination": {"more": False}}


@fin_vales.route("/fin_vales/solicitantes_json", methods=["POST"])
def query_solicitantes_json():
    """Proporcionar el JSON de solicitantes para elegir con un Select2"""
    solicitantes = (
        Usuario.query.select_from(Usuario)
        .join(UsuarioRol)
        .join(Rol)
        .where(UsuarioRol.usuario_id == Usuario.id)
        .where(UsuarioRol.rol_id == Rol.id)
        .filter(Rol.nombre == ROL_SOLICITANTES)
    )
    if "searchString" in request.form:
        email = safe_email(request.form["searchString"], search_fragment=True)
        if email != "":
            solicitantes = solicitantes.filter(Usuario.email.contains(email))
    solicitantes = solicitantes.filter(Usuario.estatus == "A")
    resultados = []
    for usuario in solicitantes.order_by(Usuario.email).limit(10).all():
        resultados.append({"id": usuario.email, "text": usuario.email})
    return {"results": resultados, "pagination": {"more": False}}


@fin_vales.route("/fin_vales/autorizantes_json", methods=["POST"])
def query_autorizantes_json():
    """Proporcionar el JSON de autorizantes para elegir con un Select2"""
    autorizantes = (
        Usuario.query.select_from(Usuario)
        .join(UsuarioRol)
        .join(Rol)
        .where(UsuarioRol.usuario_id == Usuario.id)
        .where(UsuarioRol.rol_id == Rol.id)
        .filter(Rol.nombre == ROL_AUTORIZANTES)
    )
    if "searchString" in request.form:
        email = safe_email(request.form["searchString"], search_fragment=True)
        if email != "":
            autorizantes = autorizantes.filter(Usuario.email.contains(email))
    autorizantes = autorizantes.filter(Usuario.estatus == "A")
    resultados = []
    for usuario in autorizantes.order_by(Usuario.email).limit(10).all():
        resultados.append({"id": usuario.email, "text": usuario.email})
    return {"results": resultados, "pagination": {"more": False}}


@fin_vales.route("/fin_vales/usuario_json", methods=["POST"])
def query_usuario_json():
    """Proporcionar el JSON con los datos de un usuario, cuando al editar se elije otro"""
    usuario_identity = safe_email(request.form["email"])
    if usuario_identity == "":
        return {"nombre": "", "email": ""}
    usuario = Usuario.find_by_identity(usuario_identity)
    if usuario is None:
        return {"nombre": "", "email": ""}
    return {"nombre": usuario.nombre, "email": usuario.email}


@fin_vales.route("/fin_vales/edicion/<int:fin_vale_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(fin_vale_id):
    """Editar un FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)

    # Validar que el estatus sea A
    if fin_vale.estatus != "A":
        flash("No puede editar este vale porque esta eliminado", "warning")
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Validar que el estado sea CREADO
    if fin_vale.estado != "CREADO":
        flash("No puede editar este vale porque ya está firmado (el estado no es CREADO)", "warning")
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Validar que el usuario sea quien creo este vale
    if not (current_user.can_admin(MODULO) or fin_vale.usuario_id == current_user.id):
        flash("No puede editar este vale porque usted no lo creo", "warning")
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Si viene el formulario
    form = FinValeEditForm()
    if form.validate_on_submit():
        es_valido = True

        # Inicializar variables
        usuario = None
        solicito = None
        autorizo = None

        # Validar usuario
        usuario_email = safe_email(form.usuario_email.data)
        if usuario_email != "":
            usuario = Usuario.find_by_identity(usuario_email)
            if usuario is None:
                flash("El usuario no existe", "warning")
                es_valido = False

        # Validar solicitante
        solicito_email = safe_email(form.solicito_email.data)
        if solicito_email != "":
            solicito = Usuario.find_by_identity(solicito_email)
            if solicito is None:
                flash("El solicitante no existe", "warning")
                es_valido = False

        # Validar autorizante
        autorizo_email = safe_email(form.autorizo_email.data)
        if autorizo_email != "":
            autorizo = Usuario.find_by_identity(autorizo_email)
            if autorizo is None:
                flash("El autorizante no existe", "warning")
                es_valido = False

        # Si es valido, actualizar
        if es_valido:
            fin_vale.usuario = usuario
            if solicito is None:
                fin_vale.solicito_nombre = ""
                fin_vale.solicito_puesto = ""
                fin_vale.solicito_email = ""
            else:
                fin_vale.solicito_nombre = solicito.nombre
                fin_vale.solicito_puesto = solicito.puesto
                fin_vale.solicito_email = solicito.email
            if autorizo is None:
                fin_vale.autorizo_nombre = ""
                fin_vale.autorizo_puesto = ""
                fin_vale.autorizo_email = ""
            else:
                fin_vale.autorizo_nombre = autorizo.nombre
                fin_vale.autorizo_puesto = autorizo.puesto
                fin_vale.autorizo_email = autorizo.email
            fin_vale.justificacion = safe_string(form.justificacion.data, max_len=1020, to_uppercase=False, save_enie=True)
            fin_vale.monto = float(form.monto.data)
            fin_vale.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Vale {fin_vale.justificacion}"),
                url=url_for("fin_vales.detail", fin_vale_id=fin_vale.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

    # Cambiar nulos por textos vacios
    if fin_vale.solicito_email is None:
        fin_vale.solicito_email = ""
    if fin_vale.autorizo_email is None:
        fin_vale.autorizo_email = ""

    # Mostrar el formulario
    form.usuario_email.data = fin_vale.usuario.email
    form.solicito_email.data = fin_vale.solicito_email
    form.autorizo_email.data = fin_vale.autorizo_email
    form.justificacion.data = fin_vale.justificacion
    form.monto.data = str(fin_vale.monto)
    return render_template("fin_vales/edit.jinja2", form=form, fin_vale=fin_vale)


@fin_vales.route("/fin_vale/crear", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def step_1_create():
    """Formulario paso 1 crear FinVale"""

    # Si viene el formulario
    form = FinValeStep1CreateForm()
    if form.validate_on_submit():
        # Si tiene el e-mail de quien va a solicitar, consultarlo
        solicito_email = None
        solicito_nombre = None
        solicito_puesto = None
        solicito = Usuario.query.filter_by(email=form.solicito_email.data).first()
        if solicito is not None:
            solicito_email = solicito.email
            solicito_nombre = solicito.nombre
            solicito_puesto = solicito.puesto

        # Si tiene el e-mail de quien va a autorizar, consultarlo
        autorizo_email = None
        autorizo_nombre = None
        autorizo_puesto = None
        autorizo = Usuario.query.filter_by(email=form.autorizo_email.data).first()
        if autorizo is not None:
            autorizo_email = autorizo.email
            autorizo_nombre = autorizo.nombre
            autorizo_puesto = autorizo.puesto

        # Guardar el vale
        fin_vale = FinVale(
            usuario_id=current_user.id,
            estado="CREADO",
            justificacion=safe_string(form.justificacion.data, max_len=1020, to_uppercase=False, save_enie=True),
            monto=float(form.monto.data),
            tipo="GASOLINA",
            solicito_email=solicito_email,
            solicito_nombre=solicito_nombre,
            solicito_puesto=solicito_puesto,
            autorizo_email=autorizo_email,
            autorizo_nombre=autorizo_nombre,
            autorizo_puesto=autorizo_puesto,
        )
        fin_vale.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Vale de Gasolina {fin_vale.id}"),
            url=url_for("fin_vales.detail", fin_vale_id=fin_vale.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")

        # Redireccionar a la pagina de detalle
        return redirect(bitacora.url)

    # Definir valores por defecto del formulario
    form.usuario_email.data = current_user.email
    form.solicito_email.data = ""
    form.autorizo_email.data = ""
    form.justificacion.data = f"Solicito un vale de gasolina de $200.00 (Doscientos pesos 00/100 M.N.), para {current_user.nombre} con el objetivo de ir a DESTINO."
    form.monto.data = "200.0"

    # Consultar el ultimo vale del usuario, si existe se toman los valores
    ultimo_vale = FinVale.query.filter(FinVale.usuario_id == current_user.id).order_by(FinVale.id.desc()).first()
    if ultimo_vale is not None:
        form.solicito_email.data = ultimo_vale.solicito_email
        form.autorizo_email.data = ultimo_vale.autorizo_email
        form.justificacion.data = ultimo_vale.justificacion
        form.monto.data = str(ultimo_vale.monto)

    # Entregar formulario
    return render_template("fin_vales/step_1_create.jinja2", form=form)


@fin_vales.route("/fin_vales/solicitar/<int:fin_vale_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def step_2_request(fin_vale_id):
    """Formulario paso 2 solicitar FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)
    puede_firmarlo = True

    # Validar que sea activo
    if fin_vale.estatus != "A":
        flash("El vale esta eliminado", "warning")
        puede_firmarlo = False

    # Validar el estado
    if fin_vale.estado != "CREADO":
        flash("El vale no tiene el estado CREADO", "warning")
        puede_firmarlo = False

    # Validar el usuario
    if current_user.efirma_registro_id is None:
        flash("Usted no tiene registro en la firma electronica", "warning")
        puede_firmarlo = False
    if ROL_SOLICITANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para solicitar un vale", "warning")
        puede_firmarlo = False

    # Si no puede solicitarlo, redireccionar a la pagina de detalle
    if not puede_firmarlo:
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Si viene el formulario
    form = FinValeStep2RequestForm()
    if form.validate_on_submit():
        # Lanzar la tarea en el fondo
        tarea = current_user.launch_task(
            comando="fin_vales.tasks.solicitar",
            mensaje="Elaborando solicitud en el motor de firmas electrónicas...",
            fin_vale_id=fin_vale.id,
            usuario_id=current_user.id,
            contrasena=form.contrasena.data,
        )
        flash(f"{tarea.mensaje} Esta página se va a recargar en 10 segundos...", "info")
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Entregar formulario
    return render_template("fin_vales/step_2_request.jinja2", form=form, fin_vale=fin_vale)


@fin_vales.route("/fin_vales/cancelar_solicitado/<int:fin_vale_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def cancel_2_request(fin_vale_id):
    """Formulario cancelar solicitado FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)
    puede_cancelarlo = True

    # Validar que sea activo
    if fin_vale.estatus != "A":
        flash("El vale esta eliminado", "warning")
        puede_cancelarlo = False

    # Validar el estado
    if fin_vale.estado != "SOLICITADO":
        flash("El vale no esta en estado SOLICITADO", "warning")
        puede_cancelarlo = False

    # Validar el usuario
    if current_user.efirma_registro_id is None:
        flash("Usted no tiene registro en la firma electronica", "warning")
        puede_cancelarlo = False
    if ROL_SOLICITANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para cancelar un vale solicitado", "warning")
        puede_cancelarlo = False
    if fin_vale.solicito_email != current_user.email:
        flash("Usted no es el solicitante de este vale", "warning")
        puede_cancelarlo = False

    # Si no puede cancelarlo, redireccionar a la pagina de detalle
    if not puede_cancelarlo:
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Si viene el formulario
    form = FinValeCancel2RequestForm()
    if form.validate_on_submit():
        # Lanzar la tarea en el fondo
        tarea = current_user.launch_task(
            comando="fin_vales.tasks.cancelar_solicitar",
            mensaje="Cancelando solicitud en el motor de firmas electrónicas...",
            fin_vale_id=fin_vale.id,
            usuario_id=current_user.id,
            contrasena=form.contrasena.data,
        )
        flash(f"{tarea.mensaje} Esta página se va a recargar en 10 segundos...", "info")
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Mostrar formulario
    return render_template("fin_vales/cancel_2_request.jinja2", form=form, fin_vale=fin_vale)


@fin_vales.route("/fin_vales/autorizar/<int:fin_vale_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def step_3_authorize(fin_vale_id):
    """Formulario paso 3 autorizar FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)
    puede_firmarlo = True

    # Validar que sea activo
    if fin_vale.estatus != "A":
        flash("El vale esta eliminado", "warning")
        puede_firmarlo = False

    # Validar el estado
    if fin_vale.estado != "SOLICITADO":
        flash("El vale no esta en estado SOLICITADO", "warning")
        puede_firmarlo = False

    # Validar el usuario
    if current_user.efirma_registro_id is None:
        flash("Usted no tiene registro en la firma electronica", "warning")
        puede_firmarlo = False
    if ROL_AUTORIZANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para autorizar un vale", "warning")
        puede_firmarlo = False

    # Si no puede autorizarlo, redireccionar a la pagina de detalle
    if not puede_firmarlo:
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Si viene el formulario
    form = FinValeStep3AuthorizeForm()
    if form.validate_on_submit():
        # Lanzar la tarea en el fondo
        tarea = current_user.launch_task(
            comando="fin_vales.tasks.autorizar",
            mensaje="Elaborando autorización en el motor de firmas electrónicas...",
            fin_vale_id=fin_vale.id,
            usuario_id=current_user.id,
            contrasena=form.contrasena.data,
        )
        flash(f"{tarea.mensaje} Esta página se va a recargar en 10 segundos...", "info")
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Mostrar formulario
    return render_template("fin_vales/step_3_authorize.jinja2", form=form, fin_vale=fin_vale)


@fin_vales.route("/fin_vales/cancelar_autorizado/<int:fin_vale_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def cancel_3_authorize(fin_vale_id):
    """Formulario cancelar autorizado FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)
    puede_cancelarlo = True

    # Validar que sea activo
    if fin_vale.estatus != "A":
        flash("El vale esta eliminado", "warning")
        puede_cancelarlo = False

    # Validar el estado
    if fin_vale.estado != "AUTORIZADO":
        flash("El vale no esta en estado AUTORIZADO", "warning")
        puede_cancelarlo = False

    # Validar el usuario
    if current_user.efirma_registro_id is None:
        flash("Usted no tiene registro en la firma electronica", "warning")
        puede_cancelarlo = False
    if ROL_AUTORIZANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para cancelar un vale autorizado", "warning")
        puede_cancelarlo = False
    if fin_vale.autorizo_email != current_user.email:
        flash("Usted no es el autorizante de este vale", "warning")
        puede_cancelarlo = False

    # Si no puede cancelarlo, redireccionar a la pagina de detalle
    if not puede_cancelarlo:
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Si viene el formulario
    form = FinValeCancel3AuthorizeForm()
    if form.validate_on_submit():
        # Lanzar la tarea en el fondo
        tarea = current_user.launch_task(
            comando="fin_vales.tasks.cancelar_autorizar",
            mensaje="Cancelando autorización en el motor de firmas electrónicas...",
            fin_vale_id=fin_vale.id,
            usuario_id=current_user.id,
            contrasena=form.contrasena.data,
        )
        flash(f"{tarea.mensaje} Esta página se va a recargar en 10 segundos...", "info")
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Mostrar formulario
    return render_template("fin_vales/cancel_3_authorize.jinja2", form=form, fin_vale=fin_vale)


@fin_vales.route("/fin_vales/entregar/<int:fin_vale_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def step_4_deliver(fin_vale_id):
    """Formulario paso 4 entregar FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)
    puede_entregarlo = True

    # Validar que sea activo
    if fin_vale.estatus != "A":
        flash("El vale esta eliminado", "warning")
        puede_entregarlo = False

    # Validar el estado
    if fin_vale.estado != "AUTORIZADO":
        flash("El vale no esta en estado AUTORIZADO", "warning")
        puede_entregarlo = False

    # Validar el usuario
    if ROL_AUTORIZANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para entregar un vale", "warning")
        puede_entregarlo = False

    # Si no puede entregarlo, redireccionar a la pagina de detalle
    if not puede_entregarlo:
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Si viene el formulario
    form = FinValeStep4DeliverForm()
    if form.validate_on_submit():
        fin_vale.folio = form.folio.data
        fin_vale.estado = "ENTREGADO"
        fin_vale.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Entregado el Vale de Gasolina {fin_vale.id}"),
            url=url_for("fin_vales.detail", fin_vale_id=fin_vale.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Mostrar formulario
    return render_template("fin_vales/step_4_deliver.jinja2", form=form, fin_vale=fin_vale)


@fin_vales.route("/fin_vales/adjuntar/<int:fin_vale_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def step_5_attachments(fin_vale_id):
    """Formulario paso 5 adjuntar FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)
    puede_adjuntar = True

    # Validar que sea activo
    if fin_vale.estatus != "A":
        flash("El vale esta eliminado", "warning")
        puede_adjuntar = False

    # Validar el estado
    if fin_vale.estado != "ENTREGADO" and fin_vale.estado != "POR REVISAR":
        flash("El vale no esta en estado ENTREGADO o POR REVISAR", "warning")
        puede_adjuntar = False

    # Validar el usuario
    if current_user.id != fin_vale.usuario_id:
        flash("Usted no es el usuario que creo el vale", "warning")
        puede_adjuntar = False

    # Si no puede entregarlo, redireccionar a la pagina de detalle
    if not puede_adjuntar:
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Si viene el formulario
    form = FinValeStep5AttachmentsForm()
    if form.validate_on_submit():
        fin_vale.vehiculo_descripcion = safe_string(form.vehiculo_descripcion.data)
        fin_vale.tanque_inicial = safe_string(form.tanque_inicial.data)
        fin_vale.tanque_final = safe_string(form.tanque_final.data)
        fin_vale.kilometraje_inicial = form.kilometraje_inicial.data
        fin_vale.kilometraje_final = form.kilometraje_final.data
        fin_vale.estado = "POR REVISAR"
        fin_vale.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Por revisar Vale {fin_vale.id}"),
            url=url_for("fin_vales.detail", fin_vale_id=fin_vale.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Mostrar formulario
    form.vehiculo_descripcion.data = fin_vale.vehiculo_descripcion
    form.tanque_inicial.data = fin_vale.tanque_inicial
    form.tanque_final.data = fin_vale.tanque_final
    form.kilometraje_inicial.data = fin_vale.kilometraje_inicial
    form.kilometraje_final.data = fin_vale.kilometraje_final
    return render_template("fin_vales/step_5_attachments.jinja2", form=form, fin_vale=fin_vale)


@fin_vales.route("/fin_vales/archivar/<int:fin_vale_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def step_6_archive(fin_vale_id):
    """Formulario paso 6 archivar FinVale"""

    # Consultar el vale
    fin_vale = FinVale.query.get_or_404(fin_vale_id)
    puede_archivarlo = True

    # Validar que sea activo
    if fin_vale.estatus != "A":
        flash("El vale esta eliminado", "warning")
        puede_archivarlo = False

    # Validar el estado
    if fin_vale.estado != "POR REVISAR":
        flash("El vale no esta en estado POR REVISAR", "warning")
        puede_archivarlo = False

    # Validar el usuario
    if ROL_AUTORIZANTES not in current_user.get_roles():
        flash("Usted no tiene el rol para archivar un vale", "warning")
        puede_archivarlo = False

    # Si no puede entregarlo, redireccionar a la pagina de detalle
    if not puede_archivarlo:
        return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale_id))

    # Si viene el formulario
    form = FinValeStep6ArchiveForm()
    if form.validate_on_submit():
        fin_vale.notas = safe_string(form.notas.data, to_uppercase=False, max_len=1020)
        fin_vale.estado = "ARCHIVADO"
        fin_vale.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Archivado Vale {fin_vale.id}"),
            url=url_for("fin_vales.detail", fin_vale_id=fin_vale.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Mostrar formulario
    fin_vale.notas = "Ninguna"
    return render_template("fin_vales/step_6_archive.jinja2", form=form, fin_vale=fin_vale)


@fin_vales.route("/fin_vales/eliminar/<int:fin_vale_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(fin_vale_id):
    """Eliminar FinVale"""
    fin_vale = FinVale.query.get_or_404(fin_vale_id)
    if fin_vale.estatus == "A":
        fin_vale.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado FinVale {fin_vale.id}"),
            url=url_for("fin_vales.detail", fin_vale_id=fin_vale.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale.id))


@fin_vales.route("/fin_vales/recuperar/<int:fin_vale_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(fin_vale_id):
    """Recuperar FinVale"""
    fin_vale = FinVale.query.get_or_404(fin_vale_id)
    if fin_vale.estatus == "B":
        fin_vale.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado FinVale {fin_vale.id}"),
            url=url_for("fin_vales.detail", fin_vale_id=fin_vale.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("fin_vales.detail", fin_vale_id=fin_vale.id))
