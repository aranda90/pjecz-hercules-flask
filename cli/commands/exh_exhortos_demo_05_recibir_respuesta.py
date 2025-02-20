"""
Exh Exhortos Demo 05 Recibir Respuesta

Esta es una demostración que va a insertar datos aleatorios en la base de datos para probar la interfaz de usuario.
"""

import random
import string
import sys
from datetime import datetime

import click

from hercules.app import create_app
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_archivos.models import ExhExhortoArchivo
from hercules.blueprints.exh_exhortos_videos.models import ExhExhortoVideo
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.pwgen import generar_identificador

app = create_app()
app.app_context().push()
database.app = app

ARCHIVO_PRUEBA_PDF = "prueba-1.pdf"
ARCHIVO_PRUEBA_PDF_HASHSHA1 = "3a9a09bbb22a6da576b2868c4b861cae6b096050"
ARCHIVO_PRUEBA_PDF_HASHSHA256 = "df3d983d24a5002e7dcbff1629e25f45bb3def406682642643efc4c1c8950a77"
ESTADO_ORIGEN_ID = 5  # Coahuila de Zaragoza


def demo_recibir_respuesta(exhorto_origen_id: str) -> str:
    """Recibir respuesta de un exhorto RECIBIDO CON EXITO"""

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
        "tipoDiligenciado": random.randint(0, 2),
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
    return f"DEMO Terminó recibir respuesta del exhorto {exhorto_origen_id}"
