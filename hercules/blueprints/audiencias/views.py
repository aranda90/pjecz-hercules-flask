"""
Audiencias, vistas
"""

import json
import re
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from hercules.blueprints.audiencias.forms import AudienciaDipeForm, AudienciaGenericaForm, AudienciaMapoForm, AudienciaSapeForm
from hercules.blueprints.audiencias.models import Audiencia
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_clave, safe_expediente, safe_message, safe_string
from lib.time_utc import join_for_message

MODULO = "AUDIENCIAS"

audiencias = Blueprint("audiencias", __name__, template_folder="templates")


def plantilla_por_categoria(categoria: str, prefijo: str = "list_", sufijo: str = "", por_defecto: str = "list"):
    """Determinar la plantilla por tipo de agenda de audiencia"""
    if categoria == "CIVIL FAMILIAR MERCANTIL LETRADO TCYA":
        nombre = f"{prefijo}generica{sufijo}"
    elif categoria == "MATERIA ACUSATORIO PENAL ORAL":
        nombre = f"{prefijo}mapo{sufijo}"
    elif categoria == "DISTRITALES":
        nombre = f"{prefijo}dipe{sufijo}"
    elif categoria == "SALAS":
        nombre = f"{prefijo}sape{sufijo}"
    else:
        nombre = por_defecto
    return f"audiencias/{nombre}.jinja2"


@audiencias.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@audiencias.route("/audiencias/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Audiencias"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Audiencia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter_by(autoridad=autoridad)
    # Obtener valores de tiempo desde y hasta
    tiempo_desde = None
    tiempo_hasta = None
    # Verificar si "tiempo_desde" está en el formulario y tiene el formato correcto
    if "tiempo_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", request.form["tiempo_desde"]):
        # Reemplazar "T" por un espacio para que coincida con el formato de la base de datos
        tiempo_desde = request.form["tiempo_desde"].replace("T", " ")
    # Verificar si "tiempo_hasta" está en el formulario y tiene el formato correcto
    if "tiempo_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", request.form["tiempo_hasta"]):
        # Reemplazar "T" por un espacio para que coincida con el formato de la base de datos
        tiempo_hasta = request.form["tiempo_hasta"].replace("T", " ")
    # Intercambiar tiempos si el desde es mayor que el hasta
    if tiempo_desde and tiempo_hasta and tiempo_desde > tiempo_hasta:
        tiempo_desde, tiempo_hasta = tiempo_hasta, tiempo_desde
    # Aplicar los filtros a la consulta
    if tiempo_desde:
        consulta = consulta.filter(Audiencia.tiempo >= tiempo_desde)
    if tiempo_hasta:
        consulta = consulta.filter(Audiencia.tiempo <= tiempo_hasta)
    if "tipo_audiencia" in request.form:
        tipo_audiencia = safe_string(request.form["tipo_audiencia"], save_enie=True)
        if tipo_audiencia != "":
            consulta = consulta.filter(Audiencia.tipo_audiencia.contains(tipo_audiencia))
    if "expediente" in request.form:
        try:
            expediente = safe_expediente(request.form["expediente"])
            consulta = consulta.filter_by(expediente=expediente)
        except (IndexError, ValueError):
            pass
    # Ordenar y paginar
    registros = consulta.order_by(Audiencia.tiempo.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "detalle": {
                    "tiempo": resultado.tiempo.strftime("%Y-%m-%d %H:%M"),
                    "url": url_for("audiencias.detail", audiencia_id=resultado.id),
                },
                "tipo_audiencia": resultado.tipo_audiencia,
                "expediente": resultado.expediente,
                "actores": resultado.actores,
                "demandados": resultado.demandados,
                "sala": resultado.sala,
                "caracter": resultado.caracter,
                "causa_penal": resultado.causa_penal,
                "delitos": resultado.delitos,
                "toca": resultado.toca,
                "expediente_origen": resultado.expediente_origen,
                "imputados": resultado.imputados,
                "origen": resultado.origen,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@audiencias.route("/audiencias/datatable_json_admin", methods=["GET", "POST"])
def datatable_json_admin():
    """DataTable JSON para listado de Audiencias"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = Audiencia.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "audiencia_id" in request.form:
        try:
            audiencia_id = int(request.form["audiencia_id"])
            consulta = consulta.filter(Audiencia.id == audiencia_id)
        except ValueError:
            pass
    if "autoridad_id" in request.form:
        autoridad = Autoridad.query.get(request.form["autoridad_id"])
        if autoridad:
            consulta = consulta.filter_by(autoridad=autoridad)
    if "autoridad_clave" in request.form:
        try:
            autoridad_clave = safe_clave(request.form["autoridad_clave"])
            if autoridad_clave != "":
                consulta = consulta.join(Autoridad).filter(Autoridad.clave.contains(autoridad_clave))
        except ValueError:
            pass
    # Obtener valores de tiempo desde y hasta
    tiempo_desde = None
    tiempo_hasta = None
    # Verificar si "tiempo_desde" está en el formulario y tiene el formato correcto
    if "tiempo_desde" in request.form and re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", request.form["tiempo_desde"]):
        # Reemplazar "T" por un espacio para que coincida con el formato de la base de datos
        tiempo_desde = request.form["tiempo_desde"].replace("T", " ")
    # Verificar si "tiempo_hasta" está en el formulario y tiene el formato correcto
    if "tiempo_hasta" in request.form and re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", request.form["tiempo_hasta"]):
        # Reemplazar "T" por un espacio para que coincida con el formato de la base de datos
        tiempo_hasta = request.form["tiempo_hasta"].replace("T", " ")
    # Intercambiar tiempos si el desde es mayor que el hasta
    if tiempo_desde and tiempo_hasta and tiempo_desde > tiempo_hasta:
        tiempo_desde, tiempo_hasta = tiempo_hasta, tiempo_desde
    # Aplicar los filtros a la consulta
    if tiempo_desde:
        consulta = consulta.filter(Audiencia.tiempo >= tiempo_desde)
    if tiempo_hasta:
        consulta = consulta.filter(Audiencia.tiempo <= tiempo_hasta)
    if "tipo_audiencia" in request.form:
        tipo_audiencia = safe_string(request.form["tipo_audiencia"], save_enie=True)
        if tipo_audiencia != "":
            consulta = consulta.filter(Audiencia.tipo_audiencia.contains(tipo_audiencia))
    # Ordenar y paginar
    registros = consulta.order_by(Audiencia.creado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "creado": resultado.creado.strftime("%Y-%m-%dT%H:%M:%S"),
                "autoridad": resultado.autoridad.clave,
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("audiencias.detail", audiencia_id=resultado.id),
                },
                "tiempo": resultado.tiempo.strftime("%Y-%m-%d %H:%M"),
                "tipo_audiencia": resultado.tipo_audiencia,
                "expediente": resultado.expediente,
                "actores": resultado.actores,
                "demandados": resultado.demandados,
                "sala": resultado.sala,
                "caracter": resultado.caracter,
                "causa_penal": resultado.causa_penal,
                "delitos": resultado.delitos,
                "toca": resultado.toca,
                "expediente_origen": resultado.expediente_origen,
                "imputados": resultado.imputados,
                "origen": resultado.origen,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@audiencias.route("/audiencias")
def list_active():
    """Listado de Audiencias activos"""
    # Si es administrador ve todo
    if current_user.can_admin("AUDIENCIAS"):
        return render_template(
            "audiencias/list_admin.jinja2",
            autoridad=None,
            filtros=json.dumps({"estatus": "A"}),
            titulo="Todos las Audiencias",
            estatus="A",
        )
    # Si es jurisdiccional ve lo de su autoridad
    if current_user.autoridad.es_jurisdiccional:
        autoridad = current_user.autoridad
        return render_template(
            plantilla_por_categoria(autoridad.audiencia_categoria, por_defecto="list"),
            autoridad=autoridad,
            filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
            titulo=f"Audiencias de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
            estatus="A",
        )
    # Ninguno de los anteriores
    return redirect(url_for("audiencias.list_distritos"))


@audiencias.route("/audiencias/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Audiencias inactivos"""
    # Si es administrador ve todo
    if current_user.can_admin("AUDIENCIAS"):
        return render_template(
            "audiencias/list_admin.jinja2",
            autoridad=None,
            filtros=json.dumps({"estatus": "B"}),
            titulo="Todos las Audiencias inactivos",
            estatus="B",
        )
    # Si es jurisdiccional ve lo de su autoridad
    if current_user.autoridad.es_jurisdiccional:
        autoridad = current_user.autoridad
        return render_template(
            plantilla_por_categoria(autoridad.audiencia_categoria, por_defecto="list"),
            autoridad=autoridad,
            filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "B"}),
            titulo=f"Audiencias inactivas de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
            estatus="B",
        )
    # Ninguno de los anteriores
    return redirect(url_for("audiencias.list_distritos"))


@audiencias.route("/audiencias/autoridad/<int:autoridad_id>")
def list_autoridad_audiencias(autoridad_id):
    """Listado de Audiencias activas de una autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if current_user.can_admin("AUDIENCIAS"):
        plantilla = plantilla_por_categoria(autoridad.audiencia_categoria, sufijo="_admin", por_defecto="list_admin")
    else:
        plantilla = plantilla_por_categoria(autoridad.audiencia_categoria, por_defecto="list")
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "A"}),
        titulo=f"Audiencias de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
        estatus="A",
    )


@audiencias.route("/audiencias/inactivos/autoridad/<int:autoridad_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_autoridad_audiencias_inactive(autoridad_id):
    """Listado de Audiencias inactivas de una autoridad"""
    autoridad = Autoridad.query.get_or_404(autoridad_id)
    if current_user.can_admin("AUDIENCIAS"):
        plantilla = plantilla_por_categoria(autoridad.audiencia_categoria, sufijo="_admin", por_defecto="list_admin")
    else:
        plantilla = plantilla_por_categoria(autoridad.audiencia_categoria, por_defecto="list")
    return render_template(
        plantilla,
        autoridad=autoridad,
        filtros=json.dumps({"autoridad_id": autoridad.id, "estatus": "B"}),
        titulo=f"Audiencias inactivas de {autoridad.distrito.nombre_corto}, {autoridad.descripcion_corta}",
        estatus="B",
    )


@audiencias.route("/audiencias/<int:audiencia_id>")
def detail(audiencia_id):
    """Detalle de un Audiencia"""
    audiencia = Audiencia.query.get_or_404(audiencia_id)
    return render_template("audiencias/detail.jinja2", audiencia=audiencia)


@audiencias.route("/audiencias/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nueva Audiencia"""
    autoridad = current_user.autoridad
    if autoridad is None or autoridad.estatus != "A":
        flash("Su juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("audiencias.list_active"))
    if autoridad.audiencia_categoria == "CIVIL FAMILIAR MERCANTIL LETRADO TCYA":
        return redirect(url_for("audiencias.new_generica"))
    if autoridad.audiencia_categoria == "MATERIA ACUSATORIO PENAL ORAL":
        print("Si estoy entrando a esta validacions")
        return redirect(url_for("audiencias.new_mapo"))
    if autoridad.audiencia_categoria == "DISTRITALES":
        return redirect(url_for("audiencias.new_dipe"))
    if autoridad.audiencia_categoria == "SALAS":
        return redirect(url_for("audiencias.new_sape"))
    flash("El juzgado/autoridad no tiene una categoría de audiencias correcta.", "warning")
    return redirect(url_for("audiencias.list_active"))


@audiencias.route("/audiencias/nuevo/dipe", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_dipe():
    """Nueva Audiencia DISTRITALES"""

    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("audiencias.list_active"))
    if autoridad.audiencia_categoria != "DISTRITALES":
        flash("La categoría de audiencia no es DISTRITALES.", "warning")
        return redirect(url_for("audiencias.list_active"))

    # Si viene el formulario
    form = AudienciaDipeForm()
    if form.validate_on_submit():
        # Definir tiempo con la fecha y horas:minutos
        try:
            tiempo = f"{form.tiempo_fecha.data} {form.tiempo_horas_minutos.data}"
            tiempo = datetime.strptime(tiempo, "%Y-%m-%d %H:%M:%S")
            tiempo_mensaje = join_for_message(form.tiempo_fecha.data, form.tiempo_horas_minutos.data)
        except ValueError as error:
            flash(str(error), "warning")
            return render_template("audiencias/new_dipe.jinja2", form=form)

        # Validar tipo de audiencia
        tipo_audiencia = safe_string(form.tipo_audiencia.data)
        if tipo_audiencia == "":
            tipo_audiencia = "NO DEFINIDO"

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            return render_template("audiencias/new_dipe.jinja2", form=form)

        # Insertar registro
        audiencia = Audiencia(
            autoridad=autoridad,
            tiempo=tiempo,
            tipo_audiencia=tipo_audiencia,
            expediente=expediente,
            actores=safe_string(form.actores.data),
            demandados=safe_string(form.demandados.data),
            toca=safe_string(form.toca.data),
            expediente_origen=safe_string(form.expediente_origen.data),
            imputados=safe_string(form.imputados.data),
        )
        audiencia.save()

        # Mostrar mensaje de éxito e ir al detalle
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva audiencia en {autoridad.clave} para {tiempo_mensaje}"),
            url=url_for("audiencias.detail", audiencia_id=audiencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Prellenado del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    return render_template("audiencias/new_dipe.jinja2", form=form)


@audiencias.route("/audiencias/nuevo/generica", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_generica():
    """Nueva Audiencia Materias CIVIL FAMILIAR MERCANTIL LETRADO TCYA"""

    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("audiencias.list_active"))
    if autoridad.audiencia_categoria != "CIVIL FAMILIAR MERCANTIL LETRADO TCYA":
        flash("La categoría de audiencia no es CIVIL FAMILIAR MERCANTIL LETRADO TCYA.", "warning")
        return redirect(url_for("audiencias.list_active"))

    # Si viene el formulario
    form = AudienciaGenericaForm()
    if form.validate_on_submit():
        # Definir tiempo con la fecha y horas:minutos
        try:
            tiempo = f"{form.tiempo_fecha.data} {form.tiempo_horas_minutos.data}"
            tiempo = datetime.strptime(tiempo, "%Y-%m-%d %H:%M:%S")
            tiempo_mensaje = join_for_message(form.tiempo_fecha.data, form.tiempo_horas_minutos.data)
        except ValueError as error:
            flash(str(error), "warning")
            return render_template("audiencias/new_generica.jinja2", form=form)

        # Validar tipo de audiencia
        tipo_audiencia = safe_string(form.tipo_audiencia.data)
        if tipo_audiencia == "":
            tipo_audiencia = "NO DEFINIDO"

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            return render_template("audiencias/new_generica.jinja2", form=form)

        # Insertar registro
        audiencia = Audiencia(
            autoridad=autoridad,
            tiempo=tiempo,
            tipo_audiencia=tipo_audiencia,
            expediente=expediente,
            actores=safe_string(form.actores.data),
            demandados=safe_string(form.demandados.data),
        )
        audiencia.save()

        # Mostrar mensaje de éxito e ir al detalle
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva audiencia en {autoridad.clave} para {tiempo_mensaje}"),
            url=url_for("audiencias.detail", audiencia_id=audiencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Prellenado del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    return render_template("audiencias/new_generica.jinja2", form=form)


@audiencias.route("/audiencias/nuevo/mapo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_mapo():
    """Nuevo Audiencias MATERIA ACUSATORIO PENAL ORAL"""

    # Validar Autoridad
    autoridad = current_user.autoridad
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("audiencias.list_active"))
    if autoridad.audiencia_categoria != "MATERIA ACUSATORIO PENAL ORAL":
        flash("La categoria de audiencia no es MATERIA ACUSATORIO PENAL ORAL.", "warning")
        return redirect(url_for("audiencias.list_active"))
        # Agrega este flash para ver el método de la solicitud

    # Si viene el formulario
    form = AudienciaMapoForm()

    if form.validate_on_submit():
        # Definir tiempo con la fecha y horas:minutos
        try:
            tiempo = f"{form.tiempo_fecha.data}  {form.tiempo_horas_minutos.data}"
            tiempo = datetime.strptime(tiempo, "%Y-%m-%d %H:%M:%S")
            tiempo_mensaje = join_for_message(form.tiempo_fecha.data, form.tiempo_horas_minutos.data)
        except ValueError as error:
            flash(str(error), "warning")
            return render_template("audiencias/new_mapo.jinja2", form=form)

        # Validar tipo de audiencia
        tipo_audiencia = safe_string(form.tipo_audiencia.data)
        if tipo_audiencia == "":
            tipo_audiencia = "NO DEFINIDO"

        # Insertar registro
        audiencia = Audiencia(
            autoridad=autoridad,
            tiempo=tiempo,
            tipo_audiencia=tipo_audiencia,
            sala=safe_string(form.sala.data),
            caracter=safe_string(form.caracter.data),
            causa_penal=safe_string(form.causa_penal.data),
            delitos=safe_string(form.delitos.data),
        )
        audiencia.save()

        # Mostrar mensaje de éxito e ir al detalle
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nueva audiencias en {autoridad.clave} para {tiempo_mensaje}"),
            url=url_for("audiencias.detail", audiencia_id=audiencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Prellenado del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    return render_template("audiencias/new_mapo.jinja2", form=form)


@audiencias.route("/audiencias/nuevo/sape", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new_sape():
    """Nuevo Audiencia SALAS"""
    # Validar autoridad
    autoridad = current_user.autoridad
    if autoridad is None or autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("audiencias.list_active"))
    if autoridad.audiencia_categoria != "SALAS":
        flash("La categoría de audiencia no es SALAS.", "warning")
        return redirect(url_for("audiencias.list_active"))

    form = AudienciaSapeForm()
    if form.validate_on_submit():
        # Definir tiempo con la fecha y horas:minutos
        try:
            tiempo = f"{form.tiempo_fecha.data} {form.tiempo_horas_minutos.data}"
            tiempo = datetime.strptime(tiempo, "%Y-%m-%d %H:%M:%S")
            tiempo_mensaje = join_for_message(form.tiempo_fecha.data, form.tiempo_horas_minutos.data)
        except ValueError as error:
            flash(str(error), "warning")
            return render_template("audiencias/new_sape.jinja2", form=form)

        # Validar tipo de audiencia
        tipo_audiencia = safe_string(form.tipo_audiencia.data)
        if tipo_audiencia == "":
            tipo_audiencia = "NO DEFINIDO"

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            return render_template("audiencias/new_sape.jinja2", form=form)

        audiencia = Audiencia(
            autoridad=autoridad,
            tiempo=tiempo,
            tipo_audiencia=tipo_audiencia,
            expediente=expediente,
            actores=safe_string(form.actores.data),
            demandados=safe_string(form.demandados.data),
            toca=safe_string(form.toca.data),
            expediente_origen=safe_string(form.expediente_origen.data),
            delitos=safe_string(form.delitos.data),
            origen=safe_string(form.origen.data),
        )
        audiencia.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Nuevo Audiencia SALAS {autoridad.clave} para {tiempo_mensaje}"),
            url=url_for("audiencias.detail", audiencia_id=audiencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Prellenado del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    return render_template("audiencias/new_sape.jinja2", form=form)


@audiencias.route("/audiencias/edicion/<int:audiencia_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(audiencia_id):
    """Editar Audiencia"""

    # Validad autoridad
    audiencia = Audiencia.query.get_or_404(audiencia_id)
    autoridad = audiencia.autoridad
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("audiencias.list_active"))

    # Redirigir
    if autoridad.audiencia_categoria == "CIVIL FAMILIAR MERCANTIL LETRADO TCYA":
        return redirect(url_for("audiencias.edit_generica", audiencia_id=audiencia_id))
    if autoridad.audiencia_categoria == "MATERIA ACUSATORIO PENAL ORAL":
        return redirect(url_for("audiencias.edit_mapo", audiencia_id=audiencia_id))
    if autoridad.audiencia_categoria == "DISTRITALES":
        return redirect(url_for("audiencias.edit_dipe", audiencia_id=audiencia_id))
    if autoridad.audiencia_categoria == "SALAS":
        return redirect(url_for("audiencias.edit_sape", audiencia_id=audiencia_id))

    # Mensaje por no reconocer la categoría de audiencias
    flash("El juzgado/autoridad no tiene una categoría de audiencias correcta.", "warning")
    return redirect(url_for("audiencias.list_active"))


@audiencias.route("/audiencias/edicion/generica/<int:audiencia_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit_generica(audiencia_id):
    """Editar Audiencia CIVIL FAMILIAR MERCANTIL LETRADO TCYA"""

    # Validar audiencia
    audiencia = Audiencia.query.get_or_404(audiencia_id)
    if not (current_user.can_admin("AUDIENCIAS") or current_user.autoridad_id == audiencia.autoridad_id):
        flash("No tiene permiso para editar esta audiencia.", "warning")
        return redirect(url_for("edictos.list_active"))

    # Validar autoridad
    autoridad = audiencia.autoridad
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("audiencias.list_active"))
    if autoridad.audiencia_categoria != "CIVIL FAMILIAR MERCANTIL LETRADO TCYA":
        flash("La categoría de audiencia no es CIVIL FAMILIAR MERCANTIL LETRADO TCYA.", "warning")
        return redirect(url_for("audiencias.list_active"))

    # Si viene el formulario
    form = AudienciaGenericaForm()
    if form.validate_on_submit():
        # Definir tiempo con la fecha y horas:minutos
        try:
            tiempo = f"{form.tiempo_fecha.data} {form.tiempo_horas_minutos.data}"
            tiempo = datetime.strptime(tiempo, "%Y-%m-%d %H:%M:%S")
            tiempo_mensaje = join_for_message(form.tiempo_fecha.data, form.tiempo_horas_minutos.data)
        except ValueError as error:
            flash(str(error), "warning")
            return render_template("audiencias/edit_generica.jinja2", form=form, audiencia=audiencia)

        # Validar tipo de audiencia
        tipo_audiencia = safe_string(form.tipo_audiencia.data)
        if tipo_audiencia == "":
            tipo_audiencia = "NO DEFINIDO"

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            return render_template("audiencias/edit_generica.jinja2", form=form, audiencia=audiencia)

        # Actualizar registro
        audiencia.tiempo = tiempo
        audiencia.tipo_audiencia = tipo_audiencia
        audiencia.expediente = expediente
        audiencia.actores = safe_string(form.actores.data)
        audiencia.demandados = safe_string(form.demandados.data)
        audiencia.save()

        # Registrar en bitácora e ir al detalle
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editada la audiencia de {autoridad.clave} para {tiempo_mensaje}"),
            url=url_for("audiencias.detail", audiencia_id=audiencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Descombinar el tiempo en fecha y horas:minutos
    form.tiempo_fecha.data = audiencia.tiempo.date()
    form.tiempo_horas_minutos.data = audiencia.tiempo.time()

    # Prellenado del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.tipo_audiencia.data = audiencia.tipo_audiencia
    form.expediente.data = audiencia.expediente
    form.actores.data = audiencia.actores
    form.demandados.data = audiencia.demandados
    return render_template("audiencias/edit_generica.jinja2", form=form, audiencia=audiencia)


@audiencias.route("/audiencias/edicion/dipe/<int:audiencia_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit_dipe(audiencia_id):
    """Editar Audiencia DISTRITALES"""

    # Validar audiencia
    audiencia = Audiencia.query.get_or_404(audiencia_id)
    if not (current_user.can_admin("AUDIENCIAS") or current_user.autoridad_id == audiencia.autoridad_id):
        flash("No tiene permiso para editar esta audiencia.", "warning")
        return redirect(url_for("edictos.list_active"))

    # Validar autoridad
    autoridad = audiencia.autoridad
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("audiencias.list_active"))
    if autoridad.audiencia_categoria != "DISTRITALES":
        flash("La categoría de audiencia no es DISTRITALES.", "warning")
        return redirect(url_for("audiencias.list_active"))

    # Si viene el formulario
    form = AudienciaDipeForm()
    if form.validate_on_submit():
        # Definir tiempo con la fecha y horas:minutos
        try:
            tiempo = f"{form.tiempo_fecha.data} {form.tiempo_horas_minutos.data}"
            tiempo = datetime.strptime(tiempo, "%Y-%m-%d %H:%M:%S")
            tiempo_mensaje = join_for_message(form.tiempo_fecha.data, form.tiempo_horas_minutos.data)
        except ValueError as error:
            flash(str(error), "warning")
            return render_template("audiencias/edit_dipe.jinja2", form=form, audiencia=audiencia)

        # Validar tipo de audiencia
        tipo_audiencia = safe_string(form.tipo_audiencia.data)
        if tipo_audiencia == "":
            tipo_audiencia = "NO DEFINIDO"

        # Validar expediente
        try:
            expediente = safe_expediente(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            return render_template("audiencias/edit_dipe.jinja2", form=form, audiencia=audiencia)

        # Actualizar registro
        audiencia.tiempo = tiempo
        audiencia.tipo_audiencia = tipo_audiencia
        audiencia.expediente = expediente
        audiencia.actores = safe_string(form.actores.data)
        audiencia.demandados = safe_string(form.demandados.data)
        audiencia.toca = safe_string(form.toca.data)
        audiencia.expediente_origen = safe_string(form.expediente_origen.data)
        audiencia.imputados = safe_string(form.imputados.data)
        audiencia.save()

        # Registrar en bitácora e ir al detalle
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editada la audiencia de {autoridad.clave} para {tiempo_mensaje}"),
            url=url_for("audiencias.detail", audiencia_id=audiencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Descombinar el tiempo en fecha y horas:minutos
    form.tiempo_fecha.data = audiencia.tiempo.date()
    form.tiempo_horas_minutos.data = audiencia.tiempo.time()

    # Prellenado del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.tipo_audiencia.data = audiencia.tipo_audiencia
    form.expediente.data = audiencia.expediente
    form.actores.data = audiencia.actores
    form.demandados.data = audiencia.demandados
    form.toca.data = audiencia.toca
    form.expediente_origen.data = audiencia.expediente_origen
    form.imputados.data = audiencia.imputados
    return render_template("audiencias/edit_dipe.jinja2", form=form, audiencia=audiencia)


@audiencias.route("/audiencias/edicion/mapo/<int:audiencia_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit_mapo(audiencia_id):
    """Editar Audiencia MATERIA ACUSATORIO PENAL ORAL"""

    # Validar audiencia
    audiencia = Audiencia.query.get_or_404(audiencia_id)
    if not (current_user.can_admin("AUDIENCIAS") or current_user.autoridad_id == audiencia.autoridad_id):
        flash("No tiene permiso para editar esta audiencia.", "warning")
        return redirect(url_for("edictos.list_active"))

    # Validar autoridad
    autoridad = audiencia.autoridad
    if autoridad.estatus != "A":
        flash("El juzgado/autoridad no es activa.", "warning")
        return redirect(url_for("audiencias.list_active"))
    if autoridad.audiencia_categoria != "MATERIA ACUSATORIO PENAL ORAL":
        flash("La categoría de audiencia no es MATERIA ACUSATORIO PENAL ORAL.", "warning")
        return redirect(url_for("audiencias.list_active"))

    # Si viene el formulario
    form = AudienciaMapoForm()
    if form.validate_on_submit():
        # Definir tiempo con la fecha y horas:minutos
        try:
            tiempo = f"{form.tiempo_fecha.data} {form.tiempo_horas_minutos.data}"
            tiempo = datetime.strptime(tiempo, "%Y-%m-%d %H:%M:%S")
            tiempo_mensaje = join_for_message(form.tiempo_fecha.data, form.tiempo_horas_minutos.data)
        except ValueError as error:
            flash(str(error), "warning")
            return render_template("audiencias/edit_mapo.jinja2", form=form, audiencia=audiencia)

        # Validar tipo de audiencia
        tipo_audiencia = safe_string(form.tipo_audiencia.data)
        if tipo_audiencia == "":
            tipo_audiencia = "NO DEFINIDO"

        # Actualizar registro
        audiencia.tiempo = tiempo
        audiencia.tipo_audiencia = tipo_audiencia
        audiencia.sala = safe_string(form.sala.data)
        audiencia.caracter = safe_string(form.caracter.data)
        audiencia.causa_penal = safe_string(form.causa_penal.data)
        audiencia.delitos = safe_string(form.delitos.data)
        audiencia.save()

        # Registrar en bitácora e ir al detalle
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editada la audiencia de {autoridad.clave} para {tiempo_mensaje}"),
            url=url_for("audiencias.detail", audiencia_id=audiencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)

    # Descombinar el tiempo en fecha y horas:minutos
    form.tiempo_fecha.data = audiencia.tiempo.date()
    form.tiempo_horas_minutos.data = audiencia.tiempo.time()
    # Prellenado del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.tipo_audiencia.data = audiencia.tipo_audiencia
    form.sala.data = audiencia.sala
    form.caracter.data = audiencia.caracter
    form.causa_penal.data = audiencia.causa_penal
    form.delitos.data = audiencia.delitos
    return render_template("audiencias/edit_mapo.jinja2", form=form, audiencia=audiencia)


@audiencias.route("/audiencias/edicion/sape/<int:audiencia_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit_sape(audiencia_id):
    """Editar Audiencia SALA"""
    audiencia = Audiencia.query.get_or_404(audiencia_id)
    if not (current_user.can_admin("AUDIENCIAS") or current_user.autoridad_id == audiencia.autoridad_id):
        flash("No tiene permiso para editar esta audiencia.", "warning")
        return redirect(url_for("edictos.list_active"))

    # Validad autoridad
    autoridad = audiencia.autoridad
    if autoridad.estatus != "A":
        flash("El juzgados/autoridad no es activa.", "warning")
        return redirect(url_for("audiencias.list_active"))
    if autoridad.audiencia_categoria != "SALAS":
        flash("La categoria de audiencia no es SALAS.", "warning")
        return redirect(url_for("audiencias.list_active"))

    # Si viene del formulario
    form = AudienciaSapeForm()
    if form.validate_on_submit():
        # Definir tiempo con la fecha y horas:minutos
        try:
            tiempo = f"{form.tiempo_fecha.data} {form.tiempo_horas_minutos.data}"
            tiempo = datetime.strptime(tiempo, "%Y-%m-%d %H:%M:%S")
            tiempo_mensaje = join_for_message(form.tiempo_fecha.data, form.tiempo_horas_minutos.data)
        except ValueError as error:
            flash(str(error), "warning")
            return redirect(url_for("audiencias/edit_sape.jinja2", form=form, audiencia=audiencia))

        # validar tipo de audiencia
        tipo_audiencia = safe_string(form.tipo_audiencia.data)
        if tipo_audiencia == "":
            tipo_audiencia = "NO DEFINIDO"

        # Validar expediente
        try:
            expediente = safe_string(form.expediente.data)
        except (IndexError, ValueError):
            flash("El expediente es incorrecto.", "warning")
            return render_template(url_for("audiencias.edit_sape.jinja2", form=form, audiencia=audiencia))
        # Actualizar registro
        audiencia.tiempo = tiempo
        audiencia.tipo_audiencia = tipo_audiencia
        audiencia.expediente = expediente
        audiencia.actores = safe_string(form.actores.data)
        audiencia.demandado = safe_string(form.demandados.data)
        audiencia.toca = safe_string(form.toca.data)
        audiencia.expediente_origen = safe_string(form.expediente_origen.data)
        audiencia.delitos = safe_string(form.delitos.data)
        audiencia.origen = safe_string(form.origen.data)
        audiencia.save()

        # Registar en bitácora e ir al detalle
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Editado Audiencia {autoridad.clave} para {tiempo_mensaje}"),
            url=url_for("audiencias.detail", audiencia_id=audiencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Descombinar el tiempo en fecha y horas:minutos
    form.tiempo_fecha.data = audiencia.tiempo.date()
    form.tiempo_horas_minutos.data = audiencia.tiempo.time()

    # Prellenado del formulario
    form.distrito.data = autoridad.distrito.nombre
    form.autoridad.data = autoridad.descripcion
    form.tipo_audiencia.data = audiencia.tipo_audiencia
    form.expediente.data = audiencia.expediente
    form.actores.data = audiencia.actores
    form.demandados.data = audiencia.demandados
    form.toca.data = audiencia.toca
    form.expediente_origen.data = audiencia.expediente_origen
    form.delitos.data = audiencia.delitos
    form.origen.data = audiencia.origen
    return render_template("audiencias/edit_sape.jinja2", form=form, audiencia=audiencia)


@audiencias.route("/audiencias/eliminar/<int:audiencia_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(audiencia_id):
    """Eliminar Audiencia"""
    audiencia = Audiencia.query.get_or_404(audiencia_id)
    if audiencia.estatus == "A":
        audiencia.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminada la audiencia {audiencia.id}"),
            url=url_for("audiencias.detail", audiencia_id=audiencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("audiencias.detail", audiencia_id=audiencia.id))


@audiencias.route("/audiencias/recuperar/<int:audiencia_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(audiencia_id):
    """Recuperar Audiencia"""
    audiencia = Audiencia.query.get_or_404(audiencia_id)
    if audiencia.estatus == "B":
        audiencia.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Audiencia {audiencia.id}"),
            url=url_for("audiencias.detail", audiencia_id=audiencia.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("audiencias.detail", audiencia_id=audiencia.id))
