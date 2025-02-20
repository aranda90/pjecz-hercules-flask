"""
Exh Exhortos Demo 02 Recibir

Esta es una demostración que va a insertar datos aleatorios en la base de datos para probar la interfaz de usuario.
"""

import random
import sys
from datetime import datetime

import click
from faker import Faker

from hercules.app import create_app
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_areas.models import ExhArea
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_archivos.models import ExhExhortoArchivo
from hercules.blueprints.exh_exhortos_partes.models import ExhExhortoParte
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


def demo_recibir_exhorto(estado_origen: str) -> str:
    """Recibir un exhorto"""

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
        exh_exhorto_archivo.estado = "RECIBIDO"
        exh_exhorto_archivo.url = ""
        exh_exhorto_archivo.tamano = 0
        exh_exhorto_archivo.save()
        click.echo(click.style(f"Archivo insertado {exh_exhorto_archivo.nombre_archivo}", fg="yellow"))

    # Entregar mensaje final
    return f"DEMO Terminó recibir un exhorto con estado origen {estado_origen}"
