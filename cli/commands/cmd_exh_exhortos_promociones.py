"""
CLI Exh Exhortos Promociones
"""

import click

from hercules.blueprints.exh_exhortos_promociones.communications.send import enviar_promocion


@click.group()
def cli():
    """Exh Exhortos Promociones"""


@click.command()
@click.argument("exhorto_origen_id", type=str)
def enviar(exhorto_origen_id):
    """Enviar una promoción"""
    click.echo("Enviar una promoción")
    mensaje, _, _ = enviar_promocion(exhorto_origen_id)
    click.echo(click.style(mensaje, fg="green"))


cli.add_command(enviar)
