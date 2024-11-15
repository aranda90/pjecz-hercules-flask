"""
CLI Financieros Vales de Gasolina
"""

import os
import sys

import click
from dotenv import load_dotenv

from lib.exceptions import (
    MyAnyError,
    MyConnectionError,
    MyMissingConfigurationError,
    MyNotValidParamError,
    MyStatusCodeError,
    MyRequestError,
    MyResponseError,
)
from hercules.blueprints.fin_vales.tasks import solicitar as solicitar_task
from hercules.blueprints.fin_vales.tasks import cancelar_solicitar as cancelar_solicitar_task
from hercules.blueprints.fin_vales.tasks import autorizar as autorizar_task
from hercules.blueprints.fin_vales.tasks import cancelar_autorizar as cancelar_autorizar_task
from hercules.blueprints.usuarios.models import Usuario

load_dotenv()  # Take environment variables from .env
FIN_VALES_EFIRMA_USUARIO_EMAIL = os.getenv("FIN_VALES_EFIRMA_USUARIO_EMAIL", "")
FIN_VALES_EFIRMA_USUARIO_PASSWORD = os.getenv("FIN_VALES_EFIRMA_USUARIO_PASSWORD", "")


@click.group()
def cli():
    """Fin Vales"""


@click.command()
@click.argument("fin_vale_id", type=int)
def solicitar(fin_vale_id: int):
    """Firmar electronicamente el vale por quien solicita"""

    # Validar que se haya configurado el usuario y contraseña
    if FIN_VALES_EFIRMA_USUARIO_EMAIL == "" or FIN_VALES_EFIRMA_USUARIO_PASSWORD == "":
        click.echo(click.style("No se ha configurado el usuario y/o la contraseña", fg="red"))
        sys.exit(1)

    # Obtener el usuario
    usuario = Usuario.query.filter(Usuario.email == FIN_VALES_EFIRMA_USUARIO_EMAIL).first()
    if usuario is None:
        click.echo(click.style(f"No se encontro el usuario con e-mail {FIN_VALES_EFIRMA_USUARIO_EMAIL}", fg="red"))
        sys.exit(1)

    # Ejecutar la tarea
    try:
        mensaje_termino = solicitar_task(
            fin_vale_id=fin_vale_id, usuario_id=usuario.id, contrasena=FIN_VALES_EFIRMA_USUARIO_PASSWORD
        )
    except (MyConnectionError, MyStatusCodeError, MyRequestError) as error:
        click.echo(click.style(str(error), fg="yellow"))
        sys.exit(0)
    except (MyMissingConfigurationError, MyNotValidParamError, MyResponseError) as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mostrar mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("fin_vale_id", type=int)
@click.option("--motivo", default="Cancelado", help="Motivo de la cancelacion")
def cancelar_solicitar(fin_vale_id: int, motivo: str):
    """Cancelar la firma electronica de un vale por quien solicita"""

    # Validar que se haya configurado el usuario y contraseña
    if FIN_VALES_EFIRMA_USUARIO_EMAIL == "" or FIN_VALES_EFIRMA_USUARIO_PASSWORD == "":
        click.echo(click.style("No se ha configurado el usuario y/o la contraseña", fg="red"))
        sys.exit(1)

    # Obtener el usuario
    usuario = Usuario.query.filter(Usuario.email == FIN_VALES_EFIRMA_USUARIO_EMAIL).first()
    if usuario is None:
        click.echo(click.style(f"No se encontro el usuario con e-mail {FIN_VALES_EFIRMA_USUARIO_EMAIL}", fg="red"))
        sys.exit(1)

    # Ejecutar la tarea
    try:
        mensaje_termino = cancelar_solicitar_task(
            fin_vale_id=fin_vale_id, contrasena=FIN_VALES_EFIRMA_USUARIO_PASSWORD, motivo=motivo
        )
    except (MyConnectionError, MyStatusCodeError, MyRequestError) as error:
        click.echo(click.style(str(error), fg="yellow"))
        sys.exit(0)
    except (MyMissingConfigurationError, MyNotValidParamError, MyResponseError) as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mostrar mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("fin_vale_id", type=int)
def autorizar(fin_vale_id: int):
    """Firmar electronicamente el vale por quien autoriza"""

    # Validar que se haya configurado el usuario y contraseña
    if FIN_VALES_EFIRMA_USUARIO_EMAIL == "" or FIN_VALES_EFIRMA_USUARIO_PASSWORD == "":
        click.echo(click.style("No se ha configurado el usuario y/o la contraseña", fg="red"))
        sys.exit(1)

    # Obtener el usuario
    usuario = Usuario.query.filter(Usuario.email == FIN_VALES_EFIRMA_USUARIO_EMAIL).first()
    if usuario is None:
        click.echo(click.style(f"No se encontro el usuario con e-mail {FIN_VALES_EFIRMA_USUARIO_EMAIL}", fg="red"))
        sys.exit(1)

    # Ejecutar la tarea
    try:
        mensaje_termino = autorizar_task(
            fin_vale_id=fin_vale_id, usuario_id=usuario.id, contrasena=FIN_VALES_EFIRMA_USUARIO_PASSWORD
        )
    except (MyConnectionError, MyStatusCodeError, MyRequestError) as error:
        click.echo(click.style(str(error), fg="yellow"))
        sys.exit(0)
    except (MyMissingConfigurationError, MyNotValidParamError, MyResponseError) as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mostrar mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


@click.command()
@click.argument("fin_vale_id", type=int)
@click.option("--motivo", default="Cancelado", help="Motivo de la cancelacion")
def cancelar_autorizar(fin_vale_id: int, motivo: str):
    """Cancelar la firma electronica de un vale por quien autoriza"""

    # Validar que se haya configurado el usuario y contraseña
    if FIN_VALES_EFIRMA_USUARIO_EMAIL == "" or FIN_VALES_EFIRMA_USUARIO_PASSWORD == "":
        click.echo(click.style("No se ha configurado el usuario y/o la contraseña", fg="red"))
        sys.exit(1)

    # Obtener el usuario
    usuario = Usuario.query.filter(Usuario.email == FIN_VALES_EFIRMA_USUARIO_EMAIL).first()
    if usuario is None:
        click.echo(click.style(f"No se encontro el usuario con e-mail {FIN_VALES_EFIRMA_USUARIO_EMAIL}", fg="red"))
        sys.exit(1)

    # Ejecutar la tarea
    try:
        mensaje_termino = cancelar_autorizar_task(
            fin_vale_id=fin_vale_id, contrasena=FIN_VALES_EFIRMA_USUARIO_PASSWORD, motivo=motivo
        )
    except (MyConnectionError, MyStatusCodeError, MyRequestError) as error:
        click.echo(click.style(str(error), fg="yellow"))
        sys.exit(0)
    except (MyMissingConfigurationError, MyNotValidParamError, MyResponseError) as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mostrar mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


cli.add_command(solicitar)
cli.add_command(cancelar_solicitar)
cli.add_command(autorizar)
cli.add_command(cancelar_autorizar)
