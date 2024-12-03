"""
CLI Exh Exhortos
"""

import random
import string
import sys
from datetime import datetime, timedelta

import click
from faker import Faker
from sqlalchemy import text

from hercules.app import create_app
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_areas.models import ExhArea
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_actualizaciones.models import ExhExhortoActualizacion
from hercules.blueprints.exh_exhortos_archivos.models import ExhExhortoArchivo
from hercules.blueprints.exh_exhortos_partes.models import ExhExhortoParte
from hercules.blueprints.exh_exhortos_promociones.models import ExhExhortoPromocion
from hercules.blueprints.exh_exhortos_promociones_archivos.models import ExhExhortoPromocionArchivo
from hercules.blueprints.exh_exhortos_promociones_promoventes.models import ExhExhortoPromocionPromovente
from hercules.blueprints.exh_exhortos_videos.models import ExhExhortoVideo
from hercules.blueprints.materias.models import Materia
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.pwgen import generar_identificador
from lib.safe_string import safe_string

app = create_app()
app.app_context().push()
database.app = app

ARCHIVO_PRUEBA_PDF = "prueba-1.pdf"
ARCHIVO_PRUEBA_PDF_HASHSHA1 = "3a9a09bbb22a6da576b2868c4b861cae6b096050"
ARCHIVO_PRUEBA_PDF_HASHSHA256 = "df3d983d24a5002e7dcbff1629e25f45bb3def406682642643efc4c1c8950a77"
ESTADO_ORIGEN_ID = 5  # Coahuila de Zaragoza


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
@click.argument("exhorto_origen_id", type=str)
def demo_02_enviar(exhorto_origen_id):
    """Enviar un exhorto PENDIENTE o POR ENVIAR"""
    click.echo("Enviar un exhorto PENDIENTE o POR ENVIAR")

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "PENDIENTE" o "POR ENVIAR"
    if exh_exhorto.estado not in ("PENDIENTE", "POR ENVIAR"):
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado PENDIENTE o POR ENVIAR", fg="red"))
        sys.exit(1)

    # Preparar el listado de partes
    partes = []
    for exh_exhorto_parte in exh_exhorto.exh_exhortos_partes:
        if exh_exhorto_parte.estatus == "A":
            partes.append(
                {
                    "nombre": exh_exhorto_parte.nombre,
                    "apellidoPaterno": exh_exhorto_parte.apellido_paterno,
                    "apellidoMaterno": exh_exhorto_parte.apellido_materno,
                    "genero": exh_exhorto_parte.genero,
                    "esPersonaMoral": exh_exhorto_parte.es_persona_moral,
                    "tipoParte": exh_exhorto_parte.tipo_parte,
                    "tipoParteNombre": exh_exhorto_parte.tipo_parte_nombre,
                }
            )

    # Validar que haya partes
    if len(partes) == 0:
        click.echo(click.style(f"No hay partes en el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Preparar el listado de archivos
    archivos = []
    for exh_exhorto_archivo in exh_exhorto.exh_exhortos_archivos:
        archivo = {
            "nombreArchivo": exh_exhorto_archivo.nombre_archivo,
            "hashSha1": exh_exhorto_archivo.hash_sha1,
            "hashSha256": exh_exhorto_archivo.hash_sha256,
            "tipoDocumento": exh_exhorto_archivo.tipo_documento,
        }
        archivos.append(archivo)

    # Validar que haya archivos
    if len(archivos) == 0:
        click.echo(click.style(f"No hay archivos en el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Consultar el municipio de destino porque municipio_destino_id es el ID de nuestra tabla municipios
    municipio_destino = Municipio.query.get(exh_exhorto.municipio_destino_id)

    # Preparar lo que se va a enviar
    datos = {
        "exhortoOrigenId": exh_exhorto.exhorto_origen_id,
        "municipioDestinoId": int(municipio_destino.clave),
        "materiaClave": exh_exhorto.materia_clave,
        "estadoOrigenId": int(ESTADO_ORIGEN_ID),
        "municipioOrigenId": int(exh_exhorto.municipio_origen.clave),
        "juzgadoOrigenId": exh_exhorto.juzgado_origen_id,
        "juzgadoOrigenNombre": exh_exhorto.juzgado_origen_nombre,
        "numeroExpedienteOrigen": exh_exhorto.numero_expediente_origen,
        "numeroOficioOrigen": exh_exhorto.numero_oficio_origen,
        "tipoJuicioAsuntoDelitos": exh_exhorto.tipo_juicio_asunto_delitos,
        "juezExhortante": exh_exhorto.juez_exhortante,
        "fojas": int(exh_exhorto.fojas),
        "diasResponder": int(exh_exhorto.dias_responder),
        "tipoDiligenciacionNombre": exh_exhorto.tipo_diligenciacion_nombre,
        "fechaOrigen": exh_exhorto.fecha_origen,
        "observaciones": exh_exhorto.observaciones,
    }

    # Mostrar lo que se va a enviar
    click.echo(click.style("Los datos del exhorto a enviar son...", fg="white"))
    click.echo(click.style(f"  exhortoOrigenId:          {datos['exhortoOrigenId']}", fg="green"))
    click.echo(click.style(f"  municipioDestinoId:       {datos['municipioDestinoId']}", fg="green"))
    click.echo(click.style(f"  materiaClave:             {datos['materiaClave']}", fg="green"))
    click.echo(click.style(f"  estadoOrigenId:           {datos['estadoOrigenId']}", fg="green"))
    click.echo(click.style(f"  municipioOrigenId:        {datos['municipioOrigenId']}", fg="green"))
    click.echo(click.style(f"  juzgadoOrigenId:          {datos['juzgadoOrigenId']}", fg="green"))
    click.echo(click.style(f"  juzgadoOrigenNombre:      {datos['juzgadoOrigenNombre']}", fg="green"))
    click.echo(click.style(f"  numeroExpedienteOrigen:   {datos['numeroExpedienteOrigen']}", fg="green"))
    click.echo(click.style(f"  numeroOficioOrigen:       {datos['numeroOficioOrigen']}", fg="green"))
    click.echo(click.style(f"  tipoJuicioAsuntoDelitos:  {datos['tipoJuicioAsuntoDelitos']}", fg="green"))
    click.echo(click.style(f"  juezExhortante:           {datos['juezExhortante']}", fg="green"))
    click.echo(click.style(f"  fojas:                    {datos['fojas']}", fg="green"))
    click.echo(click.style(f"  diasResponder:            {datos['diasResponder']}", fg="green"))
    click.echo(click.style(f"  tipoDiligenciacionNombre: {datos['tipoDiligenciacionNombre']}", fg="green"))
    click.echo(click.style(f"  fechaOrigen:              {datos['fechaOrigen']}", fg="green"))
    click.echo(click.style(f"  observaciones:            {datos['observaciones']}", fg="green"))

    # Mostrar las partes que se van a enviar
    click.echo(click.style("Las partes son...", fg="white"))
    for parte in partes:
        click.echo(click.style("Parte", fg="blue"))
        click.echo(click.style(f"  nombre:           {parte['nombre']}", fg="green"))
        click.echo(click.style(f"  apellidoPaterno:  {parte['apellidoPaterno']}", fg="green"))
        click.echo(click.style(f"  apellidoMaterno:  {parte['apellidoMaterno']}", fg="green"))
        click.echo(click.style(f"  genero:           {parte['genero']}", fg="green"))
        click.echo(click.style(f"  esPersonaMoral:   {parte['esPersonaMoral']}", fg="green"))
        click.echo(click.style(f"  tipoParte:        {parte['tipoParte']}", fg="green"))
        click.echo(click.style(f"  tipoParteNombre:  {parte['tipoParteNombre']}", fg="green"))

    # Mostrar los archivos que se van a enviar
    click.echo(click.style("Los archivos son...", fg="white"))
    for archivo in archivos:
        click.echo(click.style("Archivo", fg="blue"))
        click.echo(click.style(f"  nombreArchivo: {archivo['nombreArchivo']}", fg="green"))
        click.echo(click.style(f"  hashSha1:      {archivo['hashSha1']}", fg="green"))
        click.echo(click.style(f"  hashSha256:    {archivo['hashSha256']}", fg="green"))
        click.echo(click.style(f"  tipoDocumento: {archivo['tipoDocumento']}", fg="green"))

    # Esperar a que se presione ENTER para continuar
    input("Presiona ENTER para DEMOSTRAR que se va a enviar este exhorto...")

    # Elegir OTRO municipio al azar del estado de destino
    municipios_destinos = Municipio.query.filter_by(estado_id=municipio_destino.estado_id).all()
    nuevo_municipio_destino = random.choice(municipios_destinos)

    # Preparar los datos hipotéticos que se van a recibir como acuse
    acuse = {
        "exhortoOrigenId": exh_exhorto.exhorto_origen_id,
        "folioSeguimiento": generar_identificador(),
        "fechaHoraRecepcion": datetime.now(),
        "municipioAreaRecibeId": int(nuevo_municipio_destino.clave),
        "areaRecibeId": "ID-AREA-DEMO",
        "areaRecibeNombre": "NOMBRE DEL AREA QUE RECIBE",
        "urlInfo": f"https://fake.info/acuse/{exh_exhorto.exhorto_origen_id}",
    }

    # Mostrar el acuse recibido
    click.echo(click.style("He simulado que llegan estos datos como acuse...", fg="white"))
    click.echo(click.style(f"  exhortoOrigenId:       {acuse['exhortoOrigenId']}", fg="green"))
    click.echo(click.style(f"  folioSeguimiento:      {acuse['folioSeguimiento']}", fg="green"))
    click.echo(click.style(f"  fechaHoraRecepcion:    {acuse['fechaHoraRecepcion']}", fg="green"))
    click.echo(click.style(f"  municipioAreaRecibeId: {acuse['municipioAreaRecibeId']}", fg="green"))
    click.echo(click.style(f"  areaRecibeId:          {acuse['areaRecibeId']}", fg="green"))
    click.echo(click.style(f"  areaRecibeNombre:      {acuse['areaRecibeNombre']}", fg="green"))
    click.echo(click.style(f"  urlInfo:               {acuse['urlInfo']}", fg="green"))

    # Actualizar el exhorto con los datos del acuse
    click.echo(click.style("Actualizando el exhorto...", fg="yellow"))
    exh_exhorto.folio_seguimiento = acuse["folioSeguimiento"]
    exh_exhorto.acuse_fecha_hora_recepcion = acuse["fechaHoraRecepcion"]
    exh_exhorto.acuse_municipio_area_recibe_id = acuse["municipioAreaRecibeId"]
    exh_exhorto.acuse_area_recibe_id = acuse["areaRecibeId"]
    exh_exhorto.acuse_area_recibe_nombre = acuse["areaRecibeNombre"]
    exh_exhorto.acuse_url_info = acuse["urlInfo"]

    # Actualizar el exhorto con el estado "RECIBIDO CON EXITO"
    exh_exhorto.estado = "RECIBIDO CON EXITO"
    exh_exhorto.save()

    # Mensaje final
    click.echo(click.style(f"Terminó enviar un exhorto {exh_exhorto.exhorto_origen_id}", fg="green"))


@click.command()
@click.argument("estado_origen", type=str)
def demo_02_recibir(estado_origen):
    """Recibir un exhorto"""
    click.echo("Recibir un exhorto")

    # Consultar y validar el estado de origen
    estado = Estado.query.filter_by(clave=estado_origen).first()
    if estado is None:
        estado = Estado.query.filter_by(nombre=safe_string(estado_origen)).first()
        if estado is None:
            click.echo(click.style(f"ERROR: No existe el estado {estado_origen}", fg="red"))
            sys.exit(1)

    # Consultar la autoridad con clave ND
    autoridad_nd = Autoridad.query.filter_by(clave="ND").first()

    # Consultar el area con clave ND
    exh_area_nd = ExhArea.query.filter_by(clave="ND").first()

    # Elegir un municipio del estado de origen al azar
    municipios_origenes = Municipio.query.filter_by(estado_id=estado.id).all()
    municipio_origen = random.choice(municipios_origenes)

    # Elegir un municipio de destino de Coahuila de Zaragoza (clave 05) al azar
    municipios_destinos = Municipio.query.select_from(Municipio).join(Estado).filter(Estado.clave == "05").all()
    municipo_destino = random.choice(municipios_destinos)

    # Inicializar el generador de nombres aleatorios
    faker = Faker(locale="es_MX")

    # Preparar el listado de partes hipotéticas
    partes = []
    for tipo_parte in range(1, 3):
        genero = faker.random_element(elements=("M", "F"))
        partes.append(
            {
                "nombre": faker.first_name_female() if genero == "F" else faker.first_name_male(),
                "apellidoPaterno": faker.last_name(),
                "apellidoMaterno": faker.last_name(),
                "genero": genero,
                "esPersonaMoral": False,
                "tipoParte": tipo_parte,
                "tipoParteNombre": "",
            }
        )

    # Preparar el listado de archivos hipotéticos que se recibirán
    archivos = []
    for numero in range(1, random.randint(1, 2) + 1):
        archivos.append(
            {
                "nombreArchivo": f"prueba-{numero}.pdf",
                "hashSha1": ARCHIVO_PRUEBA_PDF_HASHSHA1,
                "hashSha256": ARCHIVO_PRUEBA_PDF_HASHSHA256,
                "tipoDocumento": random.randint(1, 3),
            }
        )

    # Definir un numero al azar para el juzgado de origen
    juzgado_origen_numero = random.randint(1, 6)

    # Preparar los datos hipotéticos que se van a recibir
    datos = {
        "exhortoOrigenId": generar_identificador(),
        "municipioDestinoId": int(municipo_destino.clave),
        "materiaClave": "CIV",
        "estadoOrigenId": int(estado.clave),
        "municipioOrigenId": int(municipio_origen.clave),
        "juzgadoOrigenId": f"J{juzgado_origen_numero}-CIV",
        "juzgadoOrigenNombre": f"JUZGADO {juzgado_origen_numero} CIVIL",
        "numeroExpedienteOrigen": f"{random.randint(1, 999)}/{datetime.now().year}",
        "numeroOficioOrigen": f"{random.randint(1, 999)}/{datetime.now().year}",
        "tipoJuicioAsuntoDelitos": "DIVORCIO",
        "juezExhortante": safe_string(faker.name(), save_enie=True),
        "fojas": random.randint(1, 100),
        "diasResponder": 15,
        "tipoDiligenciacionNombre": "OFICIO",
        "fechaOrigen": datetime.now(),
        "observaciones": "PRUEBA DE EXHORTO EXTERNO",
    }

    # Mostrar lo que se va a recibir
    click.echo(click.style("Los datos del exhorto que se van a recibir son...", fg="white"))
    click.echo(click.style(f"  exhortoOrigenId:          {datos['exhortoOrigenId']}", fg="green"))
    click.echo(click.style(f"  municipioDestinoId:       {datos['municipioDestinoId']}", fg="green"))
    click.echo(click.style(f"  materiaClave:             {datos['materiaClave']}", fg="green"))
    click.echo(click.style(f"  estadoOrigenId:           {datos['estadoOrigenId']}", fg="green"))
    click.echo(click.style(f"  municipioOrigenId:        {datos['municipioOrigenId']}", fg="green"))
    click.echo(click.style(f"  juzgadoOrigenId:          {datos['juzgadoOrigenId']}", fg="green"))
    click.echo(click.style(f"  juzgadoOrigenNombre:      {datos['juzgadoOrigenNombre']}", fg="green"))
    click.echo(click.style(f"  numeroExpedienteOrigen:   {datos['numeroExpedienteOrigen']}", fg="green"))
    click.echo(click.style(f"  numeroOficioOrigen:       {datos['numeroOficioOrigen']}", fg="green"))
    click.echo(click.style(f"  tipoJuicioAsuntoDelitos:  {datos['tipoJuicioAsuntoDelitos']}", fg="green"))
    click.echo(click.style(f"  juezExhortante:           {datos['juezExhortante']}", fg="green"))
    click.echo(click.style(f"  fojas:                    {datos['fojas']}", fg="green"))
    click.echo(click.style(f"  diasResponder:            {datos['diasResponder']}", fg="green"))
    click.echo(click.style(f"  tipoDiligenciacionNombre: {datos['tipoDiligenciacionNombre']}", fg="green"))
    click.echo(click.style(f"  fechaOrigen:              {datos['fechaOrigen']}", fg="green"))
    click.echo(click.style(f"  observaciones:            {datos['observaciones']}", fg="green"))

    # Mostrar las partes que se van a enviar
    click.echo(click.style("Las partes son...", fg="white"))
    for parte in partes:
        click.echo(click.style("Parte", fg="blue"))
        click.echo(click.style(f"  nombre:           {parte['nombre']}", fg="green"))
        click.echo(click.style(f"  apellidoPaterno:  {parte['apellidoPaterno']}", fg="green"))
        click.echo(click.style(f"  apellidoMaterno:  {parte['apellidoMaterno']}", fg="green"))
        click.echo(click.style(f"  genero:           {parte['genero']}", fg="green"))
        click.echo(click.style(f"  esPersonaMoral:   {parte['esPersonaMoral']}", fg="green"))
        click.echo(click.style(f"  tipoParte:        {parte['tipoParte']}", fg="green"))
        click.echo(click.style(f"  tipoParteNombre:  {parte['tipoParteNombre']}", fg="green"))

    # Mostrar los archivos que se van a enviar
    click.echo(click.style("Los archivos son...", fg="white"))
    for archivo in archivos:
        click.echo(click.style("Archivo", fg="blue"))
        click.echo(click.style(f"  nombreArchivo: {archivo['nombreArchivo']}", fg="green"))
        click.echo(click.style(f"  hashSha1:      {archivo['hashSha1']}", fg="green"))
        click.echo(click.style(f"  hashSha256:    {archivo['hashSha256']}", fg="green"))
        click.echo(click.style(f"  tipoDocumento: {archivo['tipoDocumento']}", fg="green"))

    # Esperar a que se presione ENTER para continuar
    input("Presiona ENTER para DEMOSTRAR que se va a recibir este exhorto...")

    # Consultar la materia
    materia = Materia.query.filter_by(clave=datos["materiaClave"]).first()

    # Insertar ExhExhorto
    exh_exhorto = ExhExhorto()
    exh_exhorto.exhorto_origen_id = datos["exhortoOrigenId"]
    exh_exhorto.municipio_destino_id = municipo_destino.id  # Clave foránea
    exh_exhorto.materia_clave = datos["materiaClave"]
    exh_exhorto.municipio_origen_id = municipio_origen.id  # Clave foránea
    exh_exhorto.juzgado_origen_id = datos["juzgadoOrigenId"]
    exh_exhorto.juzgado_origen_nombre = datos["juzgadoOrigenNombre"]
    exh_exhorto.numero_expediente_origen = datos["numeroExpedienteOrigen"]
    exh_exhorto.numero_oficio_origen = datos["numeroOficioOrigen"]
    exh_exhorto.tipo_juicio_asunto_delitos = datos["tipoJuicioAsuntoDelitos"]
    exh_exhorto.juez_exhortante = datos["juezExhortante"]
    exh_exhorto.fojas = datos["fojas"]
    exh_exhorto.dias_responder = datos["diasResponder"]
    exh_exhorto.tipo_diligenciacion_nombre = datos["tipoDiligenciacionNombre"]
    exh_exhorto.fecha_origen = datos["fechaOrigen"]
    exh_exhorto.observaciones = datos["observaciones"]
    exh_exhorto.folio_seguimiento = generar_identificador()
    exh_exhorto.remitente = "EXTERNO"
    exh_exhorto.materia_nombre = materia.nombre
    exh_exhorto.autoridad_id = autoridad_nd.id  # Clave foránea NO DEFINIDO
    exh_exhorto.exh_area_id = exh_area_nd.id  # Clave foránea NO DEFINIDO
    exh_exhorto.estado = "RECIBIDO"
    exh_exhorto.save()
    click.echo(click.style("Exhorto insertado con estado RECIBIDO", fg="yellow"))
    click.echo(click.style(f"  Folio de seguimiento {exh_exhorto.folio_seguimiento}", fg="green"))

    # Insertar las partes
    for parte in partes:
        exh_exhorto_parte_actor = ExhExhortoParte()
        exh_exhorto_parte_actor.exh_exhorto_id = exh_exhorto.id
        exh_exhorto_parte_actor.genero = parte["genero"]
        exh_exhorto_parte_actor.nombre = safe_string(parte["nombre"], save_enie=True)
        exh_exhorto_parte_actor.apellido_paterno = safe_string(parte["apellidoPaterno"], save_enie=True)
        exh_exhorto_parte_actor.apellido_materno = safe_string(parte["apellidoMaterno"], save_enie=True)
        exh_exhorto_parte_actor.es_persona_moral = parte["esPersonaMoral"]
        exh_exhorto_parte_actor.tipo_parte = parte["tipoParte"]
        exh_exhorto_parte_actor.tipo_parte_nombre = parte["tipoParteNombre"]
        exh_exhorto_parte_actor.save()
        click.echo(click.style(f"Parte insertada {exh_exhorto_parte_actor.nombre}", fg="yellow"))

    # Insertar los archivos
    for archivo in archivos:
        exh_exhorto_archivo = ExhExhortoArchivo()
        exh_exhorto_archivo.exh_exhorto_id = exh_exhorto.id
        exh_exhorto_archivo.nombre_archivo = archivo["nombreArchivo"]
        exh_exhorto_archivo.hash_sha1 = archivo["hashSha1"]
        exh_exhorto_archivo.hash_sha256 = archivo["hashSha256"]
        exh_exhorto_archivo.tipo_documento = archivo["tipoDocumento"]
        exh_exhorto_archivo.es_respuesta = False
        exh_exhorto_archivo.estado = "PENDIENTE"
        exh_exhorto_archivo.url = ""
        exh_exhorto_archivo.tamano = 0
        exh_exhorto_archivo.save()
        click.echo(click.style(f"Archivo insertado {exh_exhorto_archivo.nombre_archivo}", fg="yellow"))

    # Mensaje final
    click.echo(click.style(f"Terminó recibir un exhorto {exh_exhorto.exhorto_origen_id}", fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_05_enviar_respuesta(exhorto_origen_id):
    """Responder un exhorto PROCESANDO o DILIGENCIADO"""
    click.echo("Responder un exhorto PROCESANDO o DILIGENCIADO")

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "PROCESANDO" o "DILIGENCIADO"
    if exh_exhorto.estado not in ("PROCESANDO", "DILIGENCIADO"):
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado PROCESANDO o DILIGENCIADO", fg="red"))
        sys.exit(1)

    # Consultar los archivos de la respuesta
    exh_exhortos_archivos = (
        ExhExhortoArchivo.query.filter_by(exh_exhorto_id=exh_exhorto.id)
        .filter_by(es_respuesta=True)
        .order_by(ExhExhortoArchivo.id)
        .all()
    )

    # Validar que haya archivos para la respuesta
    if len(exh_exhortos_archivos) == 0:
        click.echo(click.style(f"No hay archivos para la respuesta del exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Preparar el listado con los datos de los archivos para la respuesta
    archivos = []
    for exh_exhorto_archivo in exh_exhortos_archivos:
        archivo = {
            "nombreArchivo": exh_exhorto_archivo.nombre_archivo,
            "hashSha1": exh_exhorto_archivo.hash_sha1,
            "hashSha256": exh_exhorto_archivo.hash_sha256,
            "tipoDocumento": exh_exhorto_archivo.tipo_documento,
        }
        archivos.append(archivo)

    # Consultar los videos de la respuesta
    exh_exhortos_videos = ExhExhortoVideo.query.filter_by(exh_exhorto_id=exh_exhorto.id).order_by(ExhExhortoVideo.id).all()

    # Preparar el listado con los videos para la respuesta
    videos = []
    for exh_exhorto_video in exh_exhortos_videos:
        video = {
            "titulo": exh_exhorto_video.titulo,
            "descripcion": exh_exhorto_video.descripcion,
            "fecha": exh_exhorto_video.fecha,
            "urlAcceso": exh_exhorto_video.url_acceso,
        }
        videos.append(video)

    # Definir la respuesta_origen_id
    respuesta_origen_id = generar_identificador()

    # Preparar la respuesta que se va a enviar
    respuesta = {
        "exhortoId": exh_exhorto.exhorto_origen_id,
        "respuestaOrigenId": respuesta_origen_id,
        "municipioTurnadoId": exh_exhorto.respuesta_municipio_turnado_id,
        "areaTurnadoId": exh_exhorto.respuesta_area_turnado_id,
        "areaTurnadoNombre": exh_exhorto.respuesta_area_turnado_nombre,
        "numeroExhorto": exh_exhorto.respuesta_numero_exhorto,
        "tipoDiligenciado": exh_exhorto.respuesta_tipo_diligenciado,
        "observaciones": exh_exhorto.respuesta_observaciones,
    }

    # Mostrar los datos de la respuesta que se va a enviar
    click.echo(click.style("Los datos de la respuesta que se van a enviar...", fg="white"))
    click.echo(click.style(f"  exhortoId:          {respuesta['exhortoId']}", fg="green"))
    click.echo(click.style(f"  respuestaOrigenId:  {respuesta['respuestaOrigenId']}", fg="green"))
    click.echo(click.style(f"  municipioTurnadoId: {respuesta['municipioTurnadoId']}", fg="green"))
    click.echo(click.style(f"  areaTurnadoId:      {respuesta['areaTurnadoId']}", fg="green"))
    click.echo(click.style(f"  areaTurnadoNombre:  {respuesta['areaTurnadoNombre']}", fg="green"))
    click.echo(click.style(f"  numeroExhorto:      {respuesta['numeroExhorto']}", fg="green"))
    click.echo(click.style(f"  tipoDiligenciado:   {respuesta['tipoDiligenciado']}", fg="green"))
    click.echo(click.style(f"  observaciones:      {respuesta['observaciones']}", fg="green"))

    # Mostrar los datos de los archivos de la respuesta que se va a enviar
    click.echo(click.style("Los archivos son...", fg="white"))
    for archivo in archivos:
        click.echo(click.style("Archivo", fg="blue"))
        click.echo(click.style(f"  nombreArchivo: {archivo['nombreArchivo']}", fg="green"))
        click.echo(click.style(f"  hashSha1:      {archivo['hashSha1']}", fg="green"))
        click.echo(click.style(f"  hashSha256:    {archivo['hashSha256']}", fg="green"))
        click.echo(click.style(f"  tipoDocumento: {archivo['tipoDocumento']}", fg="green"))

    # Mostrar los datos de los videos de la respuesta que se va a enviar
    if len(videos) > 0:
        click.echo(click.style("Los los videos son...", fg="white"))
        for video in videos:
            click.echo(click.style("Video", fg="blue"))
            click.echo(click.style(f"  titulo:      {video['titulo']}", fg="green"))
            click.echo(click.style(f"  descripcion: {video['descripcion']}", fg="green"))
            click.echo(click.style(f"  fecha:       {video['fecha']}", fg="green"))
            click.echo(click.style(f"  urlAcceso:   {video['urlAcceso']}", fg="green"))
    else:
        click.echo(click.style("No hay videos en la respuesta.", fg="white"))

    # Esperar a que se presione ENTER para continuar
    input("Presiona ENTER para DEMOSTRAR que se va a enviar la respuesta...")

    # Actualizar el exhorto
    exh_exhorto.respuesta_origen_id = generar_identificador()
    exh_exhorto.respuesta_fecha_hora_recepcion = datetime.now()
    exh_exhorto.estado = "CONTESTADO"
    exh_exhorto.save()

    # Mostrar
    click.echo(click.style("Exhorto actualizado...", fg="yellow"))
    click.echo(click.style(f"  respuesta_origen_id: {exh_exhorto.respuesta_origen_id}", fg="green"))
    click.echo(click.style(f"  respuesta_fecha_hora_recepcion: {exh_exhorto.respuesta_fecha_hora_recepcion}", fg="green"))
    click.echo(click.style(f"  estado: {exh_exhorto.estado}", fg="green"))

    # Mensaje final
    click.echo(click.style(f"Terminó responder el exhorto {exh_exhorto.exhorto_origen_id}", fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_05_recibir_respuesta(exhorto_origen_id):
    """Recibir respuesta de un exhorto RECIBIDO CON EXITO"""
    click.echo("Recibir respuesta de un exhorto RECIBIDO CON EXITO")

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "RECIBIDO CON EXITO"
    if exh_exhorto.estado != "RECIBIDO CON EXITO":
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado RECIBIDO CON EXITO", fg="red"))
        sys.exit(1)

    # Definir el listado con los archivos hipotéticos que se recibirían
    archivos = [
        {
            "nombreArchivo": "oficio.pdf",
            "hashSha1": ARCHIVO_PRUEBA_PDF_HASHSHA1,
            "hashSha256": ARCHIVO_PRUEBA_PDF_HASHSHA256,
            "tipoDocumento": 1,  # 1 = Oficio
        },
        {
            "nombreArchivo": "acuerdo.pdf",
            "hashSha1": ARCHIVO_PRUEBA_PDF_HASHSHA1,
            "hashSha256": ARCHIVO_PRUEBA_PDF_HASHSHA256,
            "tipoDocumento": 2,  # 2 = Acuerdo
        },
        {
            "nombreArchivo": "anexo.pdf",
            "hashSha1": ARCHIVO_PRUEBA_PDF_HASHSHA1,
            "hashSha256": ARCHIVO_PRUEBA_PDF_HASHSHA256,
            "tipoDocumento": 3,  # 3 = Anexo
        },
    ]

    # Definir el listado con los videos hipotéticos que se recibirían en la respuesta
    characters = string.ascii_letters + string.digits
    videos = []
    for numero in range(1, random.randint(1, 2) + 1):
        random_video_id = "".join(random.choice(characters) for _ in range(11))
        videos.append(
            {
                "titulo": f"Video {numero}",
                "descripcion": f"DESCRIPCION DEL VIDEO {numero}",
                "fecha": datetime.now(),
                "urlAcceso": f"https://www.youtube.com/watch?v={random_video_id}",
            }
        )

    # Elegir un municipio del estado de origen al azar para turnar
    municipios = (
        Municipio.query.select_from(Municipio)
        .join(Estado)
        .filter(Municipio.estado_id == exh_exhorto.municipio_origen.estado_id)
        .all()
    )
    municipio_turnado = random.choice(municipios)

    # Elegir un área hipotética para turnar
    area_turnado_id = f"A{random.randint(1, 5)}"
    area_turnado_nombre = f"AREA TURNADO {area_turnado_id}"

    # Preparar la respuesta que se va a recibir
    numero = random.randint(1, 9999)
    respuesta = {
        "exhortoId": exh_exhorto.exhorto_origen_id,
        "respuestaOrigenId": generar_identificador(),
        "municipioTurnadoId": int(municipio_turnado.clave),
        "areaTurnadoId": area_turnado_id,
        "areaTurnadoNombre": area_turnado_nombre,
        "numeroExhorto": f"{numero}/{datetime.now().year}",
        "tipoDiligenciado": random.choice(["", "OFICIO", "PETICION DE PARTE"]),
        "observaciones": "OBSERVACIONES DE ESTA PRUEBA",
        "archivos": archivos,
        "videos": videos,
    }

    # Mostrar la información que se va a recibir
    click.echo(click.style("Los datos de la respuesta que se van a recibir...", fg="white"))
    click.echo(click.style(f"  exhortoId:          {respuesta['exhortoId']}", fg="green"))
    click.echo(click.style(f"  respuestaOrigenId:  {respuesta['respuestaOrigenId']}", fg="green"))
    click.echo(click.style(f"  municipioTurnadoId: {respuesta['municipioTurnadoId']}", fg="green"))
    click.echo(click.style(f"  areaTurnadoId:      {respuesta['areaTurnadoId']}", fg="green"))
    click.echo(click.style(f"  areaTurnadoNombre:  {respuesta['areaTurnadoNombre']}", fg="green"))
    click.echo(click.style(f"  numeroExhorto:      {respuesta['numeroExhorto']}", fg="green"))
    click.echo(click.style(f"  tipoDiligenciado:   {respuesta['tipoDiligenciado']}", fg="green"))
    click.echo(click.style(f"  observaciones:      {respuesta['observaciones']}", fg="green"))

    # Mostrar los datos de los archivos de la respuesta que se va a enviar
    click.echo(click.style("Los archivos son...", fg="white"))
    for archivo in respuesta["archivos"]:
        click.echo(click.style(f"  nombreArchivo: {archivo['nombreArchivo']}", fg="green"))
        click.echo(click.style(f"  hashSha1:      {archivo['hashSha1']}", fg="green"))
        click.echo(click.style(f"  hashSha256:    {archivo['hashSha256']}", fg="green"))
        click.echo(click.style(f"  tipoDocumento: {archivo['tipoDocumento']}", fg="green"))

    # Mostrar los datos de los videos de la respuesta que se va a enviar
    if len(respuesta["videos"]) > 0:
        click.echo(click.style("Los los videos son...", fg="white"))
        for video in respuesta["videos"]:
            click.echo(click.style(f"  titulo:      {video['titulo']}", fg="green"))
            click.echo(click.style(f"  descripcion: {video['descripcion']}", fg="green"))
            click.echo(click.style(f"  fecha:       {video['fecha']}", fg="green"))
            click.echo(click.style(f"  urlAcceso:   {video['urlAcceso']}", fg="green"))
    else:
        click.echo(click.style("No hay videos en la respuesta.", fg="white"))

    # Esperar a que se presione ENTER para continuar
    input("Presiona ENTER para DEMOSTRAR que se va a recibir la respuesta...")

    # Actualizar el exhorto
    click.echo(click.style("Actualizando el exhorto...", fg="yellow"))
    exh_exhorto.respuesta_origen_id = respuesta["respuestaOrigenId"]
    exh_exhorto.respuesta_municipio_turnado_id = int(respuesta["municipioTurnadoId"])
    exh_exhorto.respuesta_area_turnado_id = respuesta["areaTurnadoId"]
    exh_exhorto.respuesta_area_turnado_nombre = respuesta["areaTurnadoNombre"]
    exh_exhorto.respuesta_numero_exhorto = respuesta["numeroExhorto"]
    exh_exhorto.respuesta_tipo_diligenciado = respuesta["tipoDiligenciado"]
    exh_exhorto.respuesta_observaciones = respuesta["observaciones"]
    exh_exhorto.respuesta_fecha_hora_recepcion = datetime.now()
    exh_exhorto.respuesta_fecha_hora_recepcion = datetime.now()
    exh_exhorto.estado = "RESPONDIDO"
    exh_exhorto.save()

    # Insertar los archivos de la respuesta
    click.echo(click.style("Insertando los archivos...", fg="yellow"))
    for archivo in respuesta["archivos"]:
        exh_exhorto_archivo = ExhExhortoArchivo()
        exh_exhorto_archivo.exh_exhorto_id = exh_exhorto.id
        exh_exhorto_archivo.nombre_archivo = archivo["nombreArchivo"]
        exh_exhorto_archivo.hash_sha1 = archivo["hashSha1"]
        exh_exhorto_archivo.hash_sha256 = archivo["hashSha256"]
        exh_exhorto_archivo.tipo_documento = archivo["tipoDocumento"]
        exh_exhorto_archivo.es_respuesta = True
        exh_exhorto_archivo.estado = "PENDIENTE"
        exh_exhorto_archivo.url = ""
        exh_exhorto_archivo.tamano = 0
        exh_exhorto_archivo.save()
        click.echo(click.style(f"He insertado el archivo {exh_exhorto_archivo.nombre_archivo}", fg="green"))

    # Insertar los videos con datos aleatorios que vendrían en la respuesta
    click.echo(click.style("Insertando los videos...", fg="yellow"))
    for video in respuesta["videos"]:
        exh_exhorto_video = ExhExhortoVideo()
        exh_exhorto_video.exh_exhorto_id = exh_exhorto.id
        exh_exhorto_video.titulo = video["titulo"]
        exh_exhorto_video.descripcion = video["descripcion"]
        exh_exhorto_video.fecha = video["fecha"]
        exh_exhorto_video.url_acceso = video["urlAcceso"]
        exh_exhorto_video.save()
        click.echo(click.style(f"He insertado el video {exh_exhorto_video.titulo}", fg="green"))

    # Mensaje final
    click.echo(click.style(f"Terminó recibir respuesta del exhorto {exh_exhorto.exhorto_origen_id}", fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
@click.argument("actualizacion_origen_id", type=str)
def demo_06_enviar_actualizacion(exhorto_origen_id, actualizacion_origen_id):
    """Enviar una actualización"""
    click.echo("Enviar una actualización")

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "RESPONDIDO" o "CONTESTADO"
    if exh_exhorto.estado not in ("RESPONDIDO", "CONTESTADO"):
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado PROCESANDO o DILIGENCIADO", fg="red"))
        sys.exit(1)

    # Consultar la actualización con la actualizacion_origen_id
    exh_exhorto_actualizacion = (
        ExhExhortoActualizacion.query.filter_by(exh_exhorto_id=exh_exhorto.id)
        .filter_by(actualizacion_origen_id=actualizacion_origen_id)
        .first()
    )

    # Validar que exista la actualización
    if exh_exhorto_actualizacion is None:
        click.echo(click.style(f"No existe la actualización {actualizacion_origen_id}", fg="red"))
        sys.exit(1)

    # Mostrar lo que se va a enviar
    click.echo(click.style("Mostrar lo que se va a enviar...", fg="white"))
    click.echo(click.style(f"exhortoId:             {exh_exhorto.exhorto_origen_id}", fg="green"))
    click.echo(click.style(f"actualizacionOrigenId: {exh_exhorto_actualizacion.actualizacion_origen_id}", fg="green"))
    click.echo(click.style(f"tipoActualizacion:     {exh_exhorto_actualizacion.tipo_actualizacion}", fg="green"))
    click.echo(click.style(f"fechaHora:             {exh_exhorto_actualizacion.fecha_hora}", fg="green"))
    click.echo(click.style(f"descripcion:           {exh_exhorto_actualizacion.descripcion}", fg="green"))

    # Esperar a que se presione ENTER para continuar
    input("Presiona ENTER para DEMOSTRAR que se va a enviar la actualización...")

    # Simular lo que se va a recibir
    respuesta = {
        "exhortoId": exh_exhorto.exhorto_origen_id,
        "actualizacionOrigenId": exh_exhorto_actualizacion.actualizacion_origen_id,
        "fechaHora": datetime.now(),
    }

    # Simular lo que se va a recibir
    click.echo(click.style("Simular lo que se va a recibir...", fg="white"))
    click.echo(click.style(f"exhortoId:             {respuesta['exhortoId']}", fg="green"))
    click.echo(click.style(f"actualizacionOrigenId: {respuesta['actualizacionOrigenId']}", fg="green"))
    click.echo(click.style(f"fechaHora:             {respuesta['fechaHora']} (TIEMPO ACTUAL)", fg="green"))

    # Actualizar la actualización con la fecha y hora de recepción
    click.echo(click.style("Actualizando la actualización...", fg="yellow"))
    exh_exhorto_actualizacion.fecha_hora_recepcion = respuesta["fechaHora"]
    exh_exhorto_actualizacion.save()

    # Mensaje final
    click.echo(click.style(f"Terminó enviar la actualización del exhorto {exhorto_origen_id}", fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_06_recibir_actualizacion(exhorto_origen_id):
    """Recibir una actualización"""
    click.echo("Recibir una actualización")

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "RESPONDIDO" o "CONTESTADO"
    if exh_exhorto.estado not in ("RESPONDIDO", "CONTESTADO"):
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado PROCESANDO o DILIGENCIADO", fg="red"))
        sys.exit(1)

    # Simular el tipo_actualizacion
    tipo_actualizacion = random.choice(["AreaTurnado", "NumeroExhorto"])
    descripcion = ""

    # Si es "AreaTurnado" la descripción es un hipotético juzgado al azar
    if tipo_actualizacion == "AreaTurnado":
        juzgado_numero = random.randint(1, 5)
        descripcion = f"JUZGADO {juzgado_numero} CIVIL"

    # Si es "NumeroExhorto" la descripción es un hipotético número de expediente al azar
    if tipo_actualizacion == "NumeroExhorto":
        descripcion = f"{random.randint(1, 999)}/{datetime.now().year}"

    # Esperar a que se presione ENTER para continuar
    input("Presiona ENTER para DEMOSTRAR que se va a recibir la actualización...")

    # Simular lo que se va a recibir
    recibido = {
        "exhortoId": exh_exhorto.exhorto_origen_id,
        "actualizacionOrigenId": generar_identificador(),
        "tipoActualizacion": tipo_actualizacion,
        "fechaHora": datetime.now(),
        "descripcion": descripcion,
    }

    # Simular lo que se va a recibir
    click.echo(click.style("Simular lo que se va a recibir...", fg="white"))
    click.echo(click.style(f"exhortoId:             {recibido['exhortoId']}", fg="green"))
    click.echo(click.style(f"actualizacionOrigenId: {recibido['actualizacionOrigenId']} (GENERADO AL AZAR)", fg="green"))
    click.echo(click.style(f"tipoActualizacion:     {recibido['tipoActualizacion']} (GENERADO AL AZAR)", fg="green"))
    click.echo(click.style(f"fechaHora:             {recibido['fechaHora']} (TIEMPO ACTUAL)", fg="green"))
    click.echo(click.style(f"descripcion:           {recibido['descripcion']} (HIPOTETICO)", fg="green"))

    # Insertar la actualización
    click.echo(click.style("Insertando la actualización...", fg="yellow"))
    exh_exhorto_actualizacion = ExhExhortoActualizacion()
    exh_exhorto_actualizacion.exh_exhorto_id = exh_exhorto.id
    exh_exhorto_actualizacion.actualizacion_origen_id = recibido["actualizacionOrigenId"]
    exh_exhorto_actualizacion.tipo_actualizacion = recibido["tipoActualizacion"]
    exh_exhorto_actualizacion.fecha_hora = recibido["fechaHora"]
    exh_exhorto_actualizacion.descripcion = recibido["descripcion"]
    exh_exhorto_actualizacion.save()

    # Simular lo que se va a responder
    respuesta = {
        "exhortoId": exh_exhorto.exhorto_origen_id,
        "actualizacionOrigenId": exh_exhorto_actualizacion.actualizacion_origen_id,
        "fechaHora": datetime.now(),
    }

    # Simular lo que se va a responder
    click.echo(click.style("Simular lo que se va a responder...", fg="white"))
    click.echo(click.style(f"exhortoId:             {respuesta['exhortoId']}", fg="green"))
    click.echo(click.style(f"actualizacionOrigenId: {respuesta['actualizacionOrigenId']}", fg="green"))
    click.echo(click.style(f"fechaHora:             {respuesta['fechaHora']}", fg="green"))

    # Mensaje final
    click.echo(click.style(f"Terminó recibir la actualización del exhorto {exhorto_origen_id}", fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
@click.argument("folio_origen_promocion", type=str)
def demo_07_enviar_promocion(exhorto_origen_id, folio_origen_promocion):
    """Enviar una promoción"""
    click.echo("Enviar una promoción")

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "RESPONDIDO" o "CONTESTADO"
    if exh_exhorto.estado not in ("RESPONDIDO", "CONTESTADO"):
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado PROCESANDO o DILIGENCIADO", fg="red"))
        sys.exit(1)

    # Consultar la promoción con el folio_origen_promocion
    exh_exhorto_promocion = ExhExhortoPromocion.query.filter_by(folio_origen_promocion=folio_origen_promocion).first()
    if exh_exhorto_promocion is None:
        click.echo(click.style(f"No existe la promoción {folio_origen_promocion}", fg="red"))
        sys.exit(1)

    # Se va a enviar...
    # folioSeguimiento
    # folioOrigenPromocion
    # promoventes
    # fojas
    # fechaOrigen
    # observaciones
    # archivos

    # Se va a recibir...
    # folioOrigenPromocion
    # fechaHora

    # Mensaje final
    click.echo(click.style(f"Terminó enviar la promoción del exhorto {exhorto_origen_id}", fg="green"))


@click.command()
@click.argument("exhorto_origen_id", type=str)
def demo_07_recibir_promocion(exhorto_origen_id):
    """Recibir una promoción"""
    click.echo("Recibir una promoción")

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "RESPONDIDO" o "CONTESTADO"
    if exh_exhorto.estado not in ("RESPONDIDO", "CONTESTADO"):
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado PROCESANDO o DILIGENCIADO", fg="red"))
        sys.exit(1)

    # Se va a recibir...
    # folioSeguimiento
    # folioOrigenPromocion
    # promoventes
    # fojas
    # fechaOrigen
    # observaciones
    # archivos

    # Se va a enviar...
    # folioOrigenPromocion
    # fechaHora

    # Mensaje final
    click.echo(click.style(f"Terminó recibir la promoción del exhorto {exhorto_origen_id}", fg="green"))


cli.add_command(truncar)
cli.add_command(demo_02_enviar)
cli.add_command(demo_02_recibir)
cli.add_command(demo_05_enviar_respuesta)
cli.add_command(demo_05_recibir_respuesta)
cli.add_command(demo_06_enviar_actualizacion)
cli.add_command(demo_06_recibir_actualizacion)
cli.add_command(demo_07_enviar_promocion)
cli.add_command(demo_07_recibir_promocion)
