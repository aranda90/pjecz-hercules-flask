"""
CLI Exh Exhortos Actualizaciones
"""

import click

from hercules.blueprints.exh_exhortos_actualizaciones.communications.send import enviar_actualizacion


@click.group()
def cli():
    """Exh Exhortos Actualizaciones"""


@click.command()
@click.argument("exh_exhorto_actualizacion_id", type=int)
def enviar(exh_exhorto_actualizacion_id):
    """Enviar una actualización"""
    click.echo("Enviar una actualización")
    mensaje, _, _ = enviar_actualizacion(exh_exhorto_actualizacion_id)
    click.echo(click.style(mensaje, fg="green"))


cli.add_command(enviar)
