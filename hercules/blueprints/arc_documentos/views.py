"""
Archivo - Documentos, vistas
"""

import json
import os
import requests
from flask import Blueprint, flash, redirect, render_template, request, url_for, current_app
from flask_login import current_user, login_required
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import or_

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message, safe_expediente, extract_expediente_num, extract_expediente_anio

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.arc_documentos.models import ArcDocumento
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.arc_documentos_bitacoras.models import ArcDocumentoBitacora
from hercules.blueprints.arc_documentos_tipos.models import ArcDocumentoTipo
from hercules.blueprints.arc_juzgados_extintos.models import ArcJuzgadoExtinto
from hercules.blueprints.arc_solicitudes.models import ArcSolicitud


from hercules.blueprints.arc_documentos.forms import (
    ArcDocumentoNewArchivoForm,
    ArcDocumentoNewSolicitanteForm,
    ArcDocumentoNewNoUbicacionForm,
    ArcDocumentoEditArchivoForm,
    ArcDocumentoEditSolicitanteForm,
    ArcDocumentoEditNoUbicacionForm,
)

from hercules.blueprints.arc_archivos.views import (
    ROL_JEFE_REMESA_ADMINISTRADOR,
    ROL_JEFE_REMESA,
    ROL_ARCHIVISTA,
    ROL_SOLICITANTE,
    ROL_LEVANTAMENTISTA,
)

MODULO = "ARC DOCUMENTOS"
DATAWAREHOUSE_ANIO_SAJI = 2025

arc_documentos = Blueprint("arc_documentos", __name__, template_folder="templates")


@arc_documentos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@arc_documentos.route("/arc_documentos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Documentos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ArcDocumento.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter(ArcDocumento.estatus == request.form["estatus"])
    else:
        consulta = consulta.filter(ArcDocumento.estatus == "A")
    if "expediente" in request.form:
        if request.form["expediente"].isnumeric():
            consulta = consulta.filter(ArcDocumento.expediente.contains(request.form["expediente"]))
        else:
            consulta = consulta.filter_by(expediente=safe_expediente(request.form["expediente"]))
    if "juicio" in request.form:
        juicio = safe_string(request.form["juicio"], save_enie=True)
        consulta = consulta.filter(ArcDocumento.juicio.contains(juicio))
    if "partes" in request.form:
        consulta = consulta.filter(
            or_(
                ArcDocumento.actor.contains(safe_string(request.form["partes"], save_enie=True)),
                ArcDocumento.demandado.contains(safe_string(request.form["partes"], save_enie=True)),
            )
        )
    if "tipo" in request.form:
        consulta = consulta.filter_by(arc_documento_tipo_id=int(request.form["tipo"]))
    if "ubicacion" in request.form:
        consulta = consulta.filter_by(ubicacion=request.form["ubicacion"])
    if "juzgado_id" in request.form:
        consulta = consulta.filter_by(autoridad_id=int(request.form["juzgado_id"]))
    if "juzgado_extinto_id" in request.form:
        consulta = consulta.filter_by(arc_juzgado_origen_id=int(request.form["juzgado_extinto_id"]))
    if "juzgado_extinto_clave" in request.form:
        consulta = consulta.filter(ArcDocumento.arc_juzgados_origen_claves.contains(request.form["juzgado_extinto_clave"]))
    # Luego filtrar por columnas de otras tablas
    if "distrito_id" in request.form:
        distrito_id = int(request.form["distrito_id"])
        consulta = consulta.join(Autoridad)
        consulta = consulta.filter(Autoridad.distrito_id == distrito_id)
    if "sede" in request.form:
        consulta = consulta.join(Autoridad)
        consulta = consulta.filter(Autoridad.sede == request.form["sede"])
    # Definir un set con los campos
    set_campos = {"expediente", "juicio", "partes", "tipo", "ubicacion", "juzgado_extinto_id", "distrito_id", "sede"}
    # Si se filtra por cualquiera de los campos mencionado, el orden es por número de expediente
    if set_campos.intersection(request.form):
        registros = (
            consulta.order_by(ArcDocumento.anio)
            .order_by(ArcDocumento.expediente_numero)
            .offset(start)
            .limit(rows_per_page)
            .all()
        )
    # De lo contrario, se ordena por creación.
    else:
        registros = consulta.order_by(ArcDocumento.creado.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        data.append(
            {
                "expediente": {
                    "expediente": resultado.expediente,
                    "url": url_for("arc_documentos.detail", documento_id=resultado.id),
                },
                "juzgado": {
                    "clave": resultado.autoridad.clave,
                    "nombre": resultado.autoridad.descripcion_corta,
                    "url": (
                        url_for("autoridades.detail", autoridad_id=resultado.autoridad.id)
                        if current_user.can_view("AUTORIDADES")
                        else ""
                    ),
                },
                "juzgado_y_origen": {
                    "clave_actual": resultado.autoridad.clave,
                    "nombre_actual": resultado.autoridad.descripcion_corta,
                    "url_actual": (
                        url_for("autoridades.detail", autoridad_id=resultado.autoridad.id)
                        if current_user.can_view("AUTORIDADES")
                        else ""
                    ),
                    "origenes": resultado.arc_juzgados_origen_claves if resultado.arc_juzgados_origen_claves != None else "",
                },
                "anio": resultado.anio,
                "tipo": resultado.arc_documento_tipo.nombre,
                "fojas": resultado.fojas,
                "actor": resultado.actor,
                "juicio": resultado.juicio,
                "demandado": resultado.demandado,
                "ubicacion": resultado.ubicacion,
                "partes": {
                    "actor": resultado.actor,
                    "demandado": resultado.demandado,
                },
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@arc_documentos.route("/arc_documentos")
def list_active():
    """Listado de Documentos activos"""

    # Consultar los roles del usuario
    current_user_roles = current_user.get_roles()

    if current_user.can_admin(MODULO) or ROL_JEFE_REMESA_ADMINISTRADOR in current_user_roles:
        return render_template(
            "arc_documentos/list_admin.jinja2",
            filtros=json.dumps({"estatus": "A"}),
            titulo="Expedientes",
            estatus="A",
            ubicaciones=ArcDocumento.UBICACIONES,
        )

    if (
        ROL_JEFE_REMESA in current_user_roles
        or ROL_ARCHIVISTA in current_user_roles
        or ROL_LEVANTAMENTISTA in current_user_roles
    ):
        return render_template(
            "arc_documentos/list_admin.jinja2",
            filtros=json.dumps({"estatus": "A", "sede": current_user.autoridad.sede}),
            titulo="Expedientes",
            estatus="A",
            ubicaciones=ArcDocumento.UBICACIONES,
        )

    return render_template(
        "arc_documentos/list.jinja2",
        filtros=json.dumps({"estatus": "A", "juzgado_id": current_user.autoridad.id}),
        titulo=f"Expedientes del {current_user.autoridad.descripcion_corta}",
        estatus="A",
        ubicaciones=ArcDocumento.UBICACIONES,
    )


@arc_documentos.route("/arc_documentos/<int:documento_id>")
def detail(documento_id):
    """Detalle de un Documento"""
    documento = ArcDocumento.query.get_or_404(documento_id)

    # mostrar secciones según el ROL
    mostrar_secciones = {}
    current_user_roles = current_user.get_roles()

    if current_user.can_admin(MODULO):
        mostrar_secciones["boton_eliminar"] = True

    if current_user.can_edit(MODULO):
        mostrar_secciones["boton_editar"] = True

    if (
        current_user.can_admin(MODULO)
        or ROL_JEFE_REMESA in current_user_roles
        or ROL_JEFE_REMESA_ADMINISTRADOR in current_user_roles
        or ROL_SOLICITANTE in current_user_roles
    ):
        mostrar_secciones["boton_editar"] = True
        if current_user.can_insert(MODULO) and documento.ubicacion == "ARCHIVO":
            documento_en_proceso = (
                ArcSolicitud.query.filter_by(arc_documento=documento)
                .filter_by(esta_archivado=False)
                .filter_by(estatus="A")
                .first()
            )
            if not documento_en_proceso:
                mostrar_secciones["boton_solicitar"] = True
        return render_template(
            "arc_documentos/detail.jinja2",
            documento=documento,
            acciones=ArcDocumentoBitacora.ACCIONES,
            mostrar_secciones=mostrar_secciones,
        )

    if ROL_LEVANTAMENTISTA in current_user_roles:
        mostrar_secciones["boton_editar"] = True
        return render_template(
            "arc_documentos/detail_simple.jinja2",
            documento=documento,
            mostrar_secciones=mostrar_secciones,
        )

    return render_template(
        "arc_documentos/detail_simple.jinja2",
        documento=documento,
        acciones=ArcDocumentoBitacora.ACCIONES,
        mostrar_secciones=mostrar_secciones,
    )


@arc_documentos.route("/arc_documentos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Documento"""
    mostrar_secciones = {}
    current_user_roles = current_user.get_roles()
    if ROL_ARCHIVISTA in current_user_roles and ROL_LEVANTAMENTISTA in current_user_roles:
        form = ArcDocumentoNewNoUbicacionForm()
        mostrar_secciones["select_juzgado"] = True
    elif (
        ROL_JEFE_REMESA in current_user_roles
        or current_user.can_admin(MODULO)
        or ROL_LEVANTAMENTISTA in current_user_roles
        or ROL_JEFE_REMESA_ADMINISTRADOR in current_user_roles
    ):
        form = ArcDocumentoNewArchivoForm()
        mostrar_secciones["select_juzgado"] = True
    else:
        form = ArcDocumentoNewSolicitanteForm()
    # Recepción del Formulario
    if form.validate_on_submit():
        # Validar que la clave no se repita
        expediente_numero = 0
        expediente_anio = 0
        try:
            expediente = safe_expediente(form.expediente.data)
            expediente_numero = extract_expediente_num(expediente)
            expediente_anio = extract_expediente_anio(expediente)
        except ValueError:
            expediente = None
        if isinstance(form, ArcDocumentoNewArchivoForm):
            juzgado_id = int(form.juzgado_id.data)
            ubicacion = safe_string(form.ubicacion.data)
        elif isinstance(form, ArcDocumentoNewNoUbicacionForm):
            juzgado_id = int(form.juzgado_id.data)
            ubicacion = "ARCHIVO"
        else:
            juzgado_id = current_user.autoridad.id
            ubicacion = "JUZGADO"
        try:
            anio = int(form.anio.data)
        except ValueError:
            anio = 0
        juzgado = Autoridad.query.filter_by(id=juzgado_id).first()
        tipo_documento = ArcDocumentoTipo.query.get(form.tipo.data)
        if juzgado is None:
            flash("La instancia seleccionada NO existe", "warning")
        elif tipo_documento is None:
            flash("Este tipo de documento no sé conoce")
        elif (
            ArcDocumento.query.filter_by(expediente=expediente)
            .filter_by(autoridad_id=juzgado_id)
            .filter_by(arc_documento_tipo=tipo_documento)
            .filter_by(arc_juzgados_origen_claves=form.juzgados_origen.data)
            .filter_by(estatus="A")
            .first()
        ):
            flash(
                "El número de expediente ya está en uso para la INSTANCIA con ese mismo TIPO y misma INSTANCIA DE ORIGEN. Debe de ser único.",
                "warning",
            )
        elif anio < 1900 or anio > date.today().year:
            flash(f"El Año debe ser una fecha entre 1900 y el año actual {date.today().year}", "warning")
        elif anio != expediente_anio:
            flash("El año ingresado y el año indicado en el número de expediente no coinciden.", "warning")
        elif expediente is None:
            flash("El número de expediente no es válido. El formato esperado es (número/año) (999/2023)", "warning")
        # Sólo aceptar juzgados de su SEDE
        elif ROL_JEFE_REMESA_ADMINISTRADOR not in current_user_roles and juzgado.sede != current_user.autoridad.sede:
            flash(
                f"No puede utilizar la instancia '{juzgado.descripcion_corta} - {juzgado.sede}' que se encuentra fuera de su SEDE '{current_user.autoridad.sede}'",
                "warning",
            )
        else:
            documento = ArcDocumento(
                autoridad_id=juzgado_id,
                expediente=expediente,
                anio=anio,
                expediente_numero=int(expediente_numero),
                actor=safe_string(form.actor.data, save_enie=True),
                demandado=safe_string(form.demandado.data, save_enie=True),
                juicio=safe_string(form.juicio.data, save_enie=True),
                tipo_juzgado=safe_string(form.tipo_juzgado.data),
                arc_juzgados_origen_claves=form.juzgados_origen.data,
                arc_documento_tipo_id=int(form.tipo.data),
                fojas=int(form.fojas.data),
                notas=safe_message(form.notas.data, default_output_str=None),
                ubicacion=ubicacion,
            )
            documento.save()
            documento_bitacora = ArcDocumentoBitacora(
                arc_documento_id=documento.id,
                usuario=current_user,
                fojas=int(form.fojas.data),
                accion="ALTA",
            )
            documento_bitacora.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Alta de Documento {documento.id}"),
                url=url_for("arc_documentos.detail", documento_id=documento.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # listado de instancias de origen
    listado_instancias = ArcJuzgadoExtinto.query.filter_by(estatus="A").order_by(ArcJuzgadoExtinto.clave).all()
    # Bloquear campos según el ROL
    if isinstance(form, ArcDocumentoNewArchivoForm):
        form.ubicacion.data = "ARCHIVO"
    elif isinstance(form, ArcDocumentoNewNoUbicacionForm):
        form.ubicacion_readonly.data = "ARCHIVO"
    else:
        form.juzgado_readonly.data = f"{current_user.autoridad.clave} : {current_user.autoridad.descripcion_corta}"
        form.ubicacion_readonly.data = "JUZGADO"
    return render_template(
        "arc_documentos/new.jinja2", form=form, mostrar_secciones=mostrar_secciones, instancias=listado_instancias
    )


@arc_documentos.route("/arc_documentos/edicion/<int:arc_documento_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(arc_documento_id):
    """Editar Documento"""
    documento = ArcDocumento.query.get_or_404(arc_documento_id)
    current_user_roles = current_user.get_roles()
    if ROL_ARCHIVISTA in current_user_roles and ROL_LEVANTAMENTISTA in current_user_roles:
        form = ArcDocumentoEditNoUbicacionForm()
    elif (
        ROL_JEFE_REMESA in current_user_roles
        or current_user.can_admin(MODULO)
        or ROL_LEVANTAMENTISTA in current_user_roles
        or ROL_JEFE_REMESA_ADMINISTRADOR in current_user_roles
    ):
        form = ArcDocumentoEditArchivoForm()
    else:
        form = ArcDocumentoEditSolicitanteForm()

    # Recepción del Formulario
    if form.validate_on_submit():
        # Validar que la clave no se repita
        fojas = int(form.fojas.data)
        expediente_numero = 0
        expediente_anio = 0
        try:
            expediente = safe_expediente(form.expediente.data)
            expediente_numero = extract_expediente_num(expediente)
            expediente_anio = extract_expediente_anio(expediente)
        except ValueError:
            expediente = None
        if isinstance(form, ArcDocumentoEditArchivoForm):
            juzgado_id = int(form.juzgado_id.data)
            ubicacion = safe_string(form.ubicacion.data)
        elif isinstance(form, ArcDocumentoEditNoUbicacionForm):
            juzgado_id = int(form.juzgado_id.data)
            ubicacion = documento.ubicacion
        else:
            juzgado_id = current_user.autoridad.id
            ubicacion = documento.ubicacion
        try:
            anio = int(form.anio.data)
        except ValueError:
            anio = 0
        motivo = safe_message(form.observaciones.data, max_len=256)
        juzgado = Autoridad.query.filter_by(id=juzgado_id).first()
        tipo_documento = ArcDocumentoTipo.query.get(form.tipo.data)
        if juzgado is None:
            flash("La instancia seleccionada NO existe", "warning")
        elif tipo_documento is None:
            flash("Este tipo de documento no sé conoce")
        # Verificar que solo haya un expediente por Juzgado y por mismo Tipo.
        elif (
            ArcDocumento.query.filter_by(expediente=expediente)
            .filter_by(autoridad_id=juzgado_id)
            .filter_by(arc_documento_tipo=tipo_documento)
            .filter_by(arc_juzgados_origen_claves=form.juzgados_origen.data)
            .filter(ArcDocumento.id != arc_documento_id)
            .filter_by(estatus="A")
            .first()
        ):
            flash(
                "El número de expediente ya está en uso para la INSTANCIA con ese mismo TIPO y misma INSTANCIA DE ORIGEN. Debe de ser único.",
                "warning",
            )
        elif anio != expediente_anio:
            flash("El año ingresado y el año indicado en el número de expediente no coinciden.", "warning")
        elif anio < 1900 or anio > date.today().year:
            flash(f"El Año debe ser una fecha entre 1900 y el año actual {date.today().year}", "warning")
        elif expediente is None:
            flash("El número de expediente no es válido. Utilice el formato '999/2023-XX'", "warning")
        # Sólo aceptar juzgados de su SEDE
        elif (
            ROL_JEFE_REMESA_ADMINISTRADOR not in current_user_roles
            and not current_user.can_admin(MODULO)
            and juzgado.sede != current_user.autoridad.sede
        ):
            flash(
                f"No puede utilizar la instancia '{juzgado.descripcion_corta} - {juzgado.sede}' que se encuentra fuera de su SEDE '{current_user.autoridad.sede}'",
                "warning",
            )
        else:
            documento.autoridad_id = juzgado_id
            documento.expediente = safe_expediente(expediente)
            documento.anio = int(anio)
            documento.expediente_numero = int(expediente_numero)
            documento.actor = safe_string(form.actor.data, save_enie=True)
            documento.demandado = safe_string(form.demandado.data, save_enie=True)
            documento.juicio = safe_string(form.juicio.data, save_enie=True)
            documento.tipo_juzgado = safe_string(form.tipo_juzgado.data)
            documento.arc_juzgados_origen_claves = form.juzgados_origen.data
            documento.arc_documento_tipo_id = int(form.tipo.data)
            documento.fojas = fojas
            documento.notas = safe_message(form.notas.data, default_output_str=None)
            documento.ubicacion = ubicacion
            documento_bitacora = ArcDocumentoBitacora(
                arc_documento_id=documento.id,
                usuario=current_user,
                fojas=fojas,
                observaciones=motivo,
                accion="EDICION DOC",
            )
            documento_bitacora.save()
            documento.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Edición de Documento {documento.id}"),
                url=url_for("arc_documentos.detail", documento_id=documento.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.expediente.data = documento.expediente
    form.anio.data = documento.anio
    form.actor.data = documento.actor
    form.demandado.data = documento.demandado
    form.juicio.data = documento.juicio
    form.tipo_juzgado.data = documento.tipo_juzgado
    form.tipo.data = documento.arc_documento_tipo
    form.fojas.data = documento.fojas
    form.notas.data = documento.notas
    listado_instancias = ArcJuzgadoExtinto.query.filter_by(estatus="A").order_by(ArcJuzgadoExtinto.clave).all()
    if isinstance(form, ArcDocumentoEditArchivoForm):
        form.juzgado_id.data = documento.autoridad_id
        form.ubicacion.data = documento.ubicacion
    elif isinstance(form, ArcDocumentoEditNoUbicacionForm):
        form.juzgado_id.data = documento.autoridad_id
        form.ubicacion_readonly.data = documento.ubicacion
    else:
        form.juzgado_readonly.data = f"{current_user.autoridad.clave} : {current_user.autoridad.descripcion_corta}"
        form.ubicacion_readonly.data = documento.ubicacion
    return render_template("arc_documentos/edit.jinja2", form=form, documento=documento, instancias=listado_instancias)


@arc_documentos.route("/arc_documentos/buscar", methods=["GET", "POST"])
def search():
    """Buscar Documento dentro de Expediente Virtual API"""
    num_expediente = ""
    mostrar_secciones = {}
    current_user_roles = current_user.get_roles()
    if (
        ROL_JEFE_REMESA in current_user_roles
        or current_user.can_admin(MODULO)
        or ROL_LEVANTAMENTISTA in current_user_roles
        or ROL_JEFE_REMESA_ADMINISTRADOR in current_user_roles
    ):
        form = ArcDocumentoNewArchivoForm()
        mostrar_secciones["select_juzgado"] = True
    else:
        form = ArcDocumentoNewSolicitanteForm()
    # Proceso de búsqueda
    if "num_expediente" in request.form:
        num_expediente = request.form["num_expediente"]
        EXPEDIENTE_VIRTUAL_API_URL = current_app.config["EXPEDIENTE_VIRTUAL_API_URL"]
        if EXPEDIENTE_VIRTUAL_API_URL == "":
            flash("No se declaro la variable de entorno EXPEDIENTE_VIRTUAL_API_URL", "warning")
            return redirect(url_for("arc_documentos.new"))
        EXPEDIENTE_VIRTUAL_API_KEY = current_app.config["EXPEDIENTE_VIRTUAL_API_KEY"]
        if EXPEDIENTE_VIRTUAL_API_KEY == "":
            flash("No se declaro la variable de entorno EXPEDIENTE_VIRTUAL_API_KEY", "warning")
            return redirect(url_for("arc_documentos.new"))
        num_expediente = safe_expediente(num_expediente)
        if num_expediente == "":
            flash("Número de Expediente NO válido", "warning")
            return redirect(url_for("arc_documentos.new"))
        # Determinamos el id del juzgado en base a su autoridad asignada o juzgado seleccionado
        autoridad_id = current_user.autoridad.id
        if (
            ROL_JEFE_REMESA in current_user_roles
            or current_user.can_admin(MODULO)
            or ROL_LEVANTAMENTISTA in current_user_roles
            or ROL_JEFE_REMESA_ADMINISTRADOR in current_user_roles
        ):
            if "juzgadoInput_buscar" not in request.form:
                flash("Necesita indicar un Juzgado en el formulario de búsqueda ", "warning")
                autoridad_id = 0
            else:
                autoridad_id = int(request.form["juzgadoInput_buscar"])
                mostrar_secciones["juzgado_id"] = autoridad_id
        if autoridad_id > 0:
            autoridad = Autoridad.query.get_or_404(autoridad_id)
            # Si la autoridad tienen id en datawarehouse_saji buscar cuando sea mayor a DATAWAREHOUSE_ANIO_SAJI
            juzgado_id = autoridad.datawarehouse_id
            if autoridad.datawarehouse_id_saji is not None:
                anio = extract_expediente_anio(num_expediente)
                if anio >= DATAWAREHOUSE_ANIO_SAJI:
                    juzgado_id = autoridad.datawarehouse_id_saji
            if juzgado_id:
                # Armado del cuerpo de petición para la API
                request_body = {
                    "idJuzgado": juzgado_id,
                    "idOrigen": 0,
                    "numeroExpediente": num_expediente,
                }
                # Hace el llamado a la API
                respuesta_api = {}
                try:
                    respuesta = requests.post(
                        EXPEDIENTE_VIRTUAL_API_URL,
                        headers={"X-Api-Key": EXPEDIENTE_VIRTUAL_API_KEY},
                        json=request_body,
                        timeout=32,
                    )
                    respuesta.raise_for_status()
                    respuesta_api = respuesta.json()
                except requests.exceptions.ConnectionError as err:
                    flash(f"Error en conexión con el API. {err}. {request_body}", "danger")
                except requests.exceptions.Timeout as err:
                    flash(f"Error de tiempo. {err}", "danger")
                except requests.exceptions.HTTPError as err:
                    flash(f"Error HTTP. {err}", "danger")
                except requests.exceptions.RequestException as err:
                    flash(f"Error desconocido. {err}", "danger")

                encontrado_paij = False
                if "success" in respuesta_api:
                    if respuesta_api["success"] is True:
                        flash("Registro encontrado en Expediente Virtual", "success")
                        form.expediente.data = num_expediente
                        form.anio.data = extract_expediente_anio(num_expediente)
                        form.juicio.data = respuesta_api["sintesis"]
                        form.actor.data = respuesta_api["actorPromovente"]
                        form.demandado.data = respuesta_api["demandado"]
                        form.tipo.data = "EXPEDIENTE"
                        encontrado_paij = True
                        if (
                            ROL_JEFE_REMESA in current_user_roles
                            or current_user.can_admin(MODULO)
                            or ROL_LEVANTAMENTISTA in current_user_roles
                            or ROL_JEFE_REMESA_ADMINISTRADOR in current_user_roles
                        ):
                            form.juzgado_id.data = autoridad_id
                            mostrar_secciones["juzgado_nombre"] = autoridad.nombre
                    else:
                        flash("Registro NO encontrado en PAIJ", "warning")
                else:
                    flash("Respuesta no esperada por parte del API de DataWareHouse", "danger")
            else:
                flash("Este juzgado no tiene acceso al Buscador. Asigne un valor datawarehouse_id", "warning")
        else:
            flash("No tiene una autoridad asignada compatible con el campo datawarehouse_id", "warning")
    # Bloquear campos según el ROL
    if ROL_SOLICITANTE in current_user_roles:
        form.juzgado_readonly.data = f"{current_user.autoridad.clave} : {current_user.autoridad.descripcion_corta}"
        form.ubicacion_readonly.data = "JUZGADO"
    elif ROL_JEFE_REMESA in current_user_roles or ROL_JEFE_REMESA_ADMINISTRADOR in current_user_roles:
        mostrar_secciones["select_juzgado"] = True
    elif ROL_LEVANTAMENTISTA in current_user_roles:
        form.ubicacion.data = "ARCHIVO"
    else:
        if isinstance(form, ArcDocumentoNewSolicitanteForm):
            form.juzgado_readonly.data = f"{current_user.autoridad.clave} : {current_user.autoridad.descripcion_corta}"
            form.ubicacion_readonly.data = "JUZGADO"
    return render_template(
        "arc_documentos/new.jinja2", form=form, num_expediente=num_expediente, mostrar_secciones=mostrar_secciones
    )


@arc_documentos.route("/arc_documentos/eliminar/<int:arc_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def delete(arc_documento_id):
    """Eliminar Expediente"""
    arc_documento = ArcDocumento.query.get_or_404(arc_documento_id)
    if arc_documento.estatus == "A":
        arc_documento.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Expediente {arc_documento.id}"),
            url=url_for("arc_documentos.detail", documento_id=arc_documento.id),
        )
        bitacora.save()
        # Añadir acción a la bitácora de Solicitudes
        ArcDocumentoBitacora(
            arc_documento=arc_documento,
            usuario=current_user,
            accion="ELIMINADO",
        ).save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("arc_documentos.detail", documento_id=arc_documento.id))


@arc_documentos.route("/arc_documentos/recuperar/<int:arc_documento_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def recover(arc_documento_id):
    """Eliminar Expediente"""
    arc_documento = ArcDocumento.query.get_or_404(arc_documento_id)
    if arc_documento.estatus == "B":
        arc_documento.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado el Expediente {arc_documento.id}"),
            url=url_for("arc_documentos.detail", documento_id=arc_documento.id),
        )
        bitacora.save()
        # Añadir acción a la bitácora de Solicitudes
        ArcDocumentoBitacora(
            arc_documento=arc_documento,
            usuario=current_user,
            accion="RECUPERADO",
        ).save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("arc_documentos.detail", documento_id=arc_documento.id))
