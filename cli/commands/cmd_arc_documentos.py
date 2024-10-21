"""
CLI cmd_arc_documentos

- Buscar en Expediente Virtual
"""

import os
import sys
import requests
import click
from dotenv import load_dotenv

from hercules.app import create_app
from hercules.extensions import database

from hercules.blueprints.autoridades.models import Autoridad

# Crear la aplicacion Flask para poder usar la BD
app = create_app()
app.app_context().push()
database.app = app

# Cargar las variables de entorno
load_dotenv()

# Carga de Variables de Entorno
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


cli.add_command(buscar)
