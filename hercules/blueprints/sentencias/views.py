"""
Sentencias, vistas
"""

import datetime
import json
import re
from urllib.parse import quote

from flask import Blueprint, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from pytz import timezone
from sqlalchemy.sql.functions import count
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.exceptions import NotFound

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.materias.models import Materia
from hercules.blueprints.materias_tipos_juicios.models import MateriaTipoJuicio
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.sentencias.forms import SentenciaEditForm, SentenciaNewForm, SentenciaReportForm
from hercules.blueprints.sentencias.models import Sentencia
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.exceptions import (
    MyAnyError,
    MyBucketNotFoundError,
    MyFilenameError,
    MyFileNotFoundError,
    MyMissingConfigurationError,
    MyNotAllowedExtensionError,
    MyNotValidParamError,
    MyUnknownExtensionError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs, get_media_type_from_filename
from lib.safe_string import (
    extract_expediente_anio,
    extract_expediente_num,
    safe_clave,
    safe_expediente,
    safe_message,
    safe_sentencia,
    safe_string,
)
from lib.storage import GoogleCloudStorage
from lib.time_to_text import dia_mes_ano

HUSO_HORARIO = "America/Mexico_City"
MODULO = "SENTENCIAS"
LIMITE_DIAS = 365  # Un anio
LIMITE_ADMINISTRADORES_DIAS = 7300  # Administradores pueden manipular veinte anios

# Roles que deben estar en la base de datos
ROL_REPORTES_TODOS = ["ADMINISTRADOR", "ESTADISTICA", "VISITADURIA JUDICIAL"]

SUBDIRECTORIO = "sentencias"

sentencias = Blueprint("sentencias", __name__, template_folder="templates")


@sentencias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@sentencias.route("/sentencias/acuses/<id_hashed>")
def checkout(id_hashed):
    """Acuse"""
    sentencia = Sentencia.query.get_or_404(Sentencia.decode_id(id_hashed))
    dia, mes, ano = dia_mes_ano(sentencia.creado)
    return render_template("sentencias/checkout.jinja2", sentencia=sentencia, dia=dia, mes=mes.upper(), ano=ano)


@sentencias.route("/sentencias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Sentencias"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Sentencia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Sentencia.autoridad_id == autoridad.id)
    if "autoridad_clave" in request.form:
        try:
            autoridad_clave = safe_clave(request.form["autoridad_clave"])
            if autoridad_clave != "":
                consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
                print(consulta)
        except ValueError:
            pass
    if "sentencia" in request.form:
        try:
            sentencia = safe_sentencia(request.form["sentencia"])
            consulta = consulta.filter(Sentencia.sentencia == sentencia)
        except (IndexError, ValueError):
            pass
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter_by(expediente=expediente)
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
        consulta = consulta.filter(Sentencia.fecha >= fecha_desde)
    if fecha_hasta:
        consulta = consulta.filter(Sentencia.fecha <= fecha_hasta)
    # Filtrar por tipo de juicio
    if "tipo_juicio" in request.form:
        tipo_juicio = safe_string(request.form["tipo_juicio"], save_enie=True)
        if tipo_juicio != "":
            consulta = consulta.join(MateriaTipoJuicio).filter(MateriaTipoJuicio.descripcion.contains(tipo_juicio))
    # Ordenar y paginar
    registros = consulta.order_by(Sentencia.fecha.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "sentencia": resultado.sentencia,
                    "url": url_for("sentencias.detail", sentencia_id=resultado.id),
                },
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "autoridad": resultado.autoridad.clave,
                "expediente": resultado.expediente,
                "materia_nombre": resultado.materia_tipo_juicio.materia.nombre,
                "materia_tipo_juicio_descripcion": resultado.materia_tipo_juicio.descripcion,
                "es_perspectiva_genero": "Sí" if resultado.es_perspectiva_genero else "",
                "archivo": {
                    "descargar_url": resultado.descargar_url,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@sentencias.route("/sentencias/datatable_json_admin", methods=["GET", "POST"])
def datatable_json_admin():
    """DataTable JSON para listado de Sentencias admin"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Sentencia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "sentencia_id" in request.form:
        try:
            sentencia_id = int(request.form["sentencia_id"])
            consulta = consulta.filter(Sentencia.id == sentencia_id)
        except ValueError:
            pass
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter(Sentencia.autoridad_id == autoridad.id)
    if "autoridad_clave" in request.form:
        try:
            autoridad_clave = safe_clave(request.form["autoridad_clave"])
            if autoridad_clave != "":
                consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
        except ValueError:
            pass
    if "sentencia" in request.form:
        try:
            sentencia = safe_sentencia(request.form["sentencia"])
            consulta = consulta.filter(Sentencia.sentencia == sentencia)
        except (IndexError, ValueError):
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Sentencia.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Zona horaria local
    local_tz = timezone(HUSO_HORARIO)
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        creado_local = resultado.creado.astimezone(local_tz)  # La columna creado esta en UTC, convertir a local
        data.append(
            {
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("sentencias.detail", sentencia_id=resultado.id),
                },
                "creado": creado_local.strftime("%Y-%m-%d %H:%M:%S"),
                "autoridad": resultado.autoridad.clave,
                "fecha": resultado.fecha.strftime("%Y-%m-%d"),
                "sentencia": resultado.sentencia,
                "expediente": resultado.expediente,
                "materia_nombre": resultado.materia_tipo_juicio.materia.nombre,
                "materia_tipo_juicio_descripcion": resultado.materia_tipo_juicio.descripcion,
                "es_perspectiva_genero": "Sí" if resultado.es_perspectiva_genero else "",
                "archivo": {
                    "descargar_url": url_for("sentencias.download", url=quote(resultado.url)),
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@sentencias.route("/sentencias/datatable_tipos_de_juicios_json", methods=["GET", "POST"])
def datatable_tipos_de_juicios_json():
    """Datatable JSON con los tipos de juicios y sus cantidades"""
    # Tomar parámetros de Datatables
    draw, _, _ = get_datatable_parameters()
    # SQLAlchemy database session
    database = current_app.extensions["sqlalchemy"].db.session
    # Dos columnas en la consulta
    consulta = database.query(
        MateriaTipoJuicio.descripcion.label("tipo_de_juicio"),
        count("*").label("cantidad"),
    )
    # Juntar las tablas sentencias y materias_tipos_juicios
    consulta = consulta.select_from(Sentencia).join(MateriaTipoJuicio)
    # Debe venir la autoridad_id
    autoridad = Autoridad.query.get_or_404(request.form["autoridad_id"])
    consulta = consulta.filter(Sentencia.autoridad == autoridad)
    # Debe venir la fecha_desde
    consulta = consulta.filter(Sentencia.fecha >= request.form["fecha_desde"])
    # Debe venir la fecha_hasta
    consulta = consulta.filter(Sentencia.fecha <= request.form["fecha_hasta"])
    # Agrupar
    consulta = consulta.group_by(MateriaTipoJuicio.descripcion)
    # Ordenar
    consulta = consulta.order_by(MateriaTipoJuicio.descripcion)
    # Consultar
    resultados = consulta.all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in resultados:
        data.append(
            {
                "tipo_de_juicio": resultado.tipo_de_juicio,
                "cantidad": resultado.cantidad,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@sentencias.route("/sentencias")
def list_active():
    """Listado de Sentencias activos"""
    # Si es administrador ve todo
    if current_user.can_admin("SENTENCIAS"):
        return render_template(
            "sentencias/list_admin.jinja2",
            autoridad=None,
            filtros=json.dumps({"estatus": "A"}),
            titulo="Todas las V.P. de Sentencias",
            estatus="A",
            form=None,
        )
    # Si es jurisdiccional ve lo de su autoridad
    if current_user.autoridad.es_jurisdiccional:
        autoridad = current_user.autoridad
        form = SentenciaReportForm()
        form.autoridad_id.data = autoridad.id  # Oculto la autoridad del usuario
        form.fecha_desde.data = datetime.date.today().replace(day=1)  # Por defecto fecha_desde es el primer dia del mes actual
        form.fecha_hasta.data = datetime.date.today()  # Por defecto fecha_hasta es hoy
        return render_template(
            "sentencias/list.jinja2",
            autoridad=autoridad,
            filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
            titulo=f"V.P. de Sentencias de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
            estatus="A",
            form=form,
        )
    # Ninguno de los anteriores
    return redirect(url_for("sentencias.list_distritos"))


@sentencias.route("/sentencias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Sentencias inactivos"""
    # Si es administrador ve todo
    if current_user.can_admin("SENTENCIAS"):
        return render_template(
            "sentencias/list_admin.jinja2",
            autoridad=None,
            filtros=json.dumps({"estatus": "B"}),
            titulo="Todas las V.P. de Sentencias inactivas",
            estatus="B",
            form=None,
        )
    # Si es jurisdiccional ve lo de su autoridad
    if current_user.autoridad.es_jurisdiccional:
        autoridad = current_user.autoridad
        return render_template(
            "sentencias/list.jinja2",
            autoridad=autoridad,
            filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "B"}),
            titulo=f"V.P. de Sentencias inactivas de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
            estatus="B",
            form=None,
        )
    # No es jurisdiccional, se redirige al listado de distritos
    return redirect(url_for("sentencias.list_distritos"))


@sentencias.route("/sentencias/autoridad/<int:autoridad_id>")
def list_autoridad_sentencias(autoridad_id):
    """Listado de Sentencias activas de una autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    form = None
    plantilla = "sentencias/list.jinja2"
    if current_user.can_admin("SENTENCIAS") or set(current_user.get_roles()).intersection(set(ROL_REPORTES_TODOS)):
        plantilla = "sentencias/list_admin.jinja2"
        form = SentenciaReportForm()
        form.autoridad_id.data = autoridad.id  # Oculto la autoridad que esta viendo
        form.fecha_desde.data = datetime.date.today().replace(day=1)  # Por defecto fecha_desde es el primer dia del mes actual
        form.fecha_hasta.data = datetime.date.today()  # Por defecto fecha_hasta es hoy
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
        titulo=f"V.P. de Sentencias de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
        estatus="A",
        form=form,
    )


@sentencias.route("/sentencias/inactivos/autoridad/<int:autoridad_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_autoridad_sentencias_inactive(autoridad_id):
    """Listado de Sentencias inactivas de una autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if current_user.can_admin("SENTENCIAS"):
        plantilla = "sentencias/list_admin.jinja2"
    else:
        plantilla = "sentencias/list.jinja2"
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "B"}),
        titulo=f"V.P. de Sentencias inactivas de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
        estatus="B",
        form=None,
    )


@sentencias.route("/sentencias/descargar", methods=["GET"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def download():
    """Descargar archivo desde Google Cloud Storage"""
    url = request.args.get("url")
    try:
        # Obtener nombre del blob
        blob_name = get_blob_name_from_url(url)
        # Obtener tipo de media
        media_type = get_media_type_from_filename(blob_name)
        # Obtener archivo
        archivo = get_file_from_gcs(current_app.config["CLOUD_STORAGE_DEPOSITO_SENTENCIAS"], blob_name)
    except MyAnyError as error:
        flash(str(error), "warning")
        return redirect(url_for("sentencias.list_active"))
    # Entregar archivo
    return current_app.response_class(archivo, mimetype=media_type)


@sentencias.route("/sentencias/<int:sentencia_id>")
def detail(sentencia_id):
    """Detalle de un Sentencia"""
    sentencia = Sentencia.query.get_or_404(sentencia_id)
    return render_template("sentencias/detail.jinja2", sentencia=sentencia)


def new_success(sentencia):
    """Mensaje de éxito en nueva sentencia"""
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(
            f"Nueva sentencia {sentencia.sentencia}, expediente {sentencia.expediente} de {sentencia.autoridad.clave}"
        ),
        url=url_for("sentencias.detail", sentencia_id=sentencia.id),
    )
    bitacora.save()
    return bitacora


@sentencias.route("/sentencias/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Sentencia"""

    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad is None or autoridad.estatus != "A":
        flash("El juzgado/autoridad no existe o no es activa.", "warning")
        return redirect(url_for("sentencias.list_active"))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("sentencias.list_active"))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("sentencias.list_active"))
    if autoridad.directorio_sentencias is None or autoridad.directorio_sentencias == "":
        flash("El juzgado/autoridad no tiene directorio para sentencias.", "warning")
        return redirect(url_for("sentencias.list_active"))

    # Para validar las fechas
    hoy = datetime.date.today()
    hoy_dt = datetime.datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + datetime.timedelta(days=-LIMITE_DIAS)

    form = SentenciaNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar sentencia
        try:
            sentencia_input = safe_sentencia(form.sentencia.data)
        except (IndexError, ValueError):
            flash("La sentencia es incorrecta.", "warning")
            es_valido = False

        # Validar sentencia_fecha
        sentencia_fecha = form.sentencia_fecha.data
        if (
            not limite_dt
            <= datetime.datetime(year=sentencia_fecha.year, month=sentencia_fecha.month, day=sentencia_fecha.day)
            <= hoy_dt
        ):
            flash(f"La fecha de la sentencia no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime.datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            es_valido = False

        # Tomar tipo de juicio
        materia_tipo_juicio = MateriaTipoJuicio.query.get(form.materia_tipo_juicio.data)

        # Tomar descripcion
        descripcion = safe_string(form.descripcion.data, max_len=1000)

        # Tomar perspectiva de género
        es_perspectiva_genero = form.es_perspectiva_genero.data  # Boleano

        # Validar archivo
        archivo = request.files["archivo"]
        storage = GoogleCloudStorage(base_directory=SUBDIRECTORIO, allowed_extensions=["pdf"])
        try:
            storage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False
        # Si es valido
        if es_valido:
            # Insertar registro
            sentencia = Sentencia(
                autoridad=autoridad,
                materia_tipo_juicio=materia_tipo_juicio,
                sentencia=sentencia_input,
                sentencia_fecha=sentencia_fecha,
                expediente=expediente,
                expediente_anio=extract_expediente_anio(expediente),
                expediente_num=extract_expediente_num(expediente),
                fecha=fecha,
                descripcion=descripcion,
                es_perspectiva_genero=es_perspectiva_genero,
            )
            sentencia.save()

            # El nombre del archivo contiene FECHA/SENTENCIA/EXPEDIENTE/PERSPECTIVA_GENERO/HASH
            nombre_elementos = []
            nombre_elementos.append(sentencia_input.replace("/", "-"))
            nombre_elementos.append(expediente.replace("/", "-"))
            if es_perspectiva_genero:
                nombre_elementos.append("G")

            # Subir a Google Cloud Storage
            es_exitoso = True
            try:
                storage.set_filename(hashed_id=sentencia.encode_id(), description="-".join(nombre_elementos))
                storage.upload(archivo.stream.read())
            except (MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError):
                flash("Error fatal al subir el archivo a GCS.", "warning")
                es_exitoso = False
            except MyMissingConfigurationError:
                flash("Error al subir el archivo porque falla la configuración de GCS.", "danger")
                es_exitoso = False
            except Exception:
                flash("Error desconocido al subir el archivo.", "danger")
                es_exitoso = False

            # Si se sube con exito, actualizar el registro con la URL del archivo y mostrar el detalle
            if es_exitoso:
                sentencia.archivo = storage.filename  # Conservar el nombre original
                sentencia.url = storage.url
                sentencia.save()
                bitacora = new_success(sentencia)
                flash(bitacora.descripcion, "success")
                return redirect(bitacora.url)

            # Como no se subio con exito, se cambia el estatus a "B"
            sentencia.estatus = "B"
            sentencia.save()

    # Llenar de los campos del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy
    return render_template(
        "sentencias/new.jinja2",
        form=form,
        autoridad=autoridad,
        materias=Materia.query.filter_by(en_sentencias=True).filter_by(estatus="A").order_by(Materia.id).all(),
        materias_tipos_juicios=MateriaTipoJuicio.query.filter_by(estatus="A")
        .order_by(MateriaTipoJuicio.materia_id, MateriaTipoJuicio.descripcion)
        .all(),
    )


@sentencias.route("/sentencias/nuevo/<int:autoridad_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.ADMINISTRAR)
def new_for_autoridad(autoridad_id):
    """Nuevo Sentencia"""

    # Validar autoridad
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if autoridad is None:
        flash("El juzgado/autoridad no existe.", "warning")
        return redirect(url_for("sentencias.list_active"))
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if not autoridad.distrito.es_distrito_judicial:
        flash("El juzgado/autoridad no está en un distrito jurisdiccional.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if not autoridad.es_jurisdiccional:
        flash("El juzgado/autoridad no es jurisdiccional.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))
    if autoridad.directorio_sentencias is None or autoridad.directorio_sentencias == "":
        flash("El juzgado/autoridad no tiene directorio para edictos.", "warning")
        return redirect(url_for("autoridades.detail", autoridad_id=autoridad.id))

    # Para validar las fechas
    hoy = datetime.date.today()
    hoy_dt = datetime.datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + datetime.timedelta(days=-LIMITE_ADMINISTRADORES_DIAS)

    form = SentenciaNewForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        es_valido = True

        # Validar sentencia
        try:
            sentencia_input = safe_sentencia(form.sentencia.data)
        except (IndexError, ValueError):
            flash("La sentencia es incorrecta.", "warning")
            es_valido = False

        # Validar sentencia_fecha
        sentencia_fecha = form.sentencia_fecha.data
        if (
            not limite_dt
            <= datetime.datetime(year=sentencia_fecha.year, month=sentencia_fecha.month, day=sentencia_fecha.day)
            <= hoy_dt
        ):
            flash(
                f"La fecha de la sentencia no debe ser del futuro ni anterior a {LIMITE_ADMINISTRADORES_DIAS} días.", "warning"
            )
            es_valido = False

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Validar fecha
        fecha = form.fecha.data
        if not limite_dt <= datetime.datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_ADMINISTRADORES_DIAS} días.", "warning")
            es_valido = False

        # Tomar tipo de juicio
        materia_tipo_juicio = MateriaTipoJuicio.query.get(form.materia_tipo_juicio.data)

        # Tomar descripcion
        descripcion = safe_string(form.descripcion.data, max_len=1000)

        # Tomar perspectiva de género
        es_perspectiva_genero = form.es_perspectiva_genero.data  # Boleano

        # Validar archivo
        archivo = request.files["archivo"]
        storage = GoogleCloudStorage(base_directory=SUBDIRECTORIO, allowed_extensions=["pdf"])
        try:
            storage.set_content_type(archivo.filename)
        except MyNotAllowedExtensionError:
            flash("Tipo de archivo no permitido.", "warning")
            es_valido = False
        except MyUnknownExtensionError:
            flash("Tipo de archivo desconocido.", "warning")
            es_valido = False

        # Si es valido
        if es_valido:
            # Insertar registro
            sentencia = Sentencia(
                autoridad=autoridad,
                materia_tipo_juicio=materia_tipo_juicio,
                sentencia=sentencia_input,
                sentencia_fecha=sentencia_fecha,
                expediente=expediente,
                expediente_anio=extract_expediente_anio(expediente),
                expediente_num=extract_expediente_num(expediente),
                fecha=fecha,
                descripcion=descripcion,
                es_perspectiva_genero=es_perspectiva_genero,
            )
            sentencia.save()

            # El nombre del archivo contiene FECHA/SENTENCIA/EXPEDIENTE/PERSPECTIVA_GENERO/HASH
            nombre_elementos = []
            nombre_elementos.append(sentencia_input.replace("/", "-"))
            nombre_elementos.append(expediente.replace("/", "-"))
            if es_perspectiva_genero:
                nombre_elementos.append("G")

            # Subir a Google Cloud Storage
            es_exitoso = True
            try:
                storage.set_filename(hashed_id=sentencia.encode_id(), description="-".join(nombre_elementos))
                storage.upload(archivo.stream.read())
            except (MyFilenameError, MyNotAllowedExtensionError, MyUnknownExtensionError):
                flash("Error fatal al subir el archivo a GCS.", "warning")
                es_exitoso = False
            except MyMissingConfigurationError:
                flash("Error al subir el archivo porque falla la configuración de GCS.", "danger")
                es_exitoso = False
            except Exception:
                flash("Error desconocido al subir el archivo.", "danger")
                es_exitoso = False

            # Si se sube con exito, actualizar el registro con la URL del archivo y mostrar el detalle
            if es_exitoso:
                sentencia.archivo = storage.filename  # Conservar el nombre original
                sentencia.url = storage.url
                sentencia.save()
                bitacora = new_success(sentencia)
                flash(bitacora.descripcion, "success")
                return redirect(bitacora.url)

            # Como no se subio con exito, se cambia el estatus a "B"
            sentencia.estatus = "B"
            sentencia.save()

    # Llenar de los campos del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.fecha.data = hoy
    return render_template(
        "sentencias/new_for_autoridad.jinja2",
        form=form,
        autoridad=autoridad,
        materias=Materia.query.filter_by(en_sentencias=True).filter_by(estatus="A").order_by(Materia.id).all(),
        materias_tipos_juicios=MateriaTipoJuicio.query.filter_by(estatus="A")
        .order_by(MateriaTipoJuicio.materia_id, MateriaTipoJuicio.descripcion)
        .all(),
    )


@sentencias.route("/sentencias/edicion/<int:sentencia_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(sentencia_id):
    """Editar Sentencia"""

    # Para validar las fechas
    hoy = datetime.date.today()
    hoy_dt = datetime.datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = hoy_dt + datetime.timedelta(days=-LIMITE_DIAS)

    # Validar sentencia
    sentencia = Sentencia.query.get_or_404(sentencia_id)
    if not (current_user.can_admin("SENTENCIAS") or current_user.autoridad_id == sentencia.autoridad_id):
        flash("No tiene permiso para editar esta sentencia.", "warning")
        return redirect(url_for("sentencias.list_active"))

    form = SentenciaEditForm()
    if form.validate_on_submit():
        es_valido = True

        # Validar sentencia
        try:
            sentencia.sentencia = safe_sentencia(form.sentencia.data)
        except (IndexError, ValueError):
            flash("La sentencia es incorrecta.", "warning")
            es_valido = False

        # Validar sentencia_fecha
        sentencia.sentencia_fecha = form.sentencia_fecha.data
        if (
            not limite_dt
            <= datetime.datetime(
                year=sentencia.sentencia_fecha.year, month=sentencia.sentencia_fecha.month, day=sentencia.sentencia_fecha.day
            )
            <= hoy_dt
        ):
            flash(f"La fecha de la sentencia no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            es_valido = False

        # Validar expediente
        try:
            sentencia.expediente = safe_expediente(form.expediente.data)
            sentencia.expediente_anio = extract_expediente_anio(sentencia.expediente)
            sentencia.expediente_num = extract_expediente_num(sentencia.expediente)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            es_valido = False

        # Validar fecha
        sentencia.fecha = form.fecha.data
        if (
            not limite_dt
            <= datetime.datetime(year=sentencia.fecha.year, month=sentencia.fecha.month, day=sentencia.fecha.day)
            <= hoy_dt
        ):
            flash(f"La fecha no debe ser del futuro ni anterior a {LIMITE_DIAS} días.", "warning")
            es_valido = False

        # Tomar perspectiva de genero
        sentencia.es_perspectiva_genero = form.es_perspectiva_genero.data

        # Tomar tipo de juicio
        sentencia.materia_tipo_juicio = MateriaTipoJuicio.query.get(form.materia_tipo_juicio.data)

        # Tomar descripcion
        sentencia.descripcion = safe_string(form.descripcion.data, max_len=1000)

        if es_valido:
            sentencia.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Sentencia {sentencia.sentencia}"),
                url=url_for("sentencias.detail", sentencia_id=sentencia.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)

    # Llenar de los campos del formulario
    form.sentencia.data = sentencia.sentencia
    form.sentencia_fecha.data = sentencia.sentencia_fecha
    form.expediente.data = sentencia.expediente
    form.fecha.data = sentencia.fecha
    form.descripcion.data = sentencia.descripcion
    form.es_perspectiva_genero.data = sentencia.es_perspectiva_genero
    return render_template(
        "sentencias/edit.jinja2",
        form=form,
        sentencia=sentencia,
        materias=Materia.query.filter_by(en_sentencias=True).filter_by(estatus="A").order_by(Materia.id).all(),
        materias_tipos_juicios=MateriaTipoJuicio.query.filter_by(estatus="A")
        .order_by(MateriaTipoJuicio.materia_id, MateriaTipoJuicio.descripcion)
        .all(),
    )


def delete_success(sentencia, descripcion):
    """Mensaje de éxito al eliminar una sentencia"""
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(descripcion),
        url=url_for("sentencias.detail", sentencia_id=sentencia.id),
    )
    bitacora.save()


@sentencias.route("/sentencias/eliminar/<int:sentencia_id>")
@permission_required(MODULO, Permiso.CREAR)
def delete(sentencia_id):
    """Eliminar Sentencia"""
    sentencia = Sentencia.query.get_or_404(sentencia_id)
    bitacora_descripcion = f"Eliminada la sentencia {sentencia.sentencia} de {sentencia.autoridad.clave}"
    if sentencia.estatus == "A":
        # Los administradores puede eliminar cualquiera dentro de los limites
        if current_user.can_admin("SENTENCIAS"):
            hoy = datetime.date.today()
            hoy_dt = datetime.datetime(year=hoy.year, month=hoy.month, day=hoy.day)
            limite_dt = hoy_dt + datetime.timedelta(days=-LIMITE_ADMINISTRADORES_DIAS)
            if limite_dt.timestamp() > sentencia.creado.timestamp():
                flash("No puede eliminar porque fue creado antes de la fecha límite.", "warning")
                return redirect(url_for("sentencias.detail", sentencia_id=sentencia.id))
            sentencia.delete()
            delete_success(sentencia, bitacora_descripcion)
            flash("Sentencia eliminada exitosamente", "success")
        # Los jurisdiccionales solo pueden eliminar las suyas y que sean de hoy
        elif current_user.autoridad_id == sentencia.autoridad_id and sentencia.fecha == datetime.date.today():
            sentencia.delete()
            delete_success(sentencia, bitacora_descripcion)
            flash("Sentencia eliminada exitosamente", "success")
        else:
            flash("No tiene permiso para eliminar o sólo puede eliminar de hoy.", "warning")
    return redirect(url_for("sentencias.detail", sentencia_id=sentencia.id))


def recover_success(sentencia, descripcion):
    """Mensaje de éxito al recuperar una sentencia"""
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(descripcion),
        url=url_for("sentencias.detail", sentencia_id=sentencia.id),
    )
    bitacora.save()


@sentencias.route("/sentencias/recuperar/<int:sentencia_id>")
@permission_required(MODULO, Permiso.CREAR)
def recover(sentencia_id):
    """Recuperar Sentencia"""
    sentencia = Sentencia.query.get_or_404(sentencia_id)
    bitacora_descripcion = f"Recuperada la sentencia del {sentencia.sentencia} de {sentencia.autoridad.clave}"
    if sentencia.estatus == "B":
        # Evitar que se recupere si ya existe una con la misma sentencia
        if (
            Sentencia.query.filter(Sentencia.autoridad == current_user.autoridad)
            .filter(Sentencia.sentencia == sentencia.sentencia)
            .filter_by(estatus="A")
            .first()
        ):
            flash(
                f"No se puede recuperar la sentencia {sentencia.sentencia}, ya hay una sentencia activa con el mismo número.",
                "warning",
            )
            return redirect(url_for("sentencias.detail", sentencia_id=sentencia.id))
        # Los administradores pueden recuperar cualquiera dentro de los limites
        if current_user.can_admin("SENTENCIAS"):
            hoy = datetime.date.today()
            hoy_dt = datetime.datetime(year=hoy.year, month=hoy.month, day=hoy.day)
            limite_dt = hoy_dt + datetime.timedelta(days=-LIMITE_ADMINISTRADORES_DIAS)
            if limite_dt.timestamp() > sentencia.creado.timestamp():
                flash("No puede recuperar porque fue creado antes de la fecha límite.", "warning")
                return redirect(url_for("sentencias.detail", sentencia_id=sentencia.id))
            sentencia.recover()
            recover_success(sentencia, bitacora_descripcion)
            flash("Sentencia recuperada exitosamente", "success")
        elif current_user.autoridad_id == sentencia.autoridad_id and sentencia.fecha == datetime.date.today():
            sentencia.recover()
            recover_success(sentencia, bitacora_descripcion)
            flash("Sentencia recuperada exitosamente", "success")
        else:
            flash("No tiene permiso para recuperar o sólo puede recuperar de hoy.", "warning")
    return redirect(url_for("sentencias.detail", sentencia_id=sentencia.id))


@sentencias.route("/sentencias/reporte", methods=["GET", "POST"])
def report():
    """Elaborar reporte de sentencias"""
    # Preparar el formulario
    form = SentenciaReportForm()
    # Si viene el formulario
    if form.validate():
        # Tomar valores del formulario
        autoridad = Autoridad.query.get_or_404(int(form.autoridad_id.data))
        fecha_desde = form.fecha_desde.data
        fecha_hasta = form.fecha_hasta.data
        por_tipos_de_juicios = bool(form.por_tipos_de_juicios.data)
        # Si la fecha_desde es posterior a la fecha_hasta, se intercambian
        if fecha_desde > fecha_hasta:
            fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
        # Si no es administrador, ni tiene un rol para elaborar reportes de todos
        if not current_user.can_admin("SENTENCIAS") and not set(current_user.get_roles()).intersection(set(ROL_REPORTES_TODOS)):
            # Si la autoridad del usuario no es la del formulario, se niega el acceso
            if current_user.autoridad_id != autoridad.id:
                flash("No tiene permiso para acceder a este reporte.", "warning")
                return redirect(url_for("sentencias.list_active"))
        # Si es por tipos de juicios
        if por_tipos_de_juicios:
            # Entregar pagina con los tipos de juicios y sus cantidades
            return render_template(
                "sentencias/report_tipos_de_juicios.jinja2",
                autoridad=autoridad,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                filtros=json.dumps(
                    {
                        "autoridad_id": autoridad.id,
                        "estatus": "A",
                        "fecha_desde": fecha_desde.strftime("%Y-%m-%d"),
                        "fecha_hasta": fecha_hasta.strftime("%Y-%m-%d"),
                    }
                ),
            )
        # De lo contrario, entregar pagina con el reporte de sentencias y enlaces publicos
        return render_template(
            "sentencias/report.jinja2",
            autoridad=autoridad,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            filtros=json.dumps(
                {
                    "autoridad_id": autoridad.id,
                    "estatus": "A",
                    "fecha_desde": fecha_desde.strftime("%Y-%m-%d"),
                    "fecha_hasta": fecha_hasta.strftime("%Y-%m-%d"),
                }
            ),
        )
    # No viene el formulario, por lo tanto se advierte del error
    flash("Error: datos incorrectos para hacer el reporte de sentencias.", "warning")
    return redirect(url_for("sentencias.list_active"))


@sentencias.route("/sentencias/ver_archivo_pdf/<int:sentencia_id>")
def view_file_pdf(sentencia_id):
    """Ver archivo PDF de Sentencia para insertarlo en un iframe en el detalle"""

    # Consultar la sentencia
    sentencia = Sentencia.query.get_or_404(sentencia_id)

    # Obtener el contenido del archivo
    try:
        archivo = get_file_from_gcs(
            bucket_name=current_app.config["CLOUD_STORAGE_DEPOSITO_SENTENCIAS"],
            blob_name=get_blob_name_from_url(sentencia.url),
        )
    except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
        raise NotFound("No se encontró el archivo.") from error

    # Entregar el archivo
    response = make_response(archivo)
    response.headers["Content-Type"] = "application/pdf"
    return response
