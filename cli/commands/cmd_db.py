"""
CLI Base de Datos

No deje de configurar la variable de entorno RESPALDOS_BASE_DIR

    # CLI Directorio base donde encontrar los respaldos de la base de datos
    RESPALDOS_BASE_DIR=/home/USUARIO/Descargas/Minerva/pjecz_plataforma_web

Para hacer un bucle del mes 01 al 12 de 2024, ejecutar

    for mes in {01..12}; do cli db generar-csv "2024-${mes}"; done

Para tomar los archivos en GCS agregue en las variables de entorno

    # Google Cloud Storage para generar reportes SICGD CSV
    CLOUD_STORAGE_DEPOSITO_RESPALDOS=

"""

import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from google.cloud import storage
from google.cloud.exceptions import NotFound
from tabulate import tabulate

from cli.commands.alimentar_autoridades import alimentar_autoridades
from cli.commands.alimentar_distritos import alimentar_distritos, eliminar_distritos_sin_autoridades
from cli.commands.alimentar_domicilios import alimentar_domicilios
from cli.commands.alimentar_estados import alimentar_estados
from cli.commands.alimentar_materias import alimentar_materias
from cli.commands.alimentar_modulos import alimentar_modulos
from cli.commands.alimentar_municipios import alimentar_municipios
from cli.commands.alimentar_oficinas import alimentar_oficinas
from cli.commands.alimentar_permisos import alimentar_permisos
from cli.commands.alimentar_roles import alimentar_roles
from cli.commands.alimentar_usuarios import alimentar_usuarios
from cli.commands.alimentar_usuarios_roles import alimentar_usuarios_roles
from cli.commands.respaldar_autoridades import respaldar_autoridades
from cli.commands.respaldar_distritos import respaldar_distritos
from cli.commands.respaldar_domicilios import respaldar_domicilios
from cli.commands.respaldar_estados import respaldar_estados
from cli.commands.respaldar_inv_custodias import respaldar_inv_custodias
from cli.commands.respaldar_inv_equipos import respaldar_inv_equipos
from cli.commands.respaldar_inv_marcas import respaldar_inv_marcas
from cli.commands.respaldar_inv_modelos import respaldar_inv_modelos
from cli.commands.respaldar_materias import respaldar_materias
from cli.commands.respaldar_modulos import respaldar_modulos
from cli.commands.respaldar_municipios import respaldar_municipios
from cli.commands.respaldar_oficinas import respaldar_oficinas
from cli.commands.respaldar_roles_permisos import respaldar_roles_permisos
from cli.commands.respaldar_usuarios_roles import respaldar_usuarios_roles
from hercules.app import create_app
from hercules.extensions import database
from lib.safe_string import safe_clave, safe_string

app = create_app()
app.app_context().push()
database.app = app

load_dotenv()  # Take environment variables from .env
CLOUD_STORAGE_DEPOSITO_RESPALDOS = os.environ.get("CLOUD_STORAGE_DEPOSITO_RESPALDOS")
DEPLOYMENT_ENVIRONMENT = os.environ.get("DEPLOYMENT_ENVIRONMENT", "develop").upper()
RESPALDOS_BASE_DIR = os.getenv("RESPALDOS_BASE_DIR", "")

BASE_DE_DATOS = "pjecz_plataforma_web"


@click.group()
def cli():
    """Base de Datos"""


@click.command()
def inicializar():
    """Inicializar"""
    if DEPLOYMENT_ENVIRONMENT == "PRODUCTION":
        click.echo("PROHIBIDO: No se inicializa porque este es el servidor de producción.")
        sys.exit(1)
    database.drop_all()
    database.create_all()
    click.echo("Termina inicializar.")


@click.command()
def alimentar():
    """Alimentar"""
    if DEPLOYMENT_ENVIRONMENT == "PRODUCTION":
        click.echo("PROHIBIDO: No se alimenta porque este es el servidor de producción.")
        sys.exit(1)
    alimentar_estados()
    alimentar_municipios()
    alimentar_materias()
    alimentar_modulos()
    alimentar_roles()
    alimentar_permisos()
    alimentar_distritos()
    alimentar_autoridades()
    eliminar_distritos_sin_autoridades()
    alimentar_domicilios()
    alimentar_oficinas()
    alimentar_usuarios()
    alimentar_usuarios_roles()
    click.echo("Termina alimentar.")


@click.command()
@click.pass_context
def reiniciar(ctx):
    """Reiniciar ejecuta inicializar y alimentar"""
    ctx.invoke(inicializar)
    ctx.invoke(alimentar)


@click.command()
@click.option("--inventarios", is_flag=True, help="Respaldar inventarios")
def respaldar(inventarios: bool):
    """Respaldar"""
    if inventarios:
        respaldar_inv_marcas()
        respaldar_inv_modelos()
        respaldar_inv_equipos()
        respaldar_inv_custodias()
        click.echo("Termina respaldar inventarios.")
        return
    respaldar_autoridades()
    respaldar_distritos()
    respaldar_domicilios()
    respaldar_estados()
    respaldar_materias()
    respaldar_modulos()
    respaldar_municipios()
    respaldar_oficinas()
    respaldar_roles_permisos()
    respaldar_usuarios_roles()
    click.echo("Termina respaldar.")


@click.command()
def copiar():
    """Copiar registros desde BD Origen a la BD Destino"""
    click.echo("Termina copiar.")


@click.command()
@click.argument("anio_mes", type=str)
@click.option("--cloud-storage", is_flag=True, help="Con datos de GCStorage")
def generar_sicgd_csv(anio_mes, cloud_storage):
    """Generar CSV para SICGD Respaldos BD"""

    # Compilar la expresion regular que sirve para tomar YYYY-MM-DD-HHMM del nombre del archivo
    fecha_hm_regexp = re.compile(r"\d{4}-\d{2}-\d{2}-\d{4}")

    # Definir el nombre del archivo CSV que se va a escribir
    output = f"reporte_respaldos_bd_{BASE_DE_DATOS}_{anio_mes}.csv"

    # Validar que el archivo CSV no exista
    ruta = Path(output)
    if ruta.exists():
        click.echo(f"AVISO: {output} existe, no voy a sobreescribirlo.")
        return

    # Validar que el parámetro mes_int sea YYYY-MM
    if not re.match(r"^\d{4}-\d{2}$", anio_mes):
        click.echo(f"ERROR: {anio_mes} no es una fecha valida (YYYY-MM)")
        return

    # Inicializar el listado de archivos
    archivos = []

    # Si se solicita con datos de Google Cloud Storage
    if cloud_storage is True:
        # Validar que exista el depósito
        try:
            bucket = storage.Client().get_bucket(CLOUD_STORAGE_DEPOSITO_RESPALDOS)
        except NotFound as error:
            click.echo(click.style(f"No existe el depósito {CLOUD_STORAGE_DEPOSITO_RESPALDOS}", fg="red"))
            sys.exit(1)

        # Buscar los archivos en el subdirectorio
        subdirectorio = BASE_DE_DATOS
        blobs = list(bucket.list_blobs(prefix=subdirectorio))
        archivos_cantidad = len(blobs)
        if archivos_cantidad == 0:
            click.echo(click.style(f"No hay archivos en el subdirectorio {subdirectorio} para insertar", fg="blue"))
            for blob in blobs:
                if anio_mes in blob.name:
                    click.echo(f"  {blob.name}")

        # Buscar archivos dentro del directorio de respaldo que tengan el nombre buscado
        click.echo("Elaborando reporte de respaldos BD...")
        nombre_buscado = f"{BASE_DE_DATOS}-{anio_mes[0:4]}-{anio_mes[5:7]}-"
        for blob in blobs:
            if nombre_buscado in blob.name:
                stat = 0
                concordancia = fecha_hm_regexp.search(blob.name)
                if concordancia:
                    patron_fecha = concordancia.group()
                    fecha = datetime.strptime(patron_fecha, "%Y-%m-%d-%H%M")
                    stat = blob.size / (1024 * 1024)
                else:
                    fecha = datetime.now()
                archivo = {
                    "fecha": fecha,
                    "nombre": blob.name.split("/")[-1],
                    "tamanio": stat,
                }
                archivos.append(archivo)

    # Si NO se solicita con datos de Google Cloud Storage, entonces es con archivos locales
    if cloud_storage is False:
        # Validar que la variable de entorno este definida
        if RESPALDOS_BASE_DIR is None or RESPALDOS_BASE_DIR == "":
            click.echo("ERROR: Falta la variable de entorno RESPALDOS_BASE_DIR")
            return

        # Validar que exista y que sea un directorio
        respaldos_base_dir = Path(RESPALDOS_BASE_DIR)
        if not respaldos_base_dir.exists() or not respaldos_base_dir.is_dir():
            click.echo(f"ERROR: No existe o no es directorio {respaldos_base_dir}")
            return

        # Buscar archivos dentro del directorio de respaldo que tengan el nombre buscado
        click.echo("Elaborando reporte de respaldos BD...")
        nombre_buscado = f"{BASE_DE_DATOS}-{anio_mes[0:4]}-{anio_mes[5:7]}-"
        for archivo in respaldos_base_dir.rglob("*"):
            if nombre_buscado in archivo.name:
                stat = os.stat(archivo)
                patron_fecha = re.search(r"\d{4}-\d{2}-\d{2}-\d{4}", archivo.name)
                patron_fecha = patron_fecha.group()
                fecha = datetime.strptime(patron_fecha, "%Y-%m-%d-%H%M")
                archivo = {
                    "fecha": fecha,
                    "nombre": archivo.name,
                    "tamanio": stat.st_size / (1024 * 1024),
                }
                archivos.append(archivo)

    # Si no se encontraron archivos, salir
    if len(archivos) <= 0:
        click.echo("No se genero el archivo porque no se encontraron archivos.")
        return

    # Escribir el archivo CSV
    with open(ruta, "w", encoding="utf8") as puntero:
        reporte = csv.writer(puntero)
        reporte.writerow(
            [
                "Fecha",
                "Nombre del archivo",
                "Tamaño",
            ]
        )
        for archivo in archivos:
            reporte.writerow(
                [
                    archivo["fecha"].strftime("%Y-%m-%d %H:%M:%S"),
                    archivo["nombre"],
                    f"{archivo['tamanio']:.2f}",
                ]
            )

    # Crear tabla con tabulate
    table = [
        [archivo["fecha"].strftime("%Y-%m-%d %H:%M"), archivo["nombre"], f"{archivo['tamanio']:.2f}"] for archivo in archivos
    ]
    headers = ["Fecha", "Nombre del archivo", "Tamaño (MB)"]
    click.echo(tabulate(table, headers, tablefmt="github"))

    # Mostrar mensaje final
    click.echo(f"  {len(archivos)} archivos de respaldo en {ruta.name}")


cli.add_command(inicializar)
cli.add_command(alimentar)
cli.add_command(reiniciar)
cli.add_command(respaldar)
cli.add_command(copiar)
cli.add_command(generar_sicgd_csv)
