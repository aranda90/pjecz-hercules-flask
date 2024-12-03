"""
CLI Archivos Documentos

- buscar: Buscar en Expediente Virtual
- mostrar_duplicados: Mostrar duplicados de expedientes
"""

import os
import sys

import click
import requests
from dotenv import load_dotenv

from hercules.app import create_app
from hercules.blueprints.arc_documentos.models import ArcDocumento
from hercules.blueprints.arc_documentos_tipos.models import ArcDocumentoTipo
from hercules.blueprints.autoridades.models import Autoridad
from hercules.extensions import database
from lib.safe_string import safe_clave

app = create_app()
app.app_context().push()
database.app = app

load_dotenv()
EXPEDIENTE_VIRTUAL_API_URL = os.environ.get("EXPEDIENTE_VIRTUAL_API_URL", "")
EXPEDIENTE_VIRTUAL_API_KEY = os.environ.get("EXPEDIENTE_VIRTUAL_API_KEY", "")


@click.group()
def cli():
    """Archivos Documentos"""


@click.command()
@click.argument("num_expediente", type=str)
@click.argument("autoridad_clave", type=str)
def buscar(num_expediente, autoridad_clave):
    """Buscar en expediente virtual"""
    click.echo(num_expediente)
    click.echo(autoridad_clave)
    click.echo(EXPEDIENTE_VIRTUAL_API_URL)
    click.echo(EXPEDIENTE_VIRTUAL_API_KEY)

    autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
    juzgado_id = autoridad.datawarehouse_id
    if juzgado_id:
        # Armado del cuerpo de petición para la API
        request_body = {
            "idJuzgado": juzgado_id,
            "idOrigen": 0,
            "numeroExpediente": num_expediente,
        }
        # Hace el llamado a la API
        respuesta_api = {}
        try:
            respuesta = requests.post(
                EXPEDIENTE_VIRTUAL_API_URL,
                headers={"X-Api-Key": EXPEDIENTE_VIRTUAL_API_KEY},
                json=request_body,
                timeout=32,
            )
            respuesta.raise_for_status()
            respuesta_api = respuesta.json()
        except requests.exceptions.ConnectionError as err:
            click.echo(f"Error en conexión con el API. {err}. {request_body}")
        except requests.exceptions.Timeout as err:
            click.echo(f"Error de tiempo. {err}")
        except requests.exceptions.HTTPError as err:
            click.echo(f"Error HTTP. {err}")
        except requests.exceptions.RequestException as err:
            click.echo(f"Error desconocido. {err}")

        if "success" in respuesta_api:
            if respuesta_api["success"] is True:
                click.echo("=== Registro encontrado en Expediente Virtual ===")
                click.echo(f"\tNúm. Expediente: {num_expediente}")
                click.echo(f"\tSintesis: {respuesta_api['sintesis']}")
                click.echo(f"\tActor Promovente: {respuesta_api['actorPromovente']}")
                click.echo(f"\tDemandado: {respuesta_api['demandado']}")
            else:
                click.echo("Registro NO encontrado en PAIJ")
        else:
            click.echo("Respuesta no esperada por parte del API de DataWareHouse")


@click.command()
@click.argument("autoridad_clave", type=str)
def mostrar_duplicados(autoridad_clave):
    """Mostrar duplicados de expedientes"""

    # Validar autoridad
    autoridad_clave = safe_clave(autoridad_clave)
    if autoridad_clave == "":
        click.echo("No es correcta la clave de la autoridad")
        sys.exit(1)
    autoridad = Autoridad.query.filter(Autoridad.clave == autoridad_clave).first()
    if autoridad is None:
        click.echo(f"No existe la clave {autoridad_clave} en autoridades")
        sys.exit(1)
    if autoridad.estatus != "A":
        click.echo(f"La autoridad {autoridad_clave} no está activa")
        sys.exit(1)
    if not autoridad.es_jurisdiccional:
        click.echo(f"La autoridad {autoridad_clave} no es jurisdiccional")
        sys.exit(1)
    if autoridad.es_extinto:
        click.echo(f"La autoridad {autoridad_clave} es extinta")
        sys.exit(1)
    if autoridad.es_notaria:
        click.echo(f"La autoridad {autoridad_clave} es una notaría")
        sys.exit(1)

    # Inicializar sesión a la base de datos
    session = database.session()

    # Consultar los documentos de la autoridad
    arc_documentos = (
        session.query(ArcDocumento)
        .join(ArcDocumentoTipo)
        .filter(ArcDocumento.autoridad_id == autoridad.id)
        .filter(ArcDocumentoTipo.nombre == "EXPEDIENTE")
        .filter(ArcDocumento.estatus == "A")
        .order_by(ArcDocumento.id)
    )

    # Si no hay arc_documentos, terminar
    if arc_documentos.count() == 0:
        click.echo(f"No hay arc_documentos para la autoridad {autoridad_clave}")
        sys.exit(1)

    # Inicializar listado de expedientes duplicados
    expedientes_duplicados = []

    # Inicializar contadores
    contador_consultados = 0
    contador_duplicados = 0

    # Bucle por cada arc_documento
    for arc_documento in arc_documentos.all():
        # Incrementar contador de consultados
        contador_consultados += 1

        # Mostrar progreso cada 100 registros
        if contador_consultados % 100 == 0:
            click.echo(f"Van {contador_consultados} consultados, {contador_duplicados} duplicados...")

        # Si el expediente ya está en la lista de duplicados, continuar
        if arc_documento.expediente in expedientes_duplicados:
            continue

        # Consultar en arc_documentos, con la autoridad dada, los expedientes duplicados
        duplicados = (
            session.query(ArcDocumento)
            .join(ArcDocumentoTipo)
            .filter(ArcDocumento.autoridad_id == autoridad.id)
            .filter(ArcDocumento.expediente == arc_documento.expediente)
            .filter(ArcDocumentoTipo.nombre == "EXPEDIENTE")
            .filter(ArcDocumento.estatus == "A")
            .order_by(ArcDocumento.id)
        )

        # Si hay más de un registro, agregar a la lista de duplicados
        if duplicados.count() > 1:
            expedientes_duplicados.append(arc_documento.expediente)
            contador_duplicados += 1

    # Mostrar expedientes duplicados
    click.echo(",".join(expedientes_duplicados))

    # Mensaje de finalización
    click.echo(f"Se encontraron {contador_duplicados} duplicados en {contador_consultados} expedientes.")


cli.add_command(buscar)
cli.add_command(mostrar_duplicados)
