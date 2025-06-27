"""
Usuarios, vistas
"""

import json
import re
from datetime import datetime, timedelta

import google.auth.transport.requests
import google.oauth2.id_token
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from pytz import timezone
from sqlalchemy import or_

from config.firebase import get_firebase_settings
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.distritos.models import Distrito
from hercules.blueprints.entradas_salidas.models import EntradaSalida
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.oficinas.models import Oficina
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import anonymous_required, permission_required
from hercules.blueprints.usuarios.forms import AccesoForm, UsuarioForm
from hercules.blueprints.usuarios.models import Usuario
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.pwgen import generar_api_key, generar_contrasena
from lib.safe_next_url import safe_next_url
from lib.safe_string import CONTRASENA_REGEXP, EMAIL_REGEXP, TOKEN_REGEXP, safe_email, safe_message, safe_string

HTTP_REQUEST = google.auth.transport.requests.Request()

MODULO = "USUARIOS"

usuarios = Blueprint("usuarios", __name__, template_folder="templates")


@usuarios.route("/login", methods=["GET", "POST"])
@anonymous_required()
def login():
    """Acceso al Sistema"""
    firebase_settings = get_firebase_settings()
    form = AccesoForm(siguiente=request.args.get("siguiente"))
    if form.validate_on_submit():
        # Tomar valores del formulario
        identidad = request.form.get("identidad")
        contrasena = request.form.get("contrasena")
        token = request.form.get("token")
        siguiente_url = request.form.get("siguiente")
        # Si esta definida la variable de entorno FIREBASE_APIKEY
        if firebase_settings.APIKEY != "":
            # Entonces debe ingresar con Google/Microsoft/GitHub
            if re.fullmatch(TOKEN_REGEXP, token) is not None:
                # Acceso por Firebase Auth
                claims = google.oauth2.id_token.verify_firebase_token(token, HTTP_REQUEST)
                if claims:
                    email = claims.get("email", "Unknown")
                    usuario = Usuario.find_by_identity(email)
                    if usuario and usuario.authenticated(with_password=False):
                        if login_user(usuario, remember=True) and usuario.is_active:
                            EntradaSalida(
                                usuario_id=usuario.id,
                                tipo="INGRESO",
                                direccion_ip=request.remote_addr,
                            ).save()
                            if siguiente_url:
                                return redirect(safe_next_url(siguiente_url))
                            return redirect(url_for("sistemas.start"))
                        else:
                            flash("No está activa esa cuenta.", "warning")
                    else:
                        flash("No existe esa cuenta.", "warning")
                else:
                    flash("Falló la autentificación.", "warning")
            else:
                flash("Token incorrecto.", "warning")
        else:
            # De lo contrario, el ingreso es con username/password
            if re.fullmatch(EMAIL_REGEXP, identidad) is None:
                flash("Correo electrónico no válido.", "warning")
            elif re.fullmatch(CONTRASENA_REGEXP, contrasena) is None:
                flash("Contraseña no válida.", "warning")
            else:
                usuario = Usuario.find_by_identity(identidad)
                if usuario and usuario.authenticated(password=contrasena):
                    if login_user(usuario, remember=True) and usuario.is_active:
                        EntradaSalida(
                            usuario_id=usuario.id,
                            tipo="INGRESO",
                            direccion_ip=request.remote_addr,
                        ).save()
                        if siguiente_url:
                            return redirect(safe_next_url(siguiente_url))
                        return redirect(url_for("sistemas.start"))
                    else:
                        flash("No está activa esa cuenta", "warning")
                else:
                    flash("Usuario o contraseña incorrectos.", "warning")
    return render_template(
        "usuarios/login.jinja2",
        form=form,
        firebase_settings=firebase_settings,
        title="Plataforma Web",
    )


@usuarios.route("/logout")
@login_required
def logout():
    """Salir del Sistema"""
    EntradaSalida(
        usuario_id=current_user.id,
        tipo="SALIO",
        direccion_ip=request.remote_addr,
    ).save()
    logout_user()
    flash("Ha salido de este sistema.", "success")
    return redirect(url_for("usuarios.login"))


@usuarios.route("/perfil")
@login_required
def profile():
    """Mostrar el Perfil"""
    ahora_utc = datetime.now(timezone("UTC"))
    ahora_mx_coah = ahora_utc.astimezone(timezone("America/Mexico_City"))
    formato_fecha = "%Y-%m-%d %H:%M %p"
    return render_template(
        "usuarios/profile.jinja2",
        ahora_utc_str=ahora_utc.strftime(formato_fecha),
        ahora_mx_coah_str=ahora_mx_coah.strftime(formato_fecha),
    )


@usuarios.route("/usuarios/datatable_json", methods=["GET", "POST"])
@login_required
@permission_required(MODULO, Permiso.VER)
def datatable_json():
    """DataTable JSON para listado de Usuarios"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Usuario.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Usuario.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Usuario.estatus == "A")
    # Filtrar por autoridad_id u autoridad_id_diferente_a
    if "autoridad_id" in request.form:
        consulta = consulta.filter(Usuario.autoridad_id == request.form["autoridad_id"])
    elif "autoridad_id_diferente_a" in request.form:
        consulta = consulta.filter(Usuario.autoridad_id != request.form["autoridad_id_diferente_a"])
    # Filtrar por oficina_id u oficina_id_diferente_a
    if "oficina_id" in request.form:
        consulta = consulta.filter(Usuario.oficina_id == request.form["oficina_id"])
    elif "oficina_id_diferente_a" in request.form:
        consulta = consulta.filter(Usuario.oficina_id != request.form["oficina_id_diferente_a"])
    # Filtrar por las columnas de texto de Usuario
    if "nombres" in request.form:
        consulta = consulta.filter(Usuario.nombres.contains(safe_string(request.form["nombres"])))
    if "apellido_paterno" in request.form:
        consulta = consulta.filter(Usuario.apellido_paterno.contains(safe_string(request.form["apellido_paterno"])))
    if "apellido_materno" in request.form:
        consulta = consulta.filter(Usuario.apellido_materno.contains(safe_string(request.form["apellido_materno"])))
    if "curp" in request.form:
        consulta = consulta.filter(Usuario.curp.contains(safe_string(request.form["curp"])))
    if "puesto" in request.form:
        consulta = consulta.filter(Usuario.puesto.contains(safe_string(request.form["puesto"])))
    if "email" in request.form:
        consulta = consulta.filter(Usuario.email.contains(safe_email(request.form["email"], search_fragment=True)))
    # Ordenar y paginar
    registros = consulta.order_by(Usuario.email).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "email": resultado.email,
                    "url": url_for("usuarios.detail", usuario_id=resultado.id),
                },
                "nombre": resultado.nombre,
                "curp": resultado.curp,
                "puesto": resultado.puesto,
                "autoridad": {
                    "clave": resultado.autoridad.clave,
                    "url": (
                        url_for("autoridades.detail", autoridad_id=resultado.autoridad_id)
                        if current_user.can_view("AUTORIDADES")
                        else ""
                    ),
                },
                "oficina": {
                    "clave": resultado.oficina.clave,
                    "url": (
                        url_for("oficinas.detail", oficina_id=resultado.oficina_id) if current_user.can_view("OFICINAS") else ""
                    ),
                },
                "inv_custodia": {
                    "email": resultado.email,
                    "url": url_for("inv_custodias.new_with_usuario_id", usuario_id=resultado.id),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@usuarios.route("/usuarios/api_key_request/<int:usuario_id>", methods=["GET", "POST"])
@login_required
@permission_required(MODULO, Permiso.ADMINISTRAR)
def request_api_key_json(usuario_id):
    """Solicitar API Key"""

    # Consultar usuario
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.estatus != "A":
        return {
            "success": False,
            "message": "El usuario no está activo",
            "api_key": "",
            "api_key_expiracion": "",
        }

    # Si se recibe action con clean, se va a limpiar
    if "action" in request.form and request.form["action"] == "clean":
        usuario.api_key = ""
        usuario.api_key_expiracion = datetime(year=2000, month=1, day=1)
        usuario.save()
        mensaje = f"La API Key de {usuario.email} fue eliminada"
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=mensaje,
            url=url_for("usuarios.detail", usuario_id=usuario.id),
        )
        bitacora.save()
        return {
            "success": True,
            "message": mensaje,
            "api_key": usuario.api_key,
            "api_key_expiracion": usuario.api_key_expiracion,
        }

    # Si se recibe action con new, se va a crear una nueva
    if "action" in request.form and request.form["action"] == "new":
        if "days" in request.form:
            days = int(request.form["days"])
        else:
            days = 90
        usuario.api_key = generar_api_key(usuario.id, usuario.email)
        usuario.api_key_expiracion = datetime.now() + timedelta(days=days)
        usuario.save()
        mensaje = f"Nueva API Key para {usuario.email} con expiración en {days} días"
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=mensaje,
            url=url_for("usuarios.detail", usuario_id=usuario.id),
        )
        bitacora.save()
        return {
            "success": True,
            "message": mensaje,
            "api_key": usuario.api_key,
            "api_key_expiracion": usuario.api_key_expiracion,
        }

    # Si no se recibe nada, entregar la actual
    return {
        "success": True,
        "message": "Se ha entregado la API Key a la interfaz",
        "api_key": usuario.api_key,
        "api_key_expiracion": usuario.api_key_expiracion,
    }


@usuarios.route("/usuarios")
@login_required
@permission_required(MODULO, Permiso.VER)
def list_active():
    """Listado de Usuarios activos"""
    return render_template(
        "usuarios/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Usuarios",
        estatus="A",
    )


@usuarios.route("/usuarios/inactivos")
@login_required
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Usuarios inactivos"""
    return render_template(
        "usuarios/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Usuarios inactivos",
        estatus="B",
    )


@usuarios.route("/usuarios/<int:usuario_id>")
@login_required
@permission_required(MODULO, Permiso.VER)
def detail(usuario_id):
    """Detalle de un Usuario"""
    usuario = Usuario.query.get_or_404(usuario_id)
    return render_template("usuarios/detail.jinja2", usuario=usuario)


@usuarios.route("/usuarios/api_key/<int:usuario_id>")
@login_required
@permission_required(MODULO, Permiso.ADMINISTRAR)
def view_api_key(usuario_id):
    """Ver API Key"""

    # Consultar usuario
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.estatus != "A":
        flash("El usuario no está activo.", "warning")
        return redirect(url_for("usuarios.detail", usuario_id=usuario.id))

    # Juntar los permisos por nivel
    permisos_por_nivel = {1: [], 2: [], 3: [], 4: []}
    for etiqueta, nivel in usuario.permisos.items():
        permisos_por_nivel[nivel].append(etiqueta)

    # Mostrar api_key.jinja2
    return render_template(
        "usuarios/api_key.jinja2",
        usuario=usuario,
        permisos_en_nivel_1=sorted(permisos_por_nivel[1]),
        permisos_en_nivel_2=sorted(permisos_por_nivel[2]),
        permisos_en_nivel_3=sorted(permisos_por_nivel[3]),
        permisos_en_nivel_4=sorted(permisos_por_nivel[4]),
    )


@usuarios.route("/usuarios/nuevo", methods=["GET", "POST"])
@login_required
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Usuario"""
    form = UsuarioForm()
    if form.validate_on_submit():
        # Validaciones
        es_valido = True
        # Validar que el email no se repita
        email = safe_email(form.email.data)
        if Usuario.query.filter_by(email=email).first():
            flash("El e-mail ya está en uso. Debe de ser único.", "warning")
            es_valido = False
        # Guardar
        if es_valido:
            usuario = Usuario(
                autoridad_id=form.autoridad.data,
                oficina_id=form.oficina.data,
                email=email,
                nombres=safe_string(form.nombres.data, save_enie=True),
                apellido_paterno=safe_string(form.apellido_paterno.data, save_enie=True),
                apellido_materno=safe_string(form.apellido_materno.data, save_enie=True),
                curp=safe_string(form.curp.data),
                puesto=safe_string(form.puesto.data),
                workspace=form.workspace.data,
                efirma_registro_id=form.efirma_registro_id.data,
                api_key="",
                api_key_expiracion=datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0),
                contrasena=generar_contrasena(),
            )
            usuario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Usuario {usuario.email}"),
                url=url_for("usuarios.detail", usuario_id=usuario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Consultar el distrito por defecto con clave ND
    distrito_por_defecto_id = 1
    distrito_por_defecto = Distrito.query.filter_by(clave="ND").first()
    if distrito_por_defecto is not None:
        distrito_por_defecto_id = distrito_por_defecto.id
    # Consultar la oficina por defecto con clave ND
    oficina_por_defecto = Oficina.query.filter_by(clave="ND").first()
    if oficina_por_defecto is None:
        oficina_por_defecto = None
    # Valores por defecto
    form.workspace.data = "COAHUILA"
    # Entregar
    return render_template(
        "usuarios/new.jinja2",
        form=form,
        distrito_por_defecto_id=distrito_por_defecto_id,
        oficina_por_defecto=oficina_por_defecto,
    )


@usuarios.route("/usuarios/edicion/<int:usuario_id>", methods=["GET", "POST"])
@login_required
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(usuario_id):
    """Editar Usuario"""
    usuario = Usuario.query.get_or_404(usuario_id)
    form = UsuarioForm()
    if form.validate_on_submit():
        es_valido = True
        # Si cambia el e-mail verificar que no este en uso
        email = safe_email(form.email.data)
        if usuario.email != email:
            usuario_existente = Usuario.query.filter_by(email=email).first()
            if usuario_existente and usuario_existente.id != usuario.id:
                es_valido = False
                flash("La e-mail ya está en uso. Debe de ser único.", "warning")
        # Si es valido actualizar
        if es_valido:
            usuario.autoridad_id = form.autoridad.data  # Combo select distrito-autoridad
            usuario.oficina_id = form.oficina.data  # Select2
            usuario.email = email
            usuario.nombres = safe_string(form.nombres.data, save_enie=True)
            usuario.apellido_paterno = safe_string(form.apellido_paterno.data, save_enie=True)
            usuario.apellido_materno = safe_string(form.apellido_materno.data, save_enie=True)
            usuario.curp = safe_string(form.curp.data)
            usuario.puesto = safe_string(form.puesto.data)
            usuario.workspace = form.workspace.data
            usuario.efirma_registro_id = form.efirma_registro_id.data
            usuario.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Usuario {usuario.email}"),
                url=url_for("usuarios.detail", usuario_id=usuario.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # No es necesario pasar autoridad_id porque se va a tomar de usuario con JS
    # Tampoco es necesario pasar oficina_id porque se va a tomar de usuario con JS
    form.email.data = usuario.email
    form.nombres.data = usuario.nombres
    form.apellido_paterno.data = usuario.apellido_paterno
    form.apellido_materno.data = usuario.apellido_materno
    form.curp.data = usuario.curp
    form.puesto.data = usuario.puesto
    form.workspace.data = usuario.workspace
    form.efirma_registro_id.data = usuario.efirma_registro_id
    return render_template("usuarios/edit.jinja2", form=form, usuario=usuario)


@usuarios.route("/usuarios/eliminar/<int:usuario_id>")
@login_required
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(usuario_id):
    """Eliminar Usuario"""
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.estatus == "A":
        # Dar de baja al usuario
        usuario.delete()
        # Dar de baja los roles del usuario
        for usuario_rol in usuario.usuarios_roles:
            usuario_rol.delete()
        # Guardar en la bitacora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Usuario {usuario.email}"),
            url=url_for("usuarios.detail", usuario_id=usuario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("usuarios.detail", usuario_id=usuario.id))


@usuarios.route("/usuarios/recuperar/<int:usuario_id>")
@login_required
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(usuario_id):
    """Recuperar Usuario"""
    usuario = Usuario.query.get_or_404(usuario_id)
    if usuario.estatus == "B":
        # Recuperar al usuario
        usuario.recover()
        # Recuperar los roles del usuario
        for usuario_rol in usuario.usuarios_roles:
            usuario_rol.recover()
        # Guardar en la bitacora
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Usuario {usuario.email}"),
            url=url_for("usuarios.detail", usuario_id=usuario.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("usuarios.detail", usuario_id=usuario.id))


@usuarios.route("/usuarios/select_json", methods=["GET", "POST"])
def select_json():
    """Select JSON para Usuarios"""
    # Consultar
    consulta = Usuario.query.filter_by(estatus="A")
    if "searchString" in request.form:
        usuarios_email = safe_email(request.form["searchString"], search_fragment=True)
        if usuarios_email != "":
            consulta = consulta.filter(Usuario.email.contains(usuarios_email))
    resultados = []
    for usuario in consulta.order_by(Usuario.email).limit(20).all():
        resultados.append({"id": usuario.email, "text": usuario.email, "nombre": usuario.nombre})
    return {"results": resultados, "pagination": {"more": False}}


@usuarios.route("/usuarios/select2_json", methods=["POST"])
def select2_json():
    """Proporcionar el JSON de usuarios para elegir con un Select2, se usa para filtrar en DataTables"""
    consulta = Usuario.query.filter(Usuario.estatus == "A")
    if "searchString" in request.form:
        texto = safe_string(request.form["searchString"], save_enie=True)
        if texto != "":
            palabras = texto.split()
            for palabra in palabras:
                consulta = consulta.filter(
                    or_(
                        Usuario.email.contains(palabra.lower()),
                        Usuario.nombres.contains(palabra),
                        Usuario.apellido_paterno.contains(palabra),
                        Usuario.apellido_materno.contains(palabra),
                        Usuario.puesto.contains(palabra),
                    )
                )
    if "workspace" in request.form:
        workspaces_in = safe_string(request.form["workspace"])
        if workspaces_in == "LOCAL":
            consulta = consulta.filter(
                or_(
                    Usuario.workspace == "COAHUILA",
                    Usuario.workspace == "BUSINESS STARTED",
                    Usuario.workspace == "BUSINESS STANDARD",
                )
            )
    resultados = []
    for usuario in consulta.order_by(Usuario.email).limit(10).all():
        resultados.append({"id": usuario.id, "text": f"{usuario.email}: {usuario.nombre} - {usuario.puesto}"})
    return {"results": resultados, "pagination": {"more": False}}
