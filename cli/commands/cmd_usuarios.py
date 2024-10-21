"""
CLI Usuarios

- mostrar_api_key: Mostrar la API Key de un usuario
- nueva_api_key: Nueva API Key
- nueva_contrasena: Nueva contraseña
"""

import sys
from datetime import datetime, timedelta

import click

from hercules.app import create_app
from hercules.blueprints.usuarios.models import Usuario
from hercules.extensions import database, pwd_context
from lib.pwgen import generar_api_key

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Usuarios"""


@click.command()
@click.argument("email", type=str)
def mostrar_api_key(email):
    """Mostrar la API Key de un usuario"""
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario is None:
        click.echo(f"ERROR: No existe el e-mail {email} en usuarios")
        sys.exit(1)
    click.echo(f"Usuario: {usuario.email}")
    click.echo(f"API key: {usuario.api_key}")
    click.echo(f"Expira:  {usuario.api_key_expiracion.strftime('%Y-%m-%d')}")


@click.command()
@click.argument("email", type=str)
@click.option("--dias", default=90, help="Cantidad de días para expirar la API Key")
def nueva_api_key(email, dias):
    """Nueva API Key"""
    usuario = Usuario.find_by_identity(email)
    if usuario is None:
        click.echo(f"No existe el e-mail {email} en usuarios")
        return
    api_key = generar_api_key(usuario.id, usuario.email)
    api_key_expiracion = datetime.now() + timedelta(days=dias)
    usuario.api_key = api_key
    usuario.api_key_expiracion = api_key_expiracion
    usuario.save()
    click.echo("Nueva API key")
    click.echo(f"Usuario: {usuario.email}")
    click.echo(f"API key: {usuario.api_key}")
    click.echo(f"Expira:  {usuario.api_key_expiracion.strftime('%Y-%m-%d')}")


@click.command()
@click.argument("email", type=str)
def nueva_contrasena(email):
    """Nueva contraseña"""
    usuario = Usuario.query.filter_by(email=email).first()
    if usuario is None:
        click.echo(f"ERROR: No existe el e-mail {email} en usuarios")
        sys.exit(1)
    contrasena_1 = input("Contraseña: ")
    contrasena_2 = input("De nuevo la misma contraseña: ")
    if contrasena_1 != contrasena_2:
        click.echo("ERROR: No son iguales las contraseñas. Por favor intente de nuevo.")
        sys.exit(1)
    usuario.contrasena = pwd_context.hash(contrasena_1.strip())
    usuario.save()
    click.echo(f"Se ha cambiado la contraseña de {email} en usuarios")


cli.add_command(mostrar_api_key)
cli.add_command(nueva_api_key)
cli.add_command(nueva_contrasena)
