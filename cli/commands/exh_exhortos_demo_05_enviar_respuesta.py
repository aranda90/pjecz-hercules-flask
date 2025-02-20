"""
Exh Exhortos Demo 05 Enviar Respuesta

Esta es una demostración que va a insertar datos aleatorios en la base de datos para probar la interfaz de usuario.
"""

import sys
from datetime import datetime

import click

from hercules.app import create_app
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_archivos.models import ExhExhortoArchivo
from hercules.blueprints.exh_exhortos_videos.models import ExhExhortoVideo
from hercules.extensions import database
from lib.pwgen import generar_identificador

app = create_app()
app.app_context().push()
database.app = app

ARCHIVO_PRUEBA_PDF = "prueba-1.pdf"
ARCHIVO_PRUEBA_PDF_HASHSHA1 = "3a9a09bbb22a6da576b2868c4b861cae6b096050"
ARCHIVO_PRUEBA_PDF_HASHSHA256 = "df3d983d24a5002e7dcbff1629e25f45bb3def406682642643efc4c1c8950a77"
ESTADO_ORIGEN_ID = 5  # Coahuila de Zaragoza


def demo_enviar_respuesta(exhorto_origen_id: str) -> str:
    """Responder un exhorto PROCESANDO o DILIGENCIADO"""

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
        "numeroExhorto": exh_exhorto.numero_exhorto,
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

    # Entregar mensaje final
    return f"DEMO Terminó responder el exhorto {exhorto_origen_id}"
