"""
CLI Permisos

- eliminar_no_usados: Eliminar los permisos con roles o modulos eliminados
"""

import click

from hercules.app import create_app
from hercules.blueprints.permisos.models import Permiso
from hercules.extensions import database

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Permisos"""


@click.command()
def eliminar_no_usados():
    """Eliminar los permisos con roles o modulos eliminados"""
    click.echo("Eliminar los permisos con roles o modulos eliminados: ", nl=False)
    contador = 0
    permisos = Permiso.query.filter_by(estatus="A").all()
    for permiso in permisos:
        if permiso.rol.estatus != "A" or permiso.modulo.estatus != "A":
            click.echo(click.style("-", fg="red"), nl=False)
            permiso.delete()
            contador += 1
    click.echo()
    click.echo(click.style(f"Se eliminaron {contador} permisos", fg="green"))


cli.add_command(eliminar_no_usados)
