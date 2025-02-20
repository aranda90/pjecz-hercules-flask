"""
Exh Exhortos Demo 06 Recibir Actualización

Esta es una demostración que va a insertar datos aleatorios en la base de datos para probar la interfaz de usuario.
"""

import random
import sys
from datetime import datetime

import click

from hercules.app import create_app
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_actualizaciones.models import ExhExhortoActualizacion
from hercules.extensions import database
from lib.pwgen import generar_identificador

app = create_app()
app.app_context().push()
database.app = app

ARCHIVO_PRUEBA_PDF = "prueba-1.pdf"
ARCHIVO_PRUEBA_PDF_HASHSHA1 = "3a9a09bbb22a6da576b2868c4b861cae6b096050"
ARCHIVO_PRUEBA_PDF_HASHSHA256 = "df3d983d24a5002e7dcbff1629e25f45bb3def406682642643efc4c1c8950a77"
ESTADO_ORIGEN_ID = 5  # Coahuila de Zaragoza


def demo_recibir_actualizacion(exhorto_origen_id: str) -> str:
    """Recibir una actualización"""

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

    # Entregar mensaje final
    return f"DEMO Terminó recibir la actualización del exhorto {exhorto_origen_id}"
