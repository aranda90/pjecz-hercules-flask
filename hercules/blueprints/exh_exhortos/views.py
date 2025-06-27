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
    ExhExhortoEditForm,
    ExhExhortoNewForm,
    ExhExhortoProcessForm,
    ExhExhortoRefuseForm,
    ExhExhortoTransferForm,
)
from hercules.blueprints.exh_areas.models import ExhArea
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.exh_tipos_diligencias.models import ExhTipoDiligencia
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.municipios.models import Municipio
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.pwgen import generar_identificador
from lib.safe_string import safe_expediente, safe_message, safe_string
from lib.time_to_text import dia_mes_ano

MODULO = "EXH EXHORTOS"
exh_exhortos = Blueprint("exh_exhortos", __name__, template_folder="templates")

AUTORIDAD_CLAVE_POR_DEFECTO = "ND"
EXH_AREA_CLAVE_POR_DEFECTO = "ND"
EXH_TIPO_DILIGENCIA_CLAVE_POR_DEFECTO = "OTR"  # OTRO va a tomar el campo tipo_diligenciacion_nombre


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
    if "exhorto_origen_id" in request.form:
        exhorto_origen_id = safe_string(request.form["exhorto_origen_id"], max_len=64, do_unidecode=True, to_uppercase=False)
        if exhorto_origen_id:
            consulta = consulta.filter(ExhExhorto.exhorto_origen_id.contains(exhorto_origen_id))
    if "numero_expediente_origen" in request.form:
        try:
            numero_expediente_origen = safe_expediente(request.form["numero_expediente_origen"])
            consulta = consulta.filter(ExhExhorto.numero_expediente_origen == numero_expediente_origen)
        except ValueError:
            pass
    # Ordenar y paginar
    registros = consulta.order_by(ExhExhorto.id.desc()).offset(start).limit(rows_per_page).all()
    total = consulta.count()
    # Elaborar datos para DataTable
    data = []
    for resultado in registros:
        # El municipio_destino_id NO es una clave foránea, por lo que debe de consultarse de manera independiente
        municipio_destino = Municipio.query.filter_by(id=resultado.municipio_destino_id).first()
        # Agregar a la lista
        data.append(
            {
                "detalle": {
                    "exhorto_origen_id": resultado.exhorto_origen_id,
                    "url": url_for("exh_exhortos.detail", exh_exhorto_id=resultado.id),
                },
                "estado_origen": resultado.municipio_origen.estado.nombre,
                "estado_destino": municipio_destino.estado.nombre,
                "numero_expediente_origen": resultado.numero_expediente_origen,
                "remitente": resultado.remitente,
                "estado": resultado.estado,
                "creado": resultado.creado.strftime("%Y-%m-%d %H:%M:%S"),
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
    # El municipio_destino_id NO es una clave foránea, por lo que debe de consultarse de manera independiente
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto.municipio_destino_id).first()
    # Entregar
    return render_template(
        "exh_exhortos/detail.jinja2",
        exh_exhorto=exh_exhorto,
        municipio_destino=municipio_destino,
    )


@exh_exhortos.route("/exh_exhortos/nuevo", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def new():
    """Nuevo Exhorto"""
    # Consultar Autoridad por defecto
    autoridad_por_defecto = Autoridad.query.filter_by(clave=AUTORIDAD_CLAVE_POR_DEFECTO).first()
    if autoridad_por_defecto is None:
        flash(f"No hay registro de Autoridad con clave {AUTORIDAD_CLAVE_POR_DEFECTO}", "warning")
        return redirect(url_for("exh_exhortos.list_active"))
    # Consultar ExhArea por defecto
    exh_area_por_defecto = ExhArea.query.filter_by(clave=EXH_AREA_CLAVE_POR_DEFECTO).first()
    if exh_area_por_defecto is None:
        flash(f"No hay registro de ExhArea con clave {EXH_AREA_CLAVE_POR_DEFECTO}", "warning")
        return redirect(url_for("exh_exhortos.list_active"))
    # Consultar ExhTipoDiligencia por defecto
    exh_tipo_diligencia_por_defecto = ExhTipoDiligencia.query.filter_by(clave=EXH_TIPO_DILIGENCIA_CLAVE_POR_DEFECTO).first()
    if exh_tipo_diligencia_por_defecto is None:
        flash(f"No hay registro de ExhTipoDiligencia con clave {EXH_TIPO_DILIGENCIA_CLAVE_POR_DEFECTO}", "warning")
        return redirect(url_for("exh_exhortos.list_active"))
    # Recibir el formulario
    form = ExhExhortoNewForm()
    if form.validate_on_submit():
        es_valido = True
        # Por defecto el juzgado de origen es la autoridad por defecto
        juzgado_origen = autoridad_por_defecto
        juzgado_origen_id = autoridad_por_defecto.clave
        juzgado_origen_nombre = autoridad_por_defecto.descripcion
        if form.juzgado_origen.data:
            juzgado_origen = Autoridad.query.get(form.juzgado_origen.data)
            juzgado_origen_id = juzgado_origen.clave
            juzgado_origen_nombre = juzgado_origen.descripcion
        # Por defecto el tipo de diligenciación toma el campo tipo_diligenciacion_nombre
        exh_tipo_diligencia = exh_tipo_diligencia_por_defecto
        tipo_diligencia_id = EXH_TIPO_DILIGENCIA_CLAVE_POR_DEFECTO  # Note que se conserva la clave
        tipo_diligenciacion_nombre = safe_string(form.tipo_diligenciacion_nombre.data, save_enie=True)
        if form.tipo_diligencia.data:
            exh_tipo_diligencia = ExhTipoDiligencia.query.get(form.tipo_diligencia.data)
            if exh_tipo_diligencia.clave != EXH_TIPO_DILIGENCIA_CLAVE_POR_DEFECTO:
                tipo_diligencia_id = exh_tipo_diligencia.clave  # Note que se conserva la clave
                tipo_diligenciacion_nombre = exh_tipo_diligencia.descripcion  # Se usa la descripcion en vez del campo
        # Validar el municipio de destino
        municipio_destino = Municipio.query.get(form.municipio_destino.data)
        if municipio_destino is None:
            flash("El municipio de destino no es válido", "warning")
            es_valido = False
        estado_destino = municipio_destino.estado
        # Validar la materia
        materia_clave = form.materia.data  # Este campo es la clave de la materia
        materia_nombre = ""
        if materia_clave is None:
            flash(f"No hay materias para el estado de destino {estado_destino.nombre}", "warning")
            es_valido = False
        else:
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
        # Validar el número de expediente
        try:
            numero_expediente_origen = safe_expediente(form.numero_expediente_origen.data)
        except ValueError:
            flash("El número de expediente no es válido", "warning")
            es_valido = False
        # Validar el número de oficio
        try:
            numero_oficio_origen = safe_expediente(form.numero_oficio_origen.data)
        except ValueError:
            flash("El número de oficio no es válido", "warning")
            es_valido = False
        # Si es valido, guardar
        if es_valido:
            exh_exhorto = ExhExhorto(
                autoridad_id=juzgado_origen.id,
                exh_area_id=exh_area_por_defecto.id,
                exh_tipo_diligencia_id=exh_tipo_diligencia.id,
                municipio_origen_id=form.municipio_origen.data,
                municipio_destino_id=form.municipio_destino.data,
                exhorto_origen_id=form.exhorto_origen_id.data,
                materia_clave=materia_clave,
                materia_nombre=materia_nombre,
                juzgado_origen_id=juzgado_origen_id,
                juzgado_origen_nombre=juzgado_origen_nombre,
                numero_expediente_origen=numero_expediente_origen,
                numero_oficio_origen=numero_oficio_origen,
                tipo_juicio_asunto_delitos=safe_string(form.tipo_juicio_asunto_delitos.data, save_enie=True),
                juez_exhortante=safe_string(form.juez_exhortante.data, save_enie=True),
                fojas=form.fojas.data,
                dias_responder=form.dias_responder.data,
                tipo_diligencia_id=tipo_diligencia_id,
                tipo_diligenciacion_nombre=tipo_diligenciacion_nombre,
                fecha_origen=form.fecha_origen.data,
                observaciones=safe_string(form.observaciones.data, save_enie=True, max_len=1024),
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
    # Consultar el estado y municipio de origen
    # Tomando las claves INEGI de las variables de entorno ESTADO_CLAVE y MUNICIPIO_CLAVE
    estado_origen_clave = current_app.config["ESTADO_CLAVE"]
    estado_origen = Estado.query.filter_by(clave=estado_origen_clave).first()
    municipio_origen = (
        Municipio.query.filter_by(estado_id=estado_origen.id).filter_by(clave=current_app.config["MUNICIPIO_CLAVE"]).first()
    )
    # Definir valores por defecto del formulario
    form.exhorto_origen_id.data = generar_identificador()  # Read only
    form.estado_origen.data = estado_origen.nombre  # Read only
    form.fecha_origen.data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Read only
    form.folio_seguimiento.data = ""  # Read only
    form.juzgado_origen.data = autoridad_por_defecto.id  # Select2
    # Entregar el formulario
    return render_template(
        "exh_exhortos/new.jinja2",
        form=form,
        estado_origen_clave=estado_origen_clave,
        municipio_origen_id=municipio_origen.id,
        exh_tipo_diligencia_por_defecto=exh_tipo_diligencia_por_defecto,
    )


@exh_exhortos.route("/exh_exhortos/edicion/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.MODIFICAR)
def edit(exh_exhorto_id):
    """Editar Exhorto"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    # Consultar Autoridad por defecto
    autoridad_por_defecto = Autoridad.query.filter_by(clave=AUTORIDAD_CLAVE_POR_DEFECTO).first()
    if autoridad_por_defecto is None:
        flash(f"No hay registro de Autoridad con clave {AUTORIDAD_CLAVE_POR_DEFECTO}", "warning")
        return redirect(url_for("exh_exhortos.list_active"))
    # Consultar ExhTipoDiligencia por defecto
    exh_tipo_diligencia_por_defecto = ExhTipoDiligencia.query.filter_by(clave=EXH_TIPO_DILIGENCIA_CLAVE_POR_DEFECTO).first()
    if exh_tipo_diligencia_por_defecto is None:
        flash(f"No hay registro de ExhTipoDiligencia con clave {EXH_TIPO_DILIGENCIA_CLAVE_POR_DEFECTO}", "warning")
        return redirect(url_for("exh_exhortos.list_active"))
    # Recibir el formulario
    form = ExhExhortoEditForm()
    if form.validate_on_submit():
        es_valido = True
        # Por defecto el juzgado de origen es la autoridad por defecto
        juzgado_origen = autoridad_por_defecto
        juzgado_origen_id = autoridad_por_defecto.clave
        juzgado_origen_nombre = autoridad_por_defecto.descripcion
        if form.juzgado_origen.data:
            juzgado_origen = Autoridad.query.get(form.juzgado_origen.data)
            juzgado_origen_id = juzgado_origen.clave
            juzgado_origen_nombre = juzgado_origen.descripcion
        # Por defecto el tipo de diligenciación toma el campo tipo_diligenciacion_nombre
        exh_tipo_diligencia = exh_tipo_diligencia_por_defecto
        tipo_diligencia_id = EXH_TIPO_DILIGENCIA_CLAVE_POR_DEFECTO  # Note que se conserva la clave
        tipo_diligenciacion_nombre = safe_string(form.tipo_diligenciacion_nombre.data, save_enie=True)  # Se usa el campo
        if form.tipo_diligencia.data:
            exh_tipo_diligencia = ExhTipoDiligencia.query.get(form.tipo_diligencia.data)
            tipo_diligencia_id = exh_tipo_diligencia.clave  # Note que se conserva la clave
            if exh_tipo_diligencia.clave != EXH_TIPO_DILIGENCIA_CLAVE_POR_DEFECTO:  # No es OTROS
                tipo_diligenciacion_nombre = exh_tipo_diligencia.descripcion  # Se usa la descripcion de la tabla
        # Validar el municipio de destino
        municipio_destino = Municipio.query.get(form.municipio_destino.data)
        if municipio_destino is None:
            flash("El municipio de destino no es válido", "warning")
            es_valido = False
        estado_destino = municipio_destino.estado
        # Validar la materia
        materia_clave = form.materia.data  # Este campo es la clave de la materia
        materia_nombre = ""
        if materia_clave is None:
            flash(f"No hay materias para el estado de destino {estado_destino.nombre}", "warning")
            es_valido = False
        else:
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
        # Validar el número de expediente
        try:
            numero_expediente_origen = safe_expediente(form.numero_expediente_origen.data)
        except ValueError:
            flash("El número de expediente no es válido", "warning")
            es_valido = False
        # Validar el número de oficio
        try:
            numero_oficio_origen = safe_expediente(form.numero_oficio_origen.data)
        except ValueError:
            flash("El número de oficio no es válido", "warning")
            es_valido = False
        # Si es valido, actualizar
        if es_valido:
            exh_exhorto.autoridad_id = juzgado_origen.id
            exh_exhorto.exh_tipo_diligencia_id = exh_tipo_diligencia.id
            exh_exhorto.municipio_origen_id = form.municipio_origen.data
            exh_exhorto.municipio_destino_id = form.municipio_destino.data
            exh_exhorto.materia_clave = materia_clave
            exh_exhorto.materia_nombre = materia_nombre
            exh_exhorto.juzgado_origen_id = juzgado_origen_id
            exh_exhorto.juzgado_origen_nombre = juzgado_origen_nombre
            exh_exhorto.numero_expediente_origen = numero_expediente_origen
            exh_exhorto.numero_oficio_origen = numero_oficio_origen
            exh_exhorto.tipo_juicio_asunto_delitos = safe_string(form.tipo_juicio_asunto_delitos.data)
            exh_exhorto.juez_exhortante = safe_string(form.juez_exhortante.data, save_enie=True)
            exh_exhorto.fojas = form.fojas.data
            exh_exhorto.dias_responder = form.dias_responder.data
            exh_exhorto.tipo_diligencia_id = tipo_diligencia_id
            exh_exhorto.tipo_diligenciacion_nombre = tipo_diligenciacion_nombre
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
    # Consultar el estado de origen por medio de la clave INEGI en la variable de entorno ESTADO_CLAVE
    estado_origen_clave = current_app.config["ESTADO_CLAVE"]
    estado_origen = Estado.query.filter_by(clave=estado_origen_clave).first()
    # Definir los valores solo lectura en el formulario
    form.exhorto_origen_id.data = exh_exhorto.exhorto_origen_id  # Read only
    form.estado_origen.data = estado_origen.nombre  # Read only
    form.fecha_origen.data = exh_exhorto.fecha_origen  # Read only
    form.folio_seguimiento.data = exh_exhorto.folio_seguimiento  # Read only
    # Definir los valores que se pueden modificar en el formulario
    form.juzgado_origen.data = exh_exhorto.autoridad_id  # Select2
    form.numero_expediente_origen.data = exh_exhorto.numero_expediente_origen
    form.numero_oficio_origen.data = exh_exhorto.numero_oficio_origen
    form.tipo_juicio_asunto_delitos.data = exh_exhorto.tipo_juicio_asunto_delitos
    form.juez_exhortante.data = exh_exhorto.juez_exhortante
    form.fojas.data = exh_exhorto.fojas
    form.dias_responder.data = exh_exhorto.dias_responder
    form.tipo_diligenciacion_nombre.data = exh_exhorto.tipo_diligenciacion_nombre
    form.observaciones.data = exh_exhorto.observaciones
    # Consultar la autoridad por la clave en juzgado_origen_id
    juzgado_origen = Autoridad.query.filter_by(clave=exh_exhorto.juzgado_origen_id).filter_by(estatus="A").first()
    # El municipio_destino_id NO es una clave foránea, por lo que debe de consultarse de manera independiente
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto.municipio_destino_id).first()
    # Entregar el formulario
    return render_template(
        "exh_exhortos/edit.jinja2",
        form=form,
        estado_origen_clave=estado_origen_clave,
        exh_exhorto=exh_exhorto,
        exh_tipo_diligencia_por_defecto=exh_tipo_diligencia_por_defecto,
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
            descripcion=safe_message(f"Eliminado Exhorto ID {exh_exhorto.id}"),
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
            descripcion=safe_message(f"Recuperado Exhorto ID {exh_exhorto.id}"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))


@exh_exhortos.route("/exh_exhortos/consultar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.CREAR)
def launch_task_query(exh_exhorto_id):
    """Lanzar tarea en el fondo para consultar un exhorto al PJ Externo"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar estatus
    if exh_exhorto.estatus != "A":
        flash("El exhorto no está activo", "warning")
        es_valido = False
    # Validar el remitente
    if exh_exhorto.remitente != "EXTERNO":
        flash("No puede se puede consultar porque no tiene remitente EXTERNO", "warning")
        es_valido = False
    # Validar el estado
    if exh_exhorto.estado not in (
        "RECIBIDO",
        "RECIBIDO CON EXITO",
        "RESPONIDOD",
        "TRANSFERIDO",
        "PROCESANDO",
        "CONTESTADO",
        "RECHAZADO",
    ):
        flash(f"No puede se puede consultar porque el estado {exh_exhorto.estado} no lo permite.", "warning")
        es_valido = False
    # Si NO es válido, redirigir al detalle
    if es_valido is False:
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Insertar en la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Se ha CONSULTADO el exhorto {exh_exhorto.exhorto_origen_id}"),
        url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
    )
    bitacora.save()
    # Lanzar tarea en el fondo
    tarea = current_user.launch_task(
        comando="exh_exhortos.tasks.task_consultar_exhorto",
        mensaje="Consultando el exhorto al PJ externo",
        exh_exhorto_id=exh_exhorto_id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@exh_exhortos.route("/exh_exhortos/enviar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.CREAR)
def launch_task_send(exh_exhorto_id):
    """Lanzar tarea en el fondo para envíar exhorto al PJ Externo"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar estatus
    if exh_exhorto.estatus != "A":
        flash("El exhorto no está activo", "warning")
        es_valido = False
    # Validar el remitente
    if exh_exhorto.remitente != "INTERNO":
        flash("No puede se puede enviar porque no tiene remitente INTERNO", "warning")
        es_valido = False
    # Validar el estado
    if exh_exhorto.estado not in ("POR ENVIAR", "RECHAZADO"):
        flash("No se puede enviar porque el estado debe ser POR ENVIAR o RECHAZADO.", "warning")
        es_valido = False
    # Validar que tenga partes
    partes = []
    for parte in exh_exhorto.exh_exhortos_partes:
        if parte.estatus == "A":
            partes.append(parte)
    if len(partes) == 0:
        flash("No se pudo enviar porque debe incluir al menos una parte.", "warning")
        es_valido = False
    # Validar que tenga archivos
    archivos = []
    for archivo in exh_exhorto.exh_exhortos_archivos:
        if archivo.estatus == "A" and archivo.estado != "CANCELADO":
            archivos.append(archivo)
    if len(archivos) == 0:
        flash("No se pudo enviar porque debe incluir al menos un archivo.", "warning")
        es_valido = False
    # Si NO es válido, redirigir al detalle
    if es_valido is False:
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Insertar en la bitácora
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message(f"Se ha ENVIADO el exhorto {exh_exhorto.exhorto_origen_id}"),
        url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
    )
    bitacora.save()
    # Lanzar tarea en el fondo
    tarea = current_user.launch_task(
        comando="exh_exhortos.tasks.task_enviar_exhorto",
        mensaje="Enviando el exhorto al PJ externo",
        exh_exhorto_id=exh_exhorto_id,
    )
    flash("Se ha lanzado la tarea en el fondo. Esta página se va a recargar en 10 segundos...", "info")
    return redirect(url_for("tareas.detail", tarea_id=tarea.id))


@exh_exhortos.route("/exh_exhortos/archivar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_archive(exh_exhorto_id):
    """Cambiar el estado del exhorto a ARCHIVAR"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar estatus
    if exh_exhorto.estatus != "A":
        flash("El exhorto no está activo", "warning")
        es_valido = False
    # Validar el estado del Exhorto
    if exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("Este exhorto ya estaba ARCHIVADO.", "warning")
    # Si NO es válido, redirigir al detalle
    if es_valido is False:
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Cambiar el estado
    exh_exhorto.estado_anterior = exh_exhorto.estado
    exh_exhorto.estado = "ARCHIVADO"
    exh_exhorto.save()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message("Se ha ARCHIVADO el exhorto"),
        url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))


@exh_exhortos.route("/exh_exhortos/cancelar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_cancel(exh_exhorto_id):
    """Cambiar el estado del exhorto a CANCELADO"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar estatus
    if exh_exhorto.estatus != "A":
        flash("El exhorto no está activo", "warning")
        es_valido = False
    # Validar el estado del Exhorto
    if exh_exhorto.estado == "CANCELADO":
        es_valido = False
        flash("Este exhorto ya estaba CANCELADO.", "warning")
    if exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("Este exhorto ya está ARCHIVADO. No puede cambiar su estado.", "warning")
    # Si NO es válido, redirigir al detalle
    if es_valido is False:
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Cambiar el estado
    exh_exhorto.estado_anterior = exh_exhorto.estado
    exh_exhorto.estado = "CANCELADO"
    exh_exhorto.save()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message("Se ha CANCELADO el exhorto"),
        url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))


@exh_exhortos.route("/exh_exhortos/cambiar_a_pendiente/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_pending(exh_exhorto_id):
    """Cambiar el exhorto a PENDIENTE"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar estatus
    if exh_exhorto.estatus != "A":
        flash("El exhorto no está activo", "warning")
        es_valido = False
    # Validar el estado del Exhorto
    if exh_exhorto.estado == "PENDIENTE":
        es_valido = False
        flash("Este exhorto ya estaba PENDIENTE.", "warning")
    if exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("Este exhorto ya está ARCHIVADO. No puede cambiar su estado.", "warning")
    # Si NO es válido, redirigir al detalle
    if es_valido is False:
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Cambiar el estado
    exh_exhorto.estado_anterior = exh_exhorto.estado
    exh_exhorto.estado = "PENDIENTE"
    exh_exhorto.save()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message("Se ha cambiado a PENDIENTE el exhorto"),
        url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))


@exh_exhortos.route("/exh_exhortos/procesar/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def change_to_process(exh_exhorto_id):
    """Procesar un exhorto para cambiar su estado a PROCESANDO"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar estatus
    if exh_exhorto.estatus != "A":
        flash("El exhorto no está activo", "warning")
        es_valido = False
    # Validar el estado del Exhorto
    if exh_exhorto.estado == "PROCESANDO":
        es_valido = False
        flash("Este exhorto ya estaba PROCESANDO.", "warning")
    if exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("Este exhorto ya está ARCHIVADO. No puede cambiar su estado.", "warning")
    # Si NO es válido, redirigir al detalle
    if es_valido is False:
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Recibir el formulario
    form = ExhExhortoProcessForm()
    if form.validate_on_submit():
        exh_exhorto.numero_exhorto = safe_string(form.numero_exhorto.data)
        exh_exhorto.estado_anterior = exh_exhorto.estado
        exh_exhorto.estado = "PROCESANDO"
        exh_exhorto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha cambiado a PROCESANDO el exhorto"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # El municipio_destino_id NO es una clave foránea, por lo que debe de consultarse de manera independiente
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto.municipio_destino_id).first()
    # Cargar los valores guardados en el formulario
    form.numero_exhorto.data = exh_exhorto.numero_exhorto
    # Entregar el formulario
    return render_template(
        "exh_exhortos/process.jinja2",
        form=form,
        exh_exhorto=exh_exhorto,
        municipio_destino=municipio_destino,
    )


@exh_exhortos.route("/exh_exhortos/rechazar/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def change_to_refuse(exh_exhorto_id):
    """Procesar un exhorto para cambiar su estado a RECHAZADO"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar estatus
    if exh_exhorto.estatus != "A":
        flash("El exhorto no está activo", "warning")
        es_valido = False
    # Validar el estado del Exhorto
    if exh_exhorto.estado == "RECHAZADO":
        es_valido = False
        flash("Este exhorto ya estaba RECHAZADO.", "warning")
    if exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("Este exhorto ya está ARCHIVADO. No puede cambiar su estado.", "warning")
    # Si NO es válido, redirigir al detalle
    if es_valido is False:
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Recibir el formulario
    form = ExhExhortoRefuseForm(CombinedMultiDict((request.files, request.form)))
    if form.validate_on_submit():
        exh_exhorto.estado_anterior = exh_exhorto.estado
        exh_exhorto.estado = "RECHAZADO"
        exh_exhorto.respuesta_tipo_diligenciado = 0
        exh_exhorto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha RECHAZADO el exhorto"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # El municipio_destino_id NO es una clave foránea, por lo que debe de consultarse de manera independiente
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto.municipio_destino_id).first()
    # Entregar el formulario
    return render_template(
        "exh_exhortos/refuse.jinja2",
        form=form,
        exh_exhorto=exh_exhorto,
        municipio_destino=municipio_destino,
    )


@exh_exhortos.route("/exh_exhortos/cambiar_a_por_enviar/<int:exh_exhorto_id>")
@permission_required(MODULO, Permiso.CREAR)
def change_to_send(exh_exhorto_id):
    """Cambiar el estado del exhorto a POR ENVIAR"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar estatus
    if exh_exhorto.estatus != "A":
        flash("El exhorto no está activo", "warning")
        es_valido = False
    # Validar el estado del exhorto
    if exh_exhorto.estado == "POR ENVIAR":
        es_valido = False
        flash("Este exhorto ya estaba POR ENVIAR.", "warning")
    if exh_exhorto.estado == "ARCHIVADO":
        es_valido = False
        flash("Este exhorto ya está ARCHIVADO. No puede cambiar su estado.", "warning")
    # Validar que tenga partes
    partes = []
    for parte in exh_exhorto.exh_exhortos_partes:
        if parte.estatus == "A":
            partes.append(parte)
    if len(partes) == 0:
        flash("No se puede cambiar el estado del exhorto a POR ENVIAR. Debe incluir al menos una parte.", "warning")
        es_valido = False
    # Validar que tenga archivos
    archivos = []
    for archivo in exh_exhorto.exh_exhortos_archivos:
        if archivo.estatus == "A" and archivo.estado != "CANCELADO":
            archivos.append(archivo)
    if len(archivos) == 0:
        flash("No se puede cambiar el estado del exhorto a POR ENVIAR. Debe incluir al menos un archivo.", "warning")
        es_valido = False
    # Si NO es válido, redirigir al detalle
    if es_valido is False:
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Cambiar el estado
    exh_exhorto.estado_anterior = exh_exhorto.estado
    exh_exhorto.estado = "POR ENVIAR"
    exh_exhorto.por_enviar_intentos = 0
    exh_exhorto.save()
    bitacora = Bitacora(
        modulo=Modulo.query.filter_by(nombre=MODULO).first(),
        usuario=current_user,
        descripcion=safe_message("Se ha cambiado a POR ENVIAR el exhorto"),
        url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
    )
    bitacora.save()
    flash(bitacora.descripcion, "success")
    return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))


@exh_exhortos.route("/exh_exhortos/transferir/<int:exh_exhorto_id>", methods=["GET", "POST"])
@permission_required(MODULO, Permiso.CREAR)
def change_to_transfer(exh_exhorto_id):
    """Transferir un exhorto a un juzgado"""
    exh_exhorto = ExhExhorto.query.get_or_404(exh_exhorto_id)
    es_valido = True
    # Validar el estado del exhorto
    if exh_exhorto.estado == "TRANSFIRIENDO":
        flash("Este exhorto ya estaba TRANSFIRIENDO.", "warning")
        es_valido = False
    if exh_exhorto.estado == "ARCHIVADO":
        flash("Este exhorto ya está ARCHIVADO. No puede cambiar su estado.", "warning")
        es_valido = False
    # Si NO es válido, redirigir al detalle
    if es_valido is False:
        return redirect(url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id))
    # Recibir el formulario
    form = ExhExhortoTransferForm()
    if form.validate_on_submit():
        exh_exhorto.exh_area_id = form.exh_area.data
        exh_exhorto.autoridad_id = form.autoridad.data
        exh_exhorto.estado_anterior = exh_exhorto.estado
        exh_exhorto.estado = "TRANSFIRIENDO"
        exh_exhorto.save()
        bitacora = Bitacora(
            modulo=Modulo.query.filter_by(nombre=MODULO).first(),
            usuario=current_user,
            descripcion=safe_message("Se ha cambiado a TRANSFIRIENDO el exhorto"),
            url=url_for("exh_exhortos.detail", exh_exhorto_id=exh_exhorto.id),
        )
        bitacora.save()
        flash(bitacora.descripcion, "success")
        return redirect(bitacora.url)
    # Definir los campos del formulario
    form.exh_area.data = exh_exhorto.exh_area.id
    # El municipio_destino_id NO es una clave foránea, por lo que debe de consultarse de manera independiente
    municipio_destino = Municipio.query.filter_by(id=exh_exhorto.municipio_destino_id).first()
    # Entregar el formulario
    return render_template(
        "exh_exhortos/transfer.jinja2",
        form=form,
        exh_exhorto=exh_exhorto,
        municipio_destino=municipio_destino,
    )
