"""
CLI Usuarios

- mostrar_api_key: Mostrar la API Key de un usuario
- nueva_api_key: Nueva API Key
- nueva_contrasena: Nueva contraseña
- reporte: Reporte de usuarios modificados a un archivo CSV
"""

import sys
import re
import csv
import calendar
from datetime import datetime, timedelta
from pathlib import Path

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


@click.command()
@click.argument("anio_mes", type=str)
@click.option("--output", default="reporte_usuarios.csv", type=str, help="Archivo CSV a escribir")
def generar_sicgd_csv(anio_mes, output):
    """Generar CSV para SICGD Usuarios en el Sistema de Plataforma Web"""
    # Validar el archivo CSV a escribir, que no exista
    ruta = Path(output)
    if ruta.exists():
        click.echo(f"AVISO: {output} existe, no voy a sobreescribirlo.")
        return
    # Validar que el parámetro mes_int sea YYYY-MM
    if not re.match(r"^\d{4}-\d{2}$", anio_mes):
        click.echo(f"ERROR: {anio_mes} no es una fecha valida (YYYY-MM)")
        return
    # Calcular fecha desde y hasta
    desde = f"{anio_mes}-01"
    anio = int(anio_mes[0:4])
    mes = int(anio_mes[5:7])
    _, ultimo_dia = calendar.monthrange(anio, mes)
    hasta = f"{anio_mes}-{ultimo_dia}"
    # Validar que la fecha desde sea menor que la fecha hasta
    if desde > hasta:
        click.echo(f"ERROR: {desde} es mayor que {hasta}")
        return
    # Consultar usuarios
    click.echo("Elaborando reporte de usuarios...")
    contador = 0
    usuarios = Usuario.query
    if desde:
        usuarios = usuarios.filter(Usuario.modificado >= f"{desde} 00:00:00")
    if hasta:
        usuarios = usuarios.filter(Usuario.modificado <= f"{hasta} 23:59:59")
    usuarios = usuarios.order_by(Usuario.modificado).all()
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "Fecha",
                "Nombre Completo",
                "CURP",
                "Correo Electrónico",
                "Autoridad",
                "Oficina",
                "Roles",
                "Operacion",
            ]
        )
        for usuario in usuarios:
            # Definir operacion
            operacion = "ALTA"  # Por defecto, es ALTA
            if usuario.estatus == "B":
                operacion = "BAJA"  # Si estatus es B, es BAJA
            elif usuario.modificado - usuario.creado > timedelta(hours=24):
                operacion = "CAMBIO"  # Si modificado tiene mas de 24 horas respecto a creado, es CAMBIO
            # Escribir la linea
            respaldo.writerow(
                [
                    usuario.modificado.strftime("%Y-%m-%d %H:%M:%S"),
                    usuario.nombre,
                    usuario.curp,
                    usuario.email,
                    usuario.autoridad.clave,
                    usuario.oficina.clave,
                    ", ".join(usuario.get_roles()),
                    operacion,
                ]
            )
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} en {ruta.name}")


cli.add_command(mostrar_api_key)
cli.add_command(nueva_api_key)
cli.add_command(nueva_contrasena)
cli.add_command(generar_sicgd_csv)
