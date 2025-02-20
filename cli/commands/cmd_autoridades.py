"""
CLI Autoridades
"""

import sys

import click

from hercules.app import create_app
from hercules.blueprints.autoridades.models import Autoridad
from hercules.extensions import database

app = create_app()
app.app_context().push()
database.app = app

ORGANOS_JURISDICCIONALES_CON_GLOSAS = [
    "PLENO O SALA DEL TSJ",
    "TRIBUNAL DE CONCILIACION Y ARBITRAJE",
]


@click.group()
def cli():
    """Autoridades"""


@click.command()
@click.argument("deposito", type=str)
@click.option("--actualizar", is_flag=True)
def actualizar_directorios(deposito, actualizar):
    """Listar las autoridades activas"""

    # Validar depósito
    deposito = deposito.lower()
    if deposito not in ["edictos", "glosas", "listas", "sentencias"]:
        click.echo(click.style("NO es válido el depósito, debe ser edictos, glosas, listas o sentencias"))
        sys.exit(1)

    # Consultar las autoridades
    autoridades = Autoridad.query.filter(Autoridad.estatus == "A").order_by(Autoridad.clave).all()

    # Bucle por las autoridades
    contador = 0
    for autoridad in autoridades:
        # Inicializar
        ruta = ""
        ruta_nueva = ""

        # Tomar el directorio del depósito
        if deposito == "edictos":
            ruta = autoridad.directorio_edictos
        elif deposito == "glosas":
            ruta = autoridad.directorio_glosas
        elif deposito == "listas":
            ruta = autoridad.directorio_listas_de_acuerdos
        elif deposito == "sentencias":
            ruta = autoridad.directorio_sentencias

        # Si es jurisdiccional, definir la ruta nueva
        if autoridad.es_jurisdiccional is True:
            ruta_nueva = f"{autoridad.distrito.clave}/{autoridad.clave}"

        # Si es Notaría solo puede crear Edictos
        if autoridad.es_notaria and deposito != "edictos":
            ruta_nueva = ""

        # Solo los ORGANOS_JURISDICCIONALES_CON_GLOSAS pueden crear Glosas
        if deposito == "glosas" and autoridad.organo_jurisdiccional not in ORGANOS_JURISDICCIONALES_CON_GLOSAS:
            ruta_nueva = ""

        # Si la nueva ruta es igual a la que se tiene, se omite
        if ruta == ruta_nueva:
            continue

        # Mostrar en pantalla la clave, la ruta y la ruta nueva
        click.echo(click.style(f"{autoridad.clave}: ", fg="green"), nl=False)
        click.echo(click.style(f"{ruta} > ", fg="magenta"), nl=False)
        click.echo(click.style(ruta_nueva, fg="white"))
        contador += 1

        # Si se pide actualizar
        if actualizar:
            if deposito == "edictos":
                autoridad.directorio_edictos = ruta_nueva
            elif deposito == "glosas":
                autoridad.directorio_glosas = ruta_nueva
            elif deposito == "listas":
                autoridad.directorio_listas_de_acuerdos = ruta_nueva
            elif deposito == "sentencias":
                autoridad.directorio_sentencias = ruta_nueva
            autoridad.save()

    # Mensaje final
    if contador == 0:
        click.echo(click.style(f"Se han revisado los directorios de {deposito} y no hay que actualizar ninguno", fg="green"))
    elif actualizar:
        click.echo(click.style(f"Se han actualizado {contador} directorios de {deposito}", fg="green"))
    else:
        click.echo(click.style(f"SE PUEDEN ACTUALIZAR {contador} directorios de {deposito}", fg="yellow"))
        click.echo("Agregue el parámetro --actualizar para guardar en la base de datos")


cli.add_command(actualizar_directorios)
