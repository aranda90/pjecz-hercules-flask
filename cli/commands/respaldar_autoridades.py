"""
Respaldar Autoridades
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.autoridades.models import Autoridad

AUTORIDADES_CSV = "seed/autoridades.csv"


def respaldar_autoridades():
    """Respaldar Autoridades"""
    ruta = Path(AUTORIDADES_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {AUTORIDADES_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando autoridades: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "autoridad_id",
                "distrito_id",
                "materia_id",
                "municipio_id",
                "clave",
                "descripcion",
                "descripcion_corta",
                "es_archivo_solicitante",
                "es_cemasc",
                "es_defensoria",
                "es_extinto",
                "es_jurisdiccional",
                "es_notaria",
                "es_organo_especializado",
                "es_revisor_escrituras",
                "organo_jurisdiccional",
                "directorio_edictos",
                "directorio_glosas",
                "directorio_listas_de_acuerdos",
                "directorio_sentencias",
                "audiencia_categoria",
                "limite_dias_listas_de_acuerdos",
                "datawarehouse_id",
                "sede",
                "estatus",
            ]
        )
        for autoridad in Autoridad.query.order_by(Autoridad.id).all():
            respaldo.writerow(
                [
                    autoridad.id,
                    autoridad.distrito_id,
                    autoridad.materia_id,
                    autoridad.municipio_id,
                    autoridad.clave,
                    autoridad.descripcion,
                    autoridad.descripcion_corta,
                    int(autoridad.es_archivo_solicitante),
                    int(autoridad.es_cemasc),
                    int(autoridad.es_defensoria),
                    int(autoridad.es_extinto),
                    int(autoridad.es_jurisdiccional),
                    int(autoridad.es_notaria),
                    int(autoridad.es_organo_especializado),
                    int(autoridad.es_revisor_escrituras),
                    autoridad.organo_jurisdiccional,
                    autoridad.directorio_edictos,
                    autoridad.directorio_glosas,
                    autoridad.directorio_listas_de_acuerdos,
                    autoridad.directorio_sentencias,
                    autoridad.audiencia_categoria,
                    autoridad.limite_dias_listas_de_acuerdos,
                    autoridad.datawarehouse_id,
                    autoridad.sede,
                    autoridad.estatus,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} autoridades respaldadas.", fg="green"))
