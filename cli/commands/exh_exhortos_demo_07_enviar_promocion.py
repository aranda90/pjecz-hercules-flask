"""
Exh Exhortos Demo 07 Enviar promoción

Esta es una demostración que va a insertar datos aleatorios en la base de datos para probar la interfaz de usuario.
"""

import random
import string
import sys
from datetime import datetime, timedelta

import click
from faker import Faker
from sqlalchemy import text

from hercules.app import create_app
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_areas.models import ExhArea
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_exhortos_actualizaciones.models import ExhExhortoActualizacion
from hercules.blueprints.exh_exhortos_archivos.models import ExhExhortoArchivo
from hercules.blueprints.exh_exhortos_partes.models import ExhExhortoParte
from hercules.blueprints.exh_exhortos_promociones.models import ExhExhortoPromocion
from hercules.blueprints.exh_exhortos_promociones_archivos.models import ExhExhortoPromocionArchivo
from hercules.blueprints.exh_exhortos_promociones_promoventes.models import ExhExhortoPromocionPromovente
from hercules.blueprints.exh_exhortos_videos.models import ExhExhortoVideo
from hercules.blueprints.materias.models import Materia
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.pwgen import generar_identificador
from lib.safe_string import safe_string

app = create_app()
app.app_context().push()
database.app = app

ARCHIVO_PRUEBA_PDF = "prueba-1.pdf"
ARCHIVO_PRUEBA_PDF_HASHSHA1 = "3a9a09bbb22a6da576b2868c4b861cae6b096050"
ARCHIVO_PRUEBA_PDF_HASHSHA256 = "df3d983d24a5002e7dcbff1629e25f45bb3def406682642643efc4c1c8950a77"
ESTADO_ORIGEN_ID = 5  # Coahuila de Zaragoza


def demo_enviar_promocion(exhorto_origen_id: str, folio_origen_promocion: str) -> str:
    """Enviar una promoción"""

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "RESPONDIDO" o "CONTESTADO"
    if exh_exhorto.estado not in ("RESPONDIDO", "CONTESTADO"):
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado PROCESANDO o DILIGENCIADO", fg="red"))
        sys.exit(1)

    # Consultar la promoción con el folio_origen_promocion
    exh_exhorto_promocion = ExhExhortoPromocion.query.filter_by(folio_origen_promocion=folio_origen_promocion).first()
    if exh_exhorto_promocion is None:
        click.echo(click.style(f"No existe la promoción {folio_origen_promocion}", fg="red"))
        sys.exit(1)

    # Se va a enviar...
    # folioSeguimiento
    # folioOrigenPromocion
    # promoventes
    # fojas
    # fechaOrigen
    # observaciones
    # archivos

    # Se va a recibir...
    # folioOrigenPromocion
    # fechaHora

    # Entregar mensaje final
    return f"DEMO Terminó enviar la promoción del exhorto {exhorto_origen_id} con folio {folio_origen_promocion}"
