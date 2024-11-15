"""
CLI Exh Exhortos
"""

from datetime import datetime, timedelta
import random
import sys

import click
from faker import Faker
from sqlalchemy import text

from hercules.app import create_app
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_areas.models import ExhArea
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_archivos.models import ExhExhortoArchivo
from hercules.blueprints.exh_exhortos_partes.models import ExhExhortoParte
from hercules.blueprints.exh_exhortos_videos.models import ExhExhortoVideo
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.pwgen import generar_identificador
from lib.safe_string import safe_string

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Exh Exhortos"""


@click.command()
def truncar():
    """Truncar la tabla de exhortos"""
    click.echo("Truncando la tabla de exhortos y sus dependencias")
    database.session.execute(text("TRUNCATE TABLE exh_exhortos RESTART IDENTITY CASCADE;"))
    database.session.commit()
    click.echo("Tabla de exhortos truncada")


@click.command()
@click.argument("estado_origen", type=str)
def demo_ext_02_recibir(estado_origen):
    """Demostrar EXTERNO 02 Recibir datos de exhorto"""
    click.echo("Demostrar EXTERNO 02 Recibir datos de exhorto")

    # Consultar y validar el estado de origen
    estado = Estado.query.filter_by(clave=estado_origen).first()
    if estado is None:
        estado = Estado.query.filter_by(nombre=safe_string(estado_origen)).first()
        if estado is None:
            click.echo(click.style(f"ERROR: No existe el estado {estado_origen}", fg="red"))
            sys.exit(1)

    # Consultar la autoridad con clave ND
    autoridad = Autoridad.query.filter_by(clave="ND").first()

    # Consultar el area con clave ND
    exh_area = ExhArea.query.filter_by(clave="ND").first()

    # Elegir un municipio de origen al azar
    municipios_origenes = Municipio.query.filter_by(estado_id=estado.id).all()
    municipio_origen = random.choice(municipios_origenes)

    # Elegir un municipio de destino de Coahuila de Zaragoza (clave 05) al azar
    municipios_destinos = Municipio.query.select_from(Municipio).join(Estado).filter(Estado.clave == "05").all()
    municipo_destino = random.choice(municipios_destinos)

    # Inicializar el generador de nombres aleatorios
    faker = Faker(locale="es_MX")

    # Insertar ExhExhorto
    exh_exhorto = ExhExhorto()
    exh_exhorto.remitente = "EXTERNO"
    exh_exhorto.autoridad_id = autoridad.id  # Es una clave foránea
    exh_exhorto.exh_area_id = exh_area.id  # Es una clave foránea
    exh_exhorto.materia_clave = "CIV"
    exh_exhorto.materia_nombre = "CIVIL"
    exh_exhorto.municipio_origen_id = municipio_origen.id  # Es una clave foránea
    exh_exhorto.folio_seguimiento = generar_identificador()
    exh_exhorto.exhorto_origen_id = generar_identificador()
    exh_exhorto.municipio_destino_id = municipo_destino.id  # Es una clave foránea
    juzgado_origen_numero = random.randint(1, 9)
    exh_exhorto.juzgado_origen_id = f"J{juzgado_origen_numero}-CIV"
    exh_exhorto.juzgado_origen_nombre = f"JUZGADO {juzgado_origen_numero} CIVIL"
    exh_exhorto.numero_expediente_origen = f"{random.randint(1, 999)}/{datetime.now().year}"
    exh_exhorto.tipo_juicio_asunto_delitos = "DIVORCIO"
    exh_exhorto.juez_exhortante = safe_string(faker.name(), save_enie=True)
    exh_exhorto.fojas = random.randint(1, 100)
    exh_exhorto.dias_responder = 15
    exh_exhorto.tipo_diligenciacion_nombre = "OFICIO"
    exh_exhorto.fecha_origen = datetime.now()
    exh_exhorto.observaciones = "PRUEBA DESDE CLI"
    exh_exhorto.estado = "RECIBIDO"
    exh_exhorto.save()
    click.echo(click.style(f"He insertado el exhorto {exh_exhorto.exhorto_origen_id} del estado {estado.nombre}", fg="green"))

    # Generar parte actor al azar
    genero = faker.random_element(elements=("M", "F"))
    if genero == "F":
        nombre = faker.first_name_female()
    else:
        nombre = faker.first_name_male()
    apellido_paterno = faker.last_name()
    apellido_materno = faker.last_name()
    nombre_completo = f"{nombre} {apellido_paterno} {apellido_materno}"

    # Insertar parte actor (1)
    exh_exhorto_parte_actor = ExhExhortoParte()
    exh_exhorto_parte_actor.exh_exhorto_id = exh_exhorto.id
    exh_exhorto_parte_actor.genero = genero
    exh_exhorto_parte_actor.nombre = safe_string(nombre, save_enie=True)
    exh_exhorto_parte_actor.apellido_paterno = safe_string(apellido_paterno, save_enie=True)
    exh_exhorto_parte_actor.apellido_materno = safe_string(apellido_materno, save_enie=True)
    exh_exhorto_parte_actor.es_persona_moral = False
    exh_exhorto_parte_actor.tipo_parte = 1
    exh_exhorto_parte_actor.tipo_parte_nombre = ""
    exh_exhorto_parte_actor.save()
    click.echo(click.style(f"He insertado la parte actor {nombre_completo}", fg="green"))

    # Generar parte demandado al azar
    genero = faker.random_element(elements=("M", "F"))
    if genero == "F":
        nombre = faker.first_name_female()
    else:
        nombre = faker.first_name_male()
    apellido_paterno = faker.last_name()
    apellido_materno = faker.last_name()
    nombre_completo = f"{nombre} {apellido_paterno} {apellido_materno}"

    # Insertar parte demandado (2)
    exh_exhorto_parte_demandado = ExhExhortoParte()
    exh_exhorto_parte_demandado.exh_exhorto_id = exh_exhorto.id
    exh_exhorto_parte_demandado.genero = genero
    exh_exhorto_parte_demandado.nombre = safe_string(nombre, save_enie=True)
    exh_exhorto_parte_demandado.apellido_paterno = safe_string(apellido_paterno, save_enie=True)
    exh_exhorto_parte_demandado.apellido_materno = safe_string(apellido_materno, save_enie=True)
    exh_exhorto_parte_demandado.es_persona_moral = False
    exh_exhorto_parte_demandado.tipo_parte = 1
    exh_exhorto_parte_demandado.tipo_parte_nombre = ""
    exh_exhorto_parte_demandado.save()
    click.echo(click.style(f"He insertado la parte demandado {nombre_completo}", fg="green"))

    # Insertar archivos
    for numero in range(1, random.randint(1, 4) + 1):
        exh_exhorto_archivo = ExhExhortoArchivo()
        exh_exhorto_archivo.exh_exhorto_id = exh_exhorto.id
        exh_exhorto_archivo.nombre_archivo = f"prueba-{numero}.pdf"
        exh_exhorto_archivo.hash_sha1 = "3a9a09bbb22a6da576b2868c4b861cae6b096050"
        exh_exhorto_archivo.hash_sha256 = "df3d983d24a5002e7dcbff1629e25f45bb3def406682642643efc4c1c8950a77"
        exh_exhorto_archivo.tipo_documento = 1
        exh_exhorto_archivo.es_respuesta = False
        exh_exhorto_archivo.estado = "PENDIENTE"
        exh_exhorto_archivo.url = ""
        exh_exhorto_archivo.tamano = 0
        exh_exhorto_archivo.save()
        click.echo(click.style(f"He insertado el archivo {exh_exhorto_archivo.nombre_archivo}", fg="green"))

    # Mensaje de éxito
    click.echo(click.style(f"Listo el exhorto {exh_exhorto.exhorto_origen_id} con estado {exh_exhorto.estado}", fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_int_02_enviar(exhorto_origen_id):
    """Demostrar INTERNO 02 Enviar datos de exhorto"""
    click.echo("Demostrar INTERNO 02 Enviar datos de exhorto")

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "PENDIENTE" o "POR ENVIAR"
    if exh_exhorto.estado not in ("PENDIENTE", "POR ENVIAR"):
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado PENDIENTE o POR ENVIAR", fg="red"))
        sys.exit(1)

    # Consultar el municipio de destino en el exhorto
    municipio_destino = Municipio.query.get(exh_exhorto.municipio_destino_id)
    estado_destino = municipio_destino.estado

    # Elegir un NUEVO municipio al azar del estado de destino
    municipios_destinos = Municipio.query.filter_by(estado_id=estado_destino.id).all()
    nuevo_municipio_destino = random.choice(municipios_destinos)

    # Actualizar con datos aleatorios que vendrían de la recepción del exhorto
    # exhortoOrigenId
    exh_exhorto.folio_seguimiento = generar_identificador()  # folioSeguimiento
    exh_exhorto.acuse_fecha_hora_recepcion = datetime.now()  # fechaHoraRecepcion
    exh_exhorto.acuse_municipio_area_recibe_id = int(nuevo_municipio_destino.clave)  # municipioAreaRecibeId
    exh_exhorto.acuse_area_recibe_id = ""  # areaRecibeId
    exh_exhorto.acuse_area_recibe_nombre = ""  # areaRecibeNombre
    exh_exhorto.acuse_url_info = f"https://fake.info/acuse/{exh_exhorto.exhorto_origen_id}"  # urlInfo

    # Actualizar el estado del exhorto con el estado "RECIBIDO CON EXITO"
    exh_exhorto.estado = "RECIBIDO CON EXITO"
    exh_exhorto.save()

    # Mensajes sobre los cambios realizados
    click.echo(click.style(f"He actualizado el folio seguimiento a {exh_exhorto.folio_seguimiento}", fg="green"))
    click.echo(click.style(f"He actualizado el municipio que recibe a {nuevo_municipio_destino.nombre}", fg="green"))
    click.echo(click.style(f"He actualizado la url_info a {exh_exhorto.acuse_url_info}", fg="green"))

    # Mensaje de éxito
    click.echo(click.style(f"Listo el exhorto {exh_exhorto.exhorto_origen_id} con estado {exh_exhorto.estado}", fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_ext_05_enviar_respuesta(exhorto_origen_id):
    """Demostrar EXTERNO 07 Enviar respuesta"""
    click.echo("Demostrar EXTERNO 07 Enviar respuesta")

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "PROCESANDO" o "DILIGENCIADO"
    if exh_exhorto.estado not in ("PROCESANDO", "DILIGENCIADO"):
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado PROCESANDO o DILIGENCIADO", fg="red"))
        sys.exit(1)

    # Actualizar con datos aleatorios que saldrían para responder
    # exhortoId
    exh_exhorto.respuesta_origen_id = generar_identificador()  # respuestaOrigenId
    # fechaHora

    # Mensajes sobre los cambios realizados
    click.echo(click.style(f"He actualizado la respuesta_origen_id a {exh_exhorto.respuesta_origen_id}", fg="green"))

    # Actualizar el estado del exhorto con el estado "CONTESTADO"
    exh_exhorto.estado = "CONTESTADO"
    exh_exhorto.save()

    # Mensaje de éxito
    click.echo(click.style(f"Listo el exhorto {exh_exhorto.exhorto_origen_id} con estado {exh_exhorto.estado}", fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_int_05_recibir_respuesta(exhorto_origen_id):
    """Demostrar INTERNO 07 Recibir respuesta"""
    click.echo("Demostrar INTERNO 07 Recibir respuesta")

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "RECIBIDO CON EXITO"
    if exh_exhorto.estado != "RECIBIDO CON EXITO":
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado RECIBIDO CON EXITO", fg="red"))
        sys.exit(1)

    # Elegir un municipio de COAHUILA DE ZARAGOZA al azar para turnar
    municipios = Municipio.query.select_from(Municipio).join(Estado).filter(Estado.clave == "05").all()
    municipio_turnado = random.choice(municipios)

    # Elegir un área al azar para turnar, que no sea con clave "ND"
    exh_areas = ExhArea.query.filter_by(estatus="A").filter(ExhArea.clave != "ND").all()
    exh_area_turnado = random.choice(exh_areas)

    # Actualizar con datos aleatorios que se enviarían en la respuesta
    # exhortoId
    exh_exhorto.respuesta_origen_id = generar_identificador()  # respuestaOrigenId
    exh_exhorto.respuesta_municipio_turnado_id = int(municipio_turnado.clave)  # municipioTurnadoId
    exh_exhorto.respuesta_area_turnado_id = exh_area_turnado.clave  # areaTurnadoId
    exh_exhorto.respuesta_area_turnado_nombre = exh_area_turnado.nombre  # areaTurnadoNombre
    exh_exhorto.respuesta_numero_exhorto = f"{random.randint(1, 999)}/{datetime.now().year}"  # numeroExhorto
    exh_exhorto.respuesta_tipo_diligenciado = 0  # tipoDiligenciado
    exh_exhorto.respuesta_observaciones = "PRUEBA"  # observaciones

    # Insertar los archivos con datos aleatorios que vendrían en la respuesta
    for numero in range(1, random.randint(5, 8) + 1):
        exh_exhorto_archivo = ExhExhortoArchivo()
        exh_exhorto_archivo.exh_exhorto_id = exh_exhorto.id
        exh_exhorto_archivo.nombre_archivo = f"prueba-{numero}.pdf"
        exh_exhorto_archivo.hash_sha1 = "3a9a09bbb22a6da576b2868c4b861cae6b096050"
        exh_exhorto_archivo.hash_sha256 = "df3d983d24a5002e7dcbff1629e25f45bb3def406682642643efc4c1c8950a77"
        exh_exhorto_archivo.tipo_documento = 1
        exh_exhorto_archivo.es_respuesta = True
        exh_exhorto_archivo.estado = "PENDIENTE"
        exh_exhorto_archivo.url = ""
        exh_exhorto_archivo.tamano = 0
        exh_exhorto_archivo.save()
        click.echo(click.style(f"He insertado el archivo {exh_exhorto_archivo.nombre_archivo}", fg="green"))

    # Insertar los videos con datos aleatorios que vendrían en la respuesta
    for numero in range(1, random.randint(1, 4) + 1):
        exh_exhorto_video = ExhExhortoVideo()
        exh_exhorto_video.exh_exhorto_id = exh_exhorto.id
        exh_exhorto_video.titulo = f"PRUEBA {numero}"
        exh_exhorto_video.descripcion = f"DESCRIPCION DEL VIDEO {numero}"
        exh_exhorto_video.fecha = datetime.now() - timedelta(days=-random.randint(1,15))
        exh_exhorto_video.url_acceso = "https://www.youtube.com/watch?v=LDU_Txk06tM"
        exh_exhorto_video.save()
        click.echo(click.style(f"He insertado el video {exh_exhorto_video.titulo}", fg="green"))

    # Actualizar el estado del exhorto con el estado "RESPONDIDO"
    exh_exhorto.estado = "RESPONDIDO"
    exh_exhorto.save()

    # Mensajes sobre los cambios realizados
    click.echo(click.style(f"He actualizado la respuesta_origen_id a {exh_exhorto.respuesta_origen_id}", fg="green"))

    # Mensaje de éxito
    click.echo(click.style(f"Listo el exhorto {exh_exhorto.exhorto_origen_id} con estado {exh_exhorto.estado}", fg="green"))


@click.command()
def demo_ext_06_enviar_actualizacion():
    """Demostrar EXTERNO 06 Enviar actualización"""
    click.echo("Demostrar EXTERNO 06 Enviar actualización")


@click.command()
def demo_int_06_recibir_actualizacion():
    """Demostrar INTERNO 06 Recibir actualización"""
    click.echo("Demostrar INTERNO 06 Recibir actualización")


@click.command()
def demo_ext_07_recibir_promocion():
    """Demostrar EXTERNO 07 Recibir promoción"""
    click.echo("Demostrar EXTERNO 07 Recibir promoción")


@click.command()
def demo_int_07_enviar_promocion():
    """Demostrar INTERNO 07 Enviar promoción"""
    click.echo("Demostrar INTERNO 07 Enviar promoción")


cli.add_command(truncar)
cli.add_command(demo_ext_02_recibir)
cli.add_command(demo_int_02_enviar)
cli.add_command(demo_ext_05_enviar_respuesta)
cli.add_command(demo_int_05_recibir_respuesta)
cli.add_command(demo_ext_06_enviar_actualizacion)
cli.add_command(demo_int_06_recibir_actualizacion)
cli.add_command(demo_ext_07_recibir_promocion)
cli.add_command(demo_int_07_enviar_promocion)
