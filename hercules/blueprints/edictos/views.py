"""
Edictos, vistas
"""

import json
import re
from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pytz import timezone
from sqlalchemy import Date, func
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.exceptions import NotFound

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.edictos.forms import EdictoEditForm, EdictoNewForm
from hercules.blueprints.edictos.models import Edicto
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.extensions import database
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import (
    MyBucketNotFoundError,
    MyFilenameError,
    MyFileNotFoundError,
    MyMissingConfigurationError,
    MyNotAllowedExtensionError,
    MyNotValidParamError,
    MyUnknownExtensionError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs, get_media_type_from_filename
from lib.safe_string import safe_clave, safe_expediente, safe_message, safe_numero_publicacion, safe_string
from lib.storage import GoogleCloudStorage
from lib.time_to_text import dia_mes_ano

# Zona horaria
TIMEZONE = "America/Mexico_City"
local_tz = timezone(TIMEZONE)

# Constantes de este módulo
MODULO = "EDICTOS"
DASHBOARD_CANTIDAD_DIAS = 15
LIMITE_DIAS = 365  # Un anio
LIMITE_DIAS_EDITAR = LIMITE_DIAS_ELIMINAR = LIMITE_DIAS_RECUPERAR = 7
LIMITE_ADMINISTRADORES_DIAS = 3650  # Administradores pueden manipular diez anios
MATERIAS_HABILITAR_DECLARACION_AUSENCIA = ["CIVIL", "FAMILIAR", "FAMILIAR ORAL"]

edictos = Blueprint("edictos", __name__, template_folder="templates")


@edictos.route("/edictos/acuses/<id_hashed>")
def checkout(id_hashed):
    """Acuse"""
    edicto = Edicto.query.get_or_404(Edicto.decode_id(id_hashed))
    dia, mes, anio = dia_mes_ano(edicto.creado)
    return render_template("edictos/checkout.jinja2", edicto=edicto, dia=dia, mes=mes.upper(), anio=anio)


@edictos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@edictos.route("/edictos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON con Edictos"""

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = Edicto.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Edicto.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Edicto.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Edicto.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Edicto.descripcion.contains(descripcion))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(Edicto.expediente == expediente)
        except (IndexError, ValueError):
            pass
    if "numero_publicacion" in request.form:
        try:
            numero_publicacion = safe_numero_publicacion(request.form["numero_publicacion"])
            consulta = consulta.filter(Edicto.numero_publicacion == numero_publicacion)
        except (IndexError, ValueError):
            pass

    # Filtrar por fechas, si vienen invertidas se corrigen
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(Edicto.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(Edicto.fecha <= fecha_hasta)

    # Ordenar y paginar
    registros = consulta.order_by(Edicto.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for edicto in registros:
        data.append(
            {
                "fecha": edicto.fecha.strftime("%Y-%m-%d 00:00:00"),
                "autoridad_clave": edicto.autoridad.clave,
                "detalle": {
                    "descripcion": edicto.descripcion,
                    "url": url_for("edictos.detail", edicto_id=edicto.id),
                },
                "expediente": edicto.expediente,
                "numero_publicacion": edicto.numero_publicacion,
                "es_declaracion_de_ausencia": "Sí" if edicto.es_declaracion_de_ausencia else "",
                "creado": edicto.creado.strftime("%Y-%m-%dT%H:%M:%S"),
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@edictos.route("/edictos/admin_datatable_json", methods=["GET", "POST"])
def admin_datatable_json():
    """DataTable JSON con Edicto para administrador"""

    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()

    # Consultar
    consulta = Edicto.query

    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(Edicto.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(Edicto.estatus == "A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Edicto.autoridad_id == autoridad.id)
    elif "autoridad_clave" in request.form:
        autoridad_clave = safe_clave(request.form["autoridad_clave"])
        if autoridad_clave != "":
            consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
    if "descripcion" in request.form:
        descripcion = safe_string(request.form["descripcion"], save_enie=True)
        if descripcion != "":
            consulta = consulta.filter(Edicto.descripcion.contains(descripcion))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter(Edicto.expediente == expediente)
        except (IndexError, ValueError):
            pass
    if "numero_publicacion" in request.form:
        try:
            numero_publicacion = safe_numero_publicacion(request.form["numero_publicacion"])
            consulta = consulta.filter(Edicto.numero_publicacion == numero_publicacion)
        except (IndexError, ValueError):
            pass

    # Filtrar por fechas, si vienen invertidas se corrigen
    fecha_desde = None
    fecha_hasta = None
    if "fecha_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_desde"]):
        fecha_desde = request.form["fecha_desde"]
    if "fecha_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}", request.form["fecha_hasta"]):
        fecha_hasta = request.form["fecha_hasta"]
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
    if fecha_desde:
        consulta = consulta.filter(Edicto.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(Edicto.fecha <= fecha_hasta)

    # Ordenar y paginar
    registros = consulta.order_by(Edicto.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()

    # Elaborar datos para DataTable
    data = []
    for edicto in registros:
        data.append(
            {
                "detalle": {
                    "id": edicto.id,
                    "url": url_for("edictos.detail", edicto_id=edicto.id),
                },
                "creado": edicto.creado.strftime("%Y-%m-%dT%H:%M:%S"),
                "autoridad": edicto.autoridad.clave,
                "fecha": edicto.fecha.strftime("%Y-%m-%d 00:00:00"),
                "descripcion": edicto.descripcion,
                "expediente": edicto.expediente,
                "es_declaracion_de_ausencia": "Sí" if edicto.es_declaracion_de_ausencia else "",
                "numero_publicacion": edicto.numero_publicacion,
            }
        )

    # Entregar JSON
    return output_datatable_json(draw, total, data)


@edictos.route("/edictos")
def list_active():
    """Listado de Edictos activos"""

    # Definir valores por defecto
    filtros = None
    titulo = None
    mostrar_filtro_autoridad_clave = True

    # Si es administrador
    plantilla = "edictos/list.jinja2"
    if current_user.can_admin(MODULO):
        plantilla = "edictos/list_admin.jinja2"

    # Si viene autoridad_id o autoridad_clave en la URL, agregar a los filtros
    autoridad = None
    try:
        if "autoridad_id" in request.args:
            autoridad_id = int(request.args.get("autoridad_id"))
            autoridad = Autoridad.query.get(autoridad_id)
        elif "autoridad_clave" in request.args:
            autoridad_clave = safe_clave(request.args.get("autoridad_clave"))
            autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
        if autoridad is not None:
            filtros = {"estatus": "A", "autoridad_id": autoridad.id}
            titulo = f"Edictos de {autoridad.descripcion_corta}"
            mostrar_filtro_autoridad_clave = False
    except (TypeError, ValueError):
        pass

    # Si es administrador
    if titulo is None and current_user.can_admin(MODULO):
        titulo = "Todos los Edictos"
        filtros = {"estatus": "A"}

    # Si puede editar o crear, solo ve lo de su autoridad
    if titulo is None and (current_user.can_insert(MODULO) or current_user.can_edit(MODULO)):
        filtros = {"estatus": "A", "autoridad_id": current_user.autoridad.id}
        titulo = f"Edictos de {current_user.autoridad.descripcion_corta}"
        mostrar_filtro_autoridad_clave = False

    # De lo contrario, es observador
    if titulo is None:
        filtros = {"estatus": "A"}
        titulo = "Edictos"

    # Entregar
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps(filtros),
        titulo=titulo,
        mostrar_filtro_autoridad_clave=mostrar_filtro_autoridad_clave,
        estatus="A",
    )


@edictos.route("/edictos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Edictos inactivos"""
    # Solo los administradores ven todas los edictos inactivas
    return render_template(
        "edictos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Todos los Edictos inactivos",
        estatus="B",
    )


@edictos.route("/edictos/<int:edicto_id>")
def detail(edicto_id):
    """Detalle de un Edicto"""
    edicto = Edicto.query.get_or_404(edicto_id)
    return render_template("edictos/detail.jinja2", edicto=edicto)


@edictos.route("/edictos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Subir Edicto como juzgado"""

    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad is None or autoridad.estatus != "A":
        flash("El juzgado/autoridad no existe o no es activa.", "warning")
        return redirect(url_for("edictos.list_active"))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("edictos.list_active"))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("edictos.list_active"))
    if autoridad.directorio_edictos is None or autoridad.directorio_edictos == "":
        flash("El juzgado/autoridad no tiene directorio para edictos.", "warning")
        return redirect(url_for("edictos.list_active"))

    # Definir la fecha límite para el juzgado
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_DIAS)

    # Si viene el formulario
    form = EdictoNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Validar descripcion
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        if descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Validar número de publicación
        try:
            numero_publicacion = safe_numero_publicacion(form.numero_publicacion.data)
        except (IndexError, ValueError):
            flash("El número de publicación es incorrecto.", "warning")
            es_valido = False

        # Tomar es_declaracion_de_ausencia
        es_declaracion_de_ausencia = form.es_declaracion_de_ausencia.data

        # Inicializar la liberia GCS con el directorio base, la fecha, las extensiones y los meses como palabras
        gcstorage = GoogleCloudStorage(
            base_directory=autoridad.directorio_edictos,
            upload_date=fecha,
            allowed_extensions=["pdf"],
            month_in_word=True,
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_EDICTOS"],
        )

        # Validar archivo
        archivo = request.files["archivo"]
        try:
            gcstorage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False

        # No es válido, entonces se vuelve a mostrar el formulario
        if es_valido is False:
            return render_template("edictos/new.jinja2", form=form)

        # Insertar registro
        edicto = Edicto(
            autoridad=autoridad,
            fecha=fecha,
            descripcion=descripcion,
            expediente=expediente,
            numero_publicacion=numero_publicacion,
            es_declaracion_de_ausencia=es_declaracion_de_ausencia,
        )
        edicto.save()

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            gcstorage.set_filename(hashed_id=edicto.encode_id(), description=descripcion)
            gcstorage.upload(archivo.stream.read())
        except (MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError):
            flash("Error fatal al subir el archivo a GCS.", "warning")
            es_exitoso = False
        except MyMissingConfigurationError:
            flash("Error al subir el archivo porque falla la configuración de GCS.", "danger")
            es_exitoso = False
        except Exception:
            flash("Error desconocido al subir el archivo.", "danger")
            es_exitoso = False

        # Si se sube con éxito, actualizar el registro con la URL del archivo y mostrar el detalle
        if es_exitoso:
            edicto.archivo = gcstorage.filename  # Conservar el nombre original
            edicto.url = gcstorage.url
            edicto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Edicto de {autoridad.clave} sobre {edicto.descripcion}"),
                url=url_for("edictos.detail", edicto_id=edicto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

        # Como no se subio con exito, se cambia el estatus a "B"
        edicto.estatus = "B"
        edicto.save()

    # Valores por defecto
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy

    # Si la materia es CIVIL, FAMILIAR o FAMILIAR ORAL, entonces se habilita el boleano es_declaracion_de_ausencia
    habilitar_es_declaracion_de_ausencia = False
    if autoridad.materia.nombre in MATERIAS_HABILITAR_DECLARACION_AUSENCIA:
        habilitar_es_declaracion_de_ausencia = True

    # Entregar el formulario
    return render_template(
        "edictos/new.jinja2",
        form=form,
        habilitar_es_declaracion_de_ausencia=habilitar_es_declaracion_de_ausencia,
    )


@edictos.route("/edictos/nuevo/<int:autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def new_with_autoridad_id(autoridad_id):
    """Subir Edicto para una autoridad como administrador"""

    # Validar autoridad
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if autoridad is None:
        flash("El juzgado/autoridad no existe.", "warning")
        return redirect(url_for("edictos.list_active"))
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if autoridad.directorio_edictos is None or autoridad.directorio_edictos == "":
        flash("El juzgado/autoridad no tiene directorio para edictos.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))

    # Para validar las fechas
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_ADMINISTRADORES_DIAS)

    # Si viene el formulario
    form = EdictoNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_ADMINISTRADORES_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Validar descripción
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        if descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Validar número de publicación
        try:
            numero_publicacion = safe_numero_publicacion(form.numero_publicacion.data)
        except (IndexError, ValueError):
            flash("El número de publicación es incorrecto.", "warning")
            es_valido = False

        # Tomar es_declaracion_de_ausencia
        es_declaracion_de_ausencia = form.es_declaracion_de_ausencia.data

        # Inicializar la liberia GCS con el directorio base, la fecha, las extensiones y los meses como palabras
        gcstorage = GoogleCloudStorage(
            base_directory=autoridad.directorio_glosas,
            upload_date=fecha,
            allowed_extensions=["pdf"],
            month_in_word=True,
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_EDICTOS"],
        )

        # Validar archivo
        archivo = request.files["archivo"]
        try:
            gcstorage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False

        # No es válido, entonces se vuelve a mostrar el formulario
        if es_valido is False:
            return render_template("edictos/new_for_autoridad.jinja2", form=form, autoridad=autoridad)

        # Insertar registro
        edicto = Edicto(
            autoridad=autoridad,
            fecha=fecha,
            descripcion=descripcion,
            expediente=expediente,
            numero_publicacion=numero_publicacion,
            es_declaracion_de_ausencia=es_declaracion_de_ausencia,
        )
        edicto.save()

        # Subir a Google Cloud Storage
        es_exitoso = True
        try:
            gcstorage.set_filename(hashed_id=edicto.encode_id(), description=descripcion)
            gcstorage.upload(archivo.stream.read())
        except (MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError):
            flash("Error fatal al subir el archivo a GCS.", "warning")
            es_exitoso = False
        except MyMissingConfigurationError:
            flash("Error al subir el archivo porque falla la configuración de GCS.", "danger")
            es_exitoso = False
        except Exception:
            flash("Error desconocido al subir el archivo.", "danger")
            es_exitoso = False

        # Si se sube con éxito, actualizar el registro con la URL del archivo y mostrar el detalle
        if es_exitoso:
            edicto.archivo = gcstorage.filename  # Conservar el nombre original
            edicto.url = gcstorage.url
            edicto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Edicto de {autoridad.clave} sobre {edicto.descripcion}"),
                url=url_for("edictos.detail", edicto_id=edicto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

        # Como no se subio con exito, se cambia el estatus a "B"
        edicto.estatus = "B"
        edicto.save()

    # Valores por defecto
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy

    # Si la materia es CIVIL, FAMILIAR o FAMILIAR ORAL, entonces se habilita el boleano es_declaracion_de_ausencia
    habilitar_es_declaracion_de_ausencia = False
    if autoridad.materia.nombre in MATERIAS_HABILITAR_DECLARACION_AUSENCIA:
        habilitar_es_declaracion_de_ausencia = True

    # Entregar el formulario
    return render_template(
        "edictos/new_for_autoridad.jinja2",
        form=form,
        autoridad=autoridad,
        habilitar_es_declaracion_de_ausencia=habilitar_es_declaracion_de_ausencia,
    )


@edictos.route("/edictos/editar/<int:edicto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(edicto_id):
    """Editar Edicto"""

    # Consultar
    edicto = Edicto.query.get_or_404(edicto_id)

    # Si NO es administrador
    if not (current_user.can_admin(MODULO)):
        # Validar que le pertenezca
        if current_user.autoridad_id != edicto.autoridad_id:
            flash("No puede editar registros ajenos.", "warning")
            return redirect(url_for("edictos.list_active"))
        # Si fue creado hace más de LIMITES_DIAS_EDITAR
        if edicto.creado < datetime.now(tz=local_tz) - timedelta(days=LIMITE_DIAS_EDITAR):
            flash(f"Ya no puede editar porque fue creado hace más de {LIMITE_DIAS_EDITAR} dias.", "warning")
            return redirect(url_for("edictos.detail", edicto_id=edicto.id))

    # Definir la fecha límite
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + timedelta(days=-LIMITE_DIAS)

    # Si viene el formulario
    form = EdictoEditForm()
    if form.validate_on_submit():
        es_valido = True

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            form.fecha.data = hoy
            es_valido = False

        # Validar descripción
        descripcion = safe_string(form.descripcion.data, save_enie=True)
        if edicto.descripcion == "":
            flash("La descripción es incorrecta.", "warning")
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Validar número de publicación
        try:
            numero_publicacion = safe_numero_publicacion(form.numero_publicacion.data)
        except (IndexError, ValueError):
            flash("El número de publicación es incorrecto.", "warning")
            es_valido = False

        # Tomar es_declaracion_de_ausencia
        es_declaracion_de_ausencia = form.es_declaracion_de_ausencia.data

        # Si es válido, entonces se guarda
        if es_valido:
            edicto.fecha = fecha
            edicto.descripcion = descripcion
            edicto.expediente = expediente
            edicto.numero_publicacion = numero_publicacion
            edicto.es_declaracion_de_ausencia = es_declaracion_de_ausencia
            edicto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado el Edicto de {edicto.autoridad.clave} sobre {edicto.descripcion}"),
                url=url_for("edictos.detail", edicto_id=edicto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

    # Definir valores en el formulario
    form.fecha.data = edicto.fecha
    form.descripcion.data = edicto.descripcion
    form.expediente.data = edicto.expediente
    form.numero_publicacion.data = edicto.numero_publicacion
    form.es_declaracion_de_ausencia.data = edicto.es_declaracion_de_ausencia

    # Si la materia es CIVIL, FAMILIAR o FAMILIAR ORAL, entonces se habilita el boleano es_declaracion_de_ausencia
    habilitar_es_declaracion_de_ausencia = False
    if edicto.autoridad.materia.nombre in MATERIAS_HABILITAR_DECLARACION_AUSENCIA:
        habilitar_es_declaracion_de_ausencia = True

    # Entregar el formulario
    return render_template(
        "edictos/edit.jinja2",
        form=form,
        edicto=edicto,
        habilitar_es_declaracion_de_ausencia=habilitar_es_declaracion_de_ausencia,
    )


@edictos.route("/edictos/eliminar/<int:edicto_id>")
@permission_required(MODULO, Permiso.CREAR)
def delete(edicto_id):
    """Eliminar Edicto"""

    # Consultar
    edicto = Edicto.query.get_or_404(edicto_id)
    detalle_url = url_for("edictos.detail", edicto_id=edicto.id)

    # Validar que se pueda eliminar
    if edicto.estatus == "B":
        flash("No puede eliminar este Edicto porque ya está eliminado.", "success")
        return redirect(detalle_url)

    # Definir la descripción para la bitácora
    descripcion = safe_message(f"Eliminado Edicto {edicto.id} por {current_user.email}")

    # Si es administrador, puede eliminar
    if current_user.can_admin(MODULO):
        edicto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=descripcion,
            url=detalle_url,
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Si NO le pertenece, mostrar mensaje y redirigir
    if current_user.autoridad_id != edicto.autoridad_id:
        flash("No se puede eliminar porque no le pertenece.", "warning")
        return redirect(detalle_url)

    # Si fue creado hace menos del limite de dias
    if edicto.creado >= datetime.now(tz=local_tz) - timedelta(days=LIMITE_DIAS_ELIMINAR):
        edicto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=descripcion,
            url=detalle_url,
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # No se puede eliminar
    flash(f"No se puede eliminar porque fue creado hace más de {LIMITE_DIAS_ELIMINAR} dias.", "warning")
    return redirect(detalle_url)


@edictos.route("/edictos/recuperar/<int:edicto_id>")
@permission_required(MODULO, Permiso.CREAR)
def recover(edicto_id):
    """Recuperar Edicto"""

    # Consultar
    edicto = Edicto.query.get_or_404(edicto_id)
    detalle_url = url_for("edictos.detail", edicto_id=edicto.id)

    # Validar que se pueda recuperar
    if edicto.estatus == "A":
        flash("No puede eliminar este Edicto porque ya está activo.", "success")
        return redirect(detalle_url)

    # Definir la descripción para la bitácora
    descripcion = safe_message(f"Recuperado Edicto {edicto.id} por {current_user.email}")

    # Si es administrador, puede recuperar
    if current_user.can_admin(MODULO):
        edicto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=descripcion,
            url=detalle_url,
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Si NO le pertenece, mostrar mensaje y redirigir
    if current_user.autoridad_id != edicto.autoridad_id:
        flash("No se puede recuperar porque no le pertenece.", "warning")
        return redirect(detalle_url)

    # Si fue creado hace menos del límite de días
    if edicto.creado >= datetime.now(tz=local_tz) - timedelta(days=LIMITE_DIAS_RECUPERAR):
        edicto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=descripcion,
            url=detalle_url,
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # No se puede recuperar
    flash(f"No se puede recuperar porque fue creado hace más de {LIMITE_DIAS_RECUPERAR} dias.", "warning")
    return redirect(detalle_url)


@edictos.route("/edictos/ver_archivo_pdf/<int:edicto_id>")
def view_file_pdf(edicto_id):
    """Ver archivo PDF de Edicto para insertarlo en un iframe en el detalle"""

    # Consultar
    edicto = Edicto.query.get_or_404(edicto_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_EDICTOS"],
            blob_name=get_blob_name_from_url(edicto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response


@edictos.route("/edictos/descargar_archivo_pdf/<int:edicto_id>")
def download_file_pdf(edicto_id):
    """Descargar archivo PDF de Edicto"""

    # Consultar
    edicto = Edicto.query.get_or_404(edicto_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_EDICTOS"],
            blob_name=get_blob_name_from_url(edicto.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.")

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={edicto.archivo}"
    return response


@edictos.route("/edictos/tablero_cantidades_por_dia_json")
@permission_required(MODULO, Permiso.VER)
def dashboard_amounts_per_day_json():
    """Calcular las cantidades de Edictos por día"""

    # Si viene autoridad_id o autoridad_clave en la URL, validar
    autoridad = None
    try:
        if "autoridad_id" in request.args:
            autoridad = Autoridad.query.get(int(request.args.get("autoridad_id")))
        elif "autoridad_clave" in request.args:
            autoridad = Autoridad.query.filter_by(clave=safe_clave(request.args.get("autoridad_clave"))).first()
    except (TypeError, ValueError):
        autoridad = None

    # Si viene la cantidad_dias en la URL, validar
    cantidad_dias = DASHBOARD_CANTIDAD_DIAS  # Por defecto
    try:
        if "cantidad_dias" in request.args:
            cantidad_dias = int(request.args.get("cantidad_dias"))
    except (TypeError, ValueError):
        cantidad_dias = DASHBOARD_CANTIDAD_DIAS

    # Consultar
    if autoridad is None:
        consulta = (
            database.session.query(
                func.cast(Edicto.creado, Date).label("creado"),
                func.count(Edicto.id).label("cantidad"),
            )
            .select_from(Edicto)
            .where(Edicto.estatus == "A")
            .where(Edicto.creado >= datetime.now() + timedelta(days=-cantidad_dias))
            .group_by(func.cast(Edicto.creado, Date))
            .order_by(func.cast(Edicto.creado, Date).desc())
            .limit(cantidad_dias)
            .all()
        )
    else:
        consulta = (
            database.session.query(
                func.cast(Edicto.creado, Date).label("creado"),
                func.count(Edicto.id).label("cantidad"),
            )
            .select_from(Edicto)
            .join(Autoridad)
            .where(Autoridad.id == autoridad.id)
            .where(Edicto.estatus == "A")
            .where(Edicto.creado >= datetime.now() + timedelta(days=-cantidad_dias))
            .group_by(func.cast(Edicto.creado, Date))
            .order_by(func.cast(Edicto.creado, Date).desc())
            .limit(cantidad_dias)
            .all()
        )

    # Bucle por cada día para agregar los que faltan con cantidad cero
    consulta_completo = []
    puntero = datetime.now() + timedelta(days=-cantidad_dias)
    while puntero < datetime.now() + timedelta(days=-1):
        dia = puntero.date()
        if len(consulta) > 0 and consulta[-1].creado == dia:
            item = consulta.pop()
            consulta_completo.append({"creado": item.creado, "cantidad": item.cantidad})
        else:
            consulta_completo.append({"creado": dia, "cantidad": 0})
        puntero += timedelta(days=1)

    # Entregar JSON
    return {
        "labels": [item["creado"].strftime("%Y-%m-%d") for item in consulta_completo],
        "data": [item["cantidad"] for item in consulta_completo],
    }


@edictos.route("/edictos/tablero")
@permission_required(MODULO, Permiso.VER)
def dashboard():
    """Tablero de Edictos"""

    # Por defecto
    autoridad = None
    titulo = "Tablero de Edictos"

    # Si la autoridad del usuario es jurisdiccional o es notaria, se impone
    if current_user.autoridad.es_jurisdiccional or current_user.autoridad.es_notaria:
        autoridad = current_user.autoridad
        titulo = f"Tablero de Edictos de {autoridad.clave}"

    # Si aun no hay autoridad y viene autoridad_id o autoridad_clave en la URL
    if autoridad is None:
        try:
            if "autoridad_id" in request.args:
                autoridad = Autoridad.query.get(int(request.args.get("autoridad_id")))
            elif "autoridad_clave" in request.args:
                autoridad = Autoridad.query.filter_by(clave=safe_clave(request.args.get("autoridad_clave"))).first()
            if autoridad:
                titulo = f"Tablero de Edictos de {autoridad.clave}"
        except (TypeError, ValueError):
            pass

    # Si viene la cantidad_dias en la URL, validar
    cantidad_dias = DASHBOARD_CANTIDAD_DIAS  # Por defecto
    try:
        if "cantidad_dias" in request.args:
            cantidad_dias = int(request.args.get("cantidad_dias"))
    except (TypeError, ValueError):
        cantidad_dias = DASHBOARD_CANTIDAD_DIAS

    # Entregar
    return render_template(
        "edictos/dashboard.jinja2",
        autoridad=autoridad,
        cantidad_dias=cantidad_dias,
        titulo=titulo,
    )
