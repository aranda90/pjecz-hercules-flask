"""
CLI Bitácoras
"""

import sys

import click

from hercules.blueprints.bitacoras.tasks import enviar_reporte_diario
from lib.exceptions import MyAnyError


@click.group()
def cli():
    """Bitácoras"""


@click.command()
@click.argument("modulo_nombre", type=str)
@click.argument("to_email", type=str)
@click.option("--horas", default=24, type=int, help="Número de horas para el reporte")
def enviar(modulo_nombre, to_email, horas):
    """Enviar mensaje con el reporte diario del módulo dado"""
    click.echo(f"Inicia el envío del mensaje con el reporte diario del módulo {modulo_nombre} a {to_email}")

    # Enviar el mensaje
    try:
        mensaje_termino = enviar_reporte_diario(modulo_nombre, to_email, horas)
    except MyAnyError as error:
        click.echo(error)
        sys.exit(1)

    # Mensaje de termino
    click.echo(mensaje_termino)


cli.add_command(enviar)
