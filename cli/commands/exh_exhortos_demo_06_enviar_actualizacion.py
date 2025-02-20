"""
Exh Exhortos Demo 06 Enviar Actualización

Esta es una demostración que va a insertar datos aleatorios en la base de datos para probar la interfaz de usuario.
"""

import sys
from datetime import datetime

import click

from hercules.app import create_app
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_actualizaciones.models import ExhExhortoActualizacion
from hercules.extensions import database

app = create_app()
app.app_context().push()
database.app = app

ARCHIVO_PRUEBA_PDF = "prueba-1.pdf"
ARCHIVO_PRUEBA_PDF_HASHSHA1 = "3a9a09bbb22a6da576b2868c4b861cae6b096050"
ARCHIVO_PRUEBA_PDF_HASHSHA256 = "df3d983d24a5002e7dcbff1629e25f45bb3def406682642643efc4c1c8950a77"
ESTADO_ORIGEN_ID = 5  # Coahuila de Zaragoza


def demo_enviar_actualizacion(exhorto_origen_id: str, actualizacion_origen_id: str) -> str:
    """Enviar una actualización"""

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

    # Entregar mensaje final
    return f"DEMO Terminó enviar la actualización del exhorto {exhorto_origen_id} con identificador {actualizacion_origen_id}"
