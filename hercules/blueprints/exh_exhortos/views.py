"""
Exh Exhortos, vistas
"""

import json
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos.forms import (
    ExhExhortoDiligenceForm,
    ExhExhortoEditForm,
    ExhExhortoNewForm,
    ExhExhortoProcessForm,
    ExhExhortoRecibeResponseManuallyForm,
    ExhExhortoRefuseForm,
    ExhExhortoResponseForm,
    ExhExhortoSendManuallyForm,
    ExhExhortoTransferForm,
)
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_archivos.models import ExhExhortoArchivo
from hercules.blueprints.exh_exhortos_partes.models import ExhExhortoParte
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.municipios.models import Municipio
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.pwgen import generar_identificador
from lib.safe_string import safe_clave, safe_expediente, safe_message, safe_string
from lib.time_to_text import dia_mes_ano

MODULO = "EXH EXHORTOS"

exh_exhortos = Blueprint("exh_exhortos", __name__, template_folder="templates")


@exh_exhortos.route("/exh_exhortos/acuses/recepcion/<id_hashed>")
def acuse_reception(id_hashed):
    """Acuse"""
    exh_exhorto = ExhExhorto.query.get_or_404(ExhExhorto.decode_id(id_hashed))
    dia, mes, anio = dia_mes_ano(exh_exhorto.creado)
    return render_template(
        "exh_exhortos/acuse_reception.jinja2",
        exh_exhorto=exh_exhorto,
        dia=dia,
        mes=mes.upper(),
        anio=anio,
    )


@exh_exhortos.route("/exh_exhortos/acuses/respuesta/<id_hashed>")
def acuse_reponse(id_hashed):
    """Acuse"""
    exh_exhorto = ExhExhorto.query.get_or_404(ExhExhorto.decode_id(id_hashed))
    dia, mes, anio = dia_mes_ano(exh_exhorto.creado)
    return render_template(
        "exh_exhortos/acuse_response.jinja2",
        exh_exhorto=exh_exhorto,
        dia=dia,
        mes=mes.upper(),
        anio=anio,
    )


@exh_exhortos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""


@exh_exhortos.route("/exh_exhortos/datatable_json", methods=["GET", "POST"])
def datatable_json():
    """DataTable JSON para listado de Exhortos"""
    # Tomar parámetros de Datatables
    draw, start, rows_per_page = get_datatable_parameters()
    # Consultar
    consulta = ExhExhorto.query
    # Primero filtrar por columnas propias
    if "estatus" in request.form:
        consulta = consulta.filter_by(estatus=request.form["estatus"])
    else:
        consulta = consulta.filter_by(estatus="A")
    if "estado" in request.form:
        consulta = consulta.filter_by(estado=request.form["estado"])
    if "juzgado_origen_clave" in request.form:
        juzgado_origen_clave = safe_clave(request.form["juzgado_origen_clave"])
        if juzgado_origen_clave != "":
            consulta = consulta.filter(ExhExhorto.juzgado_origen_id.contains(juzgado_origen_clave))
    if "num_expediente" in request.form:
        num_expediente = safe_expediente(request.form["num_expediente"])
        if num_expediente != "":
            consulta = consulta.filter(ExhExhorto.numero_expediente_origen.contains(num_expediente))
    # Buscar en otras tablas
    if "estado_origen" in request.form:
        estado_origen = safe_string(request.form["estado_origen"], save_enie=True)
        if estado_origen != "":
            consulta = consulta.join(Municipio).join(Estado)
            consulta = consulta.filter(Estado.nombre.contains(estado_origen))
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhorto.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        municipio_destino = Municipio.query.filter_by(id=resultado.municipio_destino_id).first()
        data.append(
            {
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
                "detalle": {
                    "id": resultado.id,
                    "url": url_for("exh_exhortos.detail", exh_exhorto_id=resultado.id),
                },
                "juzgado_origen": {
                    "clave": resultado.juzgado_origen_id,
                    "nombre": resultado.juzgado_origen_nombre,
                },
                "numero_expediente_origen": resultado.numero_expediente_origen,
                "estado_origen": resultado.municipio_origen.estado.nombre,
                "estado_destino": municipio_destino.estado.nombre,
                "remitente": resultado.remitente,
                "estado": resultado.estado,
            }
        )
    # Entregar JSON
    return output_datatable_json(draw, total, data)


@exh_exhortos.route("/exh_exhortos")
def list_active():
    """Listado de Exhortos activos"""
    return render_template(
        "exh_exhortos/list.jinja2",
        filtros=json.dumps({"estatus": "A"}),
        titulo="Exhortos",
        estatus="A",
        estados=ExhExhorto.ESTADOS,
    )


@exh_exhortos.route("/exh_exhortos/inactivos")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def list_inactive():
    """Listado de Exhortos inactivos"""
    return render_template(
        "exh_exhortos/list.jinja2",
        filtros=json.dumps({"estatus": "B"}),
        titulo="Exhortos inactivos",
        estatus="B",
        estados=ExhExhorto.ESTADOS,
    )


@exh_exhortos.route("/exh_exhortos/<int:exh_exhorto_id>")
def detail(exh_exhorto_id):
    """Detalle de un Exhorto"""
    # Consultar exhorto
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    # Consultar el municipio de origen porque NO es una relacion
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto.municipio_destino_id).first()
    # Comprimir partes
    partes = ExhExhortoParte.query.filter_by(exh_exhorto=exh_exhorto).all()
    # Comprimir archvios
    archivos = ExhExhortoArchivo.query.filter_by(exh_exhorto=exh_exhorto).filter_by(es_respuesta=False).all()
    # Entregar
    return render_template(
        "exh_exhortos/detail.jinja2",
        exh_exhorto=exh_exhorto,
        partes=partes,
        archivos=archivos,
        municipio_destino=municipio_destino,
    )


@exh_exhortos.route("/exh_exhortos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Exhorto"""
    form = ExhExhortoNewForm()
    if form.validate_on_submit():
        es_valido = True
        # Consultar el juzgado de origen
        juzgado_origen = Autoridad.query.get(form.juzgado_origen.data)
        if juzgado_origen is None:
            flash("El juzgado de origen no es válido", "warning")
            es_valido = False
        # Inicilizar las variables para la clave y el nombre de la materia
        materia_clave = form.materia.data
        materia_nombre = ""
        # Consultar el municipio de destino
        municipio_destino = Municipio.query.get(form.municipio_destino.data)
        if municipio_destino is None:
            flash("El municipio de destino no es válido", "warning")
            es_valido = False
        else:
            estado_destino = municipio_destino.estado
            # Consultar en exh_externos al estado de destino
            exh_externo = ExhExterno.query.filter_by(estado_id=estado_destino.id).first()
            if exh_externo is None:
                flash(f"No hay registro en externos para el estado de destino {estado_destino.nombre}", "warning")
                es_valido = False
            else:
                # Validar la clave de la materia y obtener el nombre de la misma
                if exh_externo.materias is None:
                    flash(f"No hay materias en externos para el estado de destino {estado_destino.nombre}", "warning")
                    es_valido = False
                else:
                    materia = next((materia for materia in exh_externo.materias if materia["clave"] == materia_clave), None)
                    if materia is None:
                        flash(f"La clave de materia {materia_clave} no se encuentra en externo {exh_externo.clave}", "warning")
                        es_valido = False
                    materia_nombre = materia["nombre"]
        # Si es valido, guardar
        if es_valido:
            exh_exhorto = ExhExhorto(
                exhorto_origen_id=generar_identificador(),
                municipio_destino_id=form.municipio_destino.data,
                materia_clave=materia_clave,
                materia_nombre=materia_nombre,
                municipio_origen_id=form.municipio_origen.data,
                juzgado_origen_id=safe_string(juzgado_origen.clave),
                juzgado_origen_nombre=safe_string(juzgado_origen.descripcion, save_enie=True),
                numero_expediente_origen=safe_string(form.numero_expediente_origen.data),
                numero_oficio_origen=safe_string(form.numero_oficio_origen.data),
                tipo_juicio_asunto_delitos=safe_string(form.tipo_juicio_asunto_delitos.data),
                juez_exhortante=safe_string(form.juez_exhortante.data, save_enie=True),
                fojas=form.fojas.data,
                dias_responder=form.dias_responder.data,
                tipo_diligenciacion_nombre=safe_string(form.tipo_diligenciacion_nombre.data, save_enie=True),
                fecha_origen=form.fecha_origen.data,
                observaciones=safe_string(form.observaciones.data, save_enie=True, max_len=1024),
                # Datos por defecto
                exh_area_id=1,  # valor: NO DEFINIDO
                autoridad_id=342,  # valor por defecto: ND - NO DEFINIDO
                numero_exhorto="",
                remitente="INTERNO",
                estado="PENDIENTE",
            )
            exh_exhorto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Nuevo Exhorto {exh_exhorto.exhorto_origen_id}"),
                url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    form.exhorto_origen_id.data = "0" * 24  # Read only
    form.estado_origen.data = "COAHUILA DE ZARAGOZA"
    form.estado.data = "PENDIENTE"
    form.fecha_origen.data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Consultar el estado de origen por medio de la clave INEGI en las variables de entorno ESTADO_CLAVE
    estado_origen_id = Estado.query.filter_by(clave=current_app.config["ESTADO_CLAVE"]).first().id
    # Entregar
    return render_template("exh_exhortos/new.jinja2", form=form, estado_origen_id=estado_origen_id)


@exh_exhortos.route("/exh_exhortos/edicion/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_id):
    """Editar Exhorto"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    form = ExhExhortoEditForm()
    if form.validate_on_submit():
        es_valido = True
        # Consultar la autoridad que es el juzgado de origen
        juzgado_origen = Autoridad.query.filter_by(id=form.juzgado_origen.data).filter_by(estatus="A").first()
        if juzgado_origen is None:
            flash("El juzgado de origen no es válido", "warning")
            es_valido = False
        # Inicializar las variables para la clave y el nombre de la materia
        materia_clave = form.materia.data
        materia_nombre = ""
        # Consultar el municipio de destino
        municipio_destino = Municipio.query.get(form.municipio_destino.data)
        if municipio_destino is None:
            flash("El municipio de destino no es válido", "warning")
            es_valido = False
        else:
            estado_destino = municipio_destino.estado
            # Consultar en exh_externos al estado de destino
            exh_externo = ExhExterno.query.filter_by(estado_id=estado_destino.id).first()
            if exh_externo is None:
                flash(f"No hay registro en externos para el estado de destino {estado_destino.nombre}", "warning")
                es_valido = False
            else:
                # Validar la clave de la materia y obtener el nombre de la misma
                if exh_externo.materias is None:
                    flash(f"No hay materias en externos para el estado de destino {estado_destino.nombre}", "warning")
                    es_valido = False
                else:
                    materia = next((materia for materia in exh_externo.materias if materia["clave"] == materia_clave), None)
                    if materia is None:
                        flash(f"La clave de materia {materia_clave} no se encuentra en externo {exh_externo.clave}", "warning")
                        es_valido = False
                    materia_nombre = materia["nombre"]
        # Si es valido, actualizar
        if es_valido:
            exh_exhorto.municipio_destino_id = form.municipio_destino.data
            exh_exhorto.materia_clave = materia_clave
            exh_exhorto.materia_nombre = materia_nombre
            exh_exhorto.municipio_origen_id = form.municipio_origen.data
            exh_exhorto.juzgado_origen_id = safe_string(juzgado_origen.clave)
            exh_exhorto.juzgado_origen_nombre = safe_string(juzgado_origen.descripcion, save_enie=True)
            exh_exhorto.numero_expediente_origen = safe_string(form.numero_expediente_origen.data)
            exh_exhorto.numero_oficio_origen = safe_string(form.numero_oficio_origen.data)
            exh_exhorto.tipo_juicio_asunto_delitos = safe_string(form.tipo_juicio_asunto_delitos.data)
            exh_exhorto.juez_exhortante = safe_string(form.juez_exhortante.data, save_enie=True)
            exh_exhorto.fojas = form.fojas.data
            exh_exhorto.dias_responder = form.dias_responder.data
            exh_exhorto.tipo_diligenciacion_nombre = safe_string(form.tipo_diligenciacion_nombre.data, save_enie=True)
            exh_exhorto.fecha_origen = form.fecha_origen.data
            exh_exhorto.observaciones = safe_string(form.observaciones.data, save_enie=True, max_len=1024)
            exh_exhorto.save()
            bitacora = Bitacora(
                modulo=Modulo.query.filter_by(nombre=MODULO).first(),
                usuario=current_user,
                descripcion=safe_message(f"Editado Exhorto {exh_exhorto.exhorto_origen_id}"),
                url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
            )
            bitacora.save()
            flash(bitacora.descripcion, "success")
            return redirect(bitacora.url)
    # Buscar el juzgado origen en Autoridades
    juzgado_origen = Autoridad.query.filter_by(clave=exh_exhorto.juzgado_origen_id).filter_by(estatus="A").first()
    # Cargar los valores guardados en el formulario
    form.exhorto_origen_id.data = exh_exhorto.exhorto_origen_id
    form.juzgado_origen.data = juzgado_origen.id
    form.numero_expediente_origen.data = exh_exhorto.numero_expediente_origen
    form.numero_oficio_origen.data = exh_exhorto.numero_oficio_origen
    form.tipo_juicio_asunto_delitos.data = exh_exhorto.tipo_juicio_asunto_delitos
    form.juez_exhortante.data = exh_exhorto.juez_exhortante
    form.fojas.data = exh_exhorto.fojas
    form.dias_responder.data = exh_exhorto.dias_responder
    form.tipo_diligenciacion_nombre.data = exh_exhorto.tipo_diligenciacion_nombre
    form.fecha_origen.data = exh_exhorto.fecha_origen
    form.observaciones.data = exh_exhorto.observaciones
    form.folio_seguimiento.data = exh_exhorto.folio_seguimiento
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto.municipio_destino_id).first()
    form.exh_area.data = exh_exhorto.exh_area.nombre
    form.remitente.data = exh_exhorto.remitente
    form.numero_exhorto.data = exh_exhorto.numero_exhorto
    form.estado.data = exh_exhorto.estado  # Read only
    # Entregar
    return render_template(
        "exh_exhortos/edit.jinja2",
        form=form,
        exh_exhorto=exh_exhorto,
        juzgado_origen=juzgado_origen,
        municipio_destino=municipio_destino,
    )


@exh_exhortos.route("/exh_exhortos/eliminar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def delete(exh_exhorto_id):
    """Eliminar Exhorto"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    if exh_exhorto.estatus == "A":
        exh_exhorto.delete()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Eliminado Exhorto {exh_exhorto.exhorto_origen_id}"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))


@exh_exhortos.route("/exh_exhortos/recuperar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.ADMINISTRAR)
def recover(exh_exhorto_id):
    """Recuperar Exhorto"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    if exh_exhorto.estatus == "B":
        exh_exhorto.recover()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Recuperado Exhorto {exh_exhorto.exhorto_origen_id}"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))


@exh_exhortos.route("/exh_exhortos/consultar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def launch_task_query(exh_exhorto_id):
    """Lanzar tarea en el fondo para consultar un exhorto al PJ Externo"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    # Validar el estado del exhorto
    if exh_exhorto.estado not in ["RECIBIDO CON EXITO", "RESPONDIDO"]:
        flash("El estado del exhorto debe ser RECIBIDO CON EXITO o RESPONDIDO.", "warning")
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Lanzar tarea en el fondo
    tarea = current_user.launch_task(
        comando="exh_exhortos.tasks.task_consultar_exhorto",
        mensaje="Consultando el exhorto al PJ externo",
        exh_exhorto_id=exh_exhorto_id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@exh_exhortos.route("/exh_exhortos/responder/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def launch_task_reply(exh_exhorto_id):
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    """Lanzar tarea en el fondo para responder un exhorto al PJ Externo"""
    # Validar el estado del exhorto
    if exh_exhorto.estado not in ["RECIBIDO", "TRANSFERIDO", "PROCESANDO", "DILIGENCIADO"]:
        flash("El estado del exhorto debe ser RECIBIDO, TRANSFERIDO, PROCESANDO o DILIGENCIADO.", "warning")
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Lanzar tarea en el fondo
    tarea = current_user.launch_task(
        comando="exh_exhortos.tasks.task_responder_exhorto",
        mensaje="Respondiendo el exhorto al PJ externo",
        exh_exhorto_id=exh_exhorto_id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@exh_exhortos.route("/exh_exhortos/enviar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def launch_task_send(exh_exhorto_id):
    """Lanzar tarea en el fondo para envíar exhorto al PJ Externo"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    # Validar que tenga partes
    exh_exhorto_partes = ExhExhortoParte.query.filter_by(exh_exhorto_id=exh_exhorto_id).filter_by(estatus="A").first()
    if exh_exhorto_partes is None:
        flash("No se pudo enviar el exhorto. Debe incluir al menos una parte.", "warning")
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Validar que tenga archivos
    exh_exhorto_archivos = ExhExhortoArchivo.query.filter_by(exh_exhorto_id=exh_exhorto_id).filter_by(estatus="A").first()
    if exh_exhorto_archivos is None:
        flash("No se pudo enviar el exhorto. Debe incluir al menos un archivo.", "warning")
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Validar el estado
    if exh_exhorto.estado not in ("PENDIENTE", "POR ENVIAR"):
        flash("El estado del exhorto debe ser PENDIENTE.", "warning")
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Lanzar tarea en el fondo
    tarea = current_user.launch_task(
        comando="exh_exhortos.tasks.task_enviar_exhorto",
        mensaje="Enviando el exhorto al PJ externo",
        exh_exhorto_id=exh_exhorto_id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@exh_exhortos.route("/exh_exhortos/archivar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def change_to_archive(exh_exhorto_id):
    """Regresar el estado del exhorto a ARCHIVAR"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar que el estado del Exhorto sea "INTENTOS AGOTADOS"
    if exh_exhorto.estado not in ("DILIGENCIADO", "RESPONDIDO"):
        es_valido = False
        flash("El estado del exhorto debe ser DILIGENCIADO o RESPONDIDO.", "warning")
    # Hacer el cambio de estado
    if es_valido:
        exh_exhorto.estado = "ARCHIVADO"
        exh_exhorto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Se paso a ARCHIVADO el exhorto {exh_exhorto.exhorto_origen_id}"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))


@exh_exhortos.route("/exh_exhortos/cancelar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def change_to_cancel(exh_exhorto_id):
    """Cancelar Exhorto"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    if exh_exhorto.estado == "PENDIENTE":
        exh_exhorto.estado = "CANCELADO"
        exh_exhorto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Exhorto CANCELADO {exh_exhorto.exhorto_origen_id}"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))


@exh_exhortos.route("/exh_exhortos/deligenciar/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def change_to_diligence(exh_exhorto_id):
    """Diligenciado exhorto por un juzgado"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    form = ExhExhortoDiligenceForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        exh_exhorto.estado = "DILIGENCIADO"
        exh_exhorto.respuesta_tipo_diligenciado = 2
        exh_exhorto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Exhorto Diligenciado {exh_exhorto.exhorto_origen_id}"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Buscar el juzgado origen en Autoridades
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto.municipio_destino_id).first()
    # Entregar
    return render_template(
        "exh_exhortos/diligence.jinja2", form=form, exh_exhorto=exh_exhorto, municipio_destino=municipio_destino
    )


@exh_exhortos.route("/exh_exhortos/regresar_a_pendiente/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def change_to_pending(exh_exhorto_id):
    """Regresar el estado del exhorto a por enviar"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar que el estado del Exhorto sea "RECHAZADO"
    if exh_exhorto.estado != "RECHAZADO":
        es_valido = False
        flash("El estado del exhorto debe ser RECHAZADO.", "warning")
    # Hacer el cambio de estado
    if es_valido:
        exh_exhorto.estado = "PENDIENTE"
        exh_exhorto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"El exhorto se regresó al estado PENDIENTE {exh_exhorto.exhorto_origen_id}"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))


@exh_exhortos.route("/exh_exhortos/procesar/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def change_to_process(exh_exhorto_id):
    """Procesar un exhorto por un juzgado"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    form = ExhExhortoProcessForm()
    if form.validate_on_submit():
        exh_exhorto.numero_exhorto = safe_string(form.numero_exhorto.data)
        exh_exhorto.estado = "PROCESANDO"
        exh_exhorto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Exhorto Procesando {exh_exhorto.exhorto_origen_id}"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Buscar el juzgado origen en Autoridades
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto.municipio_destino_id).first()
    # Cargar los valores guardados en el formulario
    form.numero_exhorto.data = exh_exhorto.numero_exhorto
    # Entregar
    return render_template(
        "exh_exhortos/process.jinja2", form=form, exh_exhorto=exh_exhorto, municipio_destino=municipio_destino
    )


@exh_exhortos.route("/exh_exhortos/rechazar/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def change_to_refuse(exh_exhorto_id):
    """Rechazar un exhorto por un juzgado"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    form = ExhExhortoRefuseForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        exh_exhorto.estado = "RECHAZADO"
        exh_exhorto.respuesta_tipo_diligenciado = 0
        exh_exhorto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Exhorto Rechazado {exh_exhorto.exhorto_origen_id}"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Buscar el juzgado origen en Autoridades
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto.municipio_destino_id).first()
    # Entregar
    return render_template(
        "exh_exhortos/refuse.jinja2", form=form, exh_exhorto=exh_exhorto, municipio_destino=municipio_destino
    )


@exh_exhortos.route("/exh_exhortos/regresar_a_por_enviar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.MODIFICAR)
def change_to_send(exh_exhorto_id):
    """Regresar el estado del exhorto a por enviar"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar que el estado del Exhorto sea "INTENTOS AGOTADOS"
    if exh_exhorto.estado != "INTENTOS AGOTADOS":
        es_valido = False
        flash("El estado del exhorto debe ser INTENTOS AGOTADOS.", "warning")
    # Hacer el cambio de estado
    if es_valido:
        exh_exhorto.estado = "POR ENVIAR"
        exh_exhorto.por_enviar_intentos = 0
        exh_exhorto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Se reiniciaron los intentos de envío del exhorto {exh_exhorto.exhorto_origen_id}"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))


@exh_exhortos.route("/exh_exhortos/transferir/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def change_to_transfer(exh_exhorto_id):
    """Transferir un exhorto a un juzgado"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    form = ExhExhortoTransferForm()
    if form.validate_on_submit():
        exh_exhorto.exh_area_id = form.exh_area.data
        exh_exhorto.autoridad_id = form.autoridad.data
        exh_exhorto.estado = "TRANSFIRIENDO"
        exh_exhorto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message(f"Exhorto Transferido {exh_exhorto.exhorto_origen_id}"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Buscar el juzgado origen en Autoridades
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto.municipio_destino_id).first()
    # Cargar los valores guardados en el formulario
    form.exh_area.data = exh_exhorto.exh_area.id
    # Entregar
    return render_template(
        "exh_exhortos/transfer.jinja2", form=form, exh_exhorto=exh_exhorto, municipio_destino=municipio_destino
    )
