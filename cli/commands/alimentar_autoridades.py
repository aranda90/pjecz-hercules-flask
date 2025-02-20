"""
Alimentar Autoridades
"""

import csv
import sys
from pathlib import Path

import click
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.distritos.models import Distrito
from hercules.blueprints.materias.models import Materia
from hercules.blueprints.municipios.models import Municipio
from lib.safe_string import safe_clave, safe_string

AUTORIDADES_CSV = "seed/autoridades.csv"


def alimentar_autoridades():
    """Alimentar Autoridades"""
    ruta = Path(AUTORIDADES_CSV)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        sys.exit(1)
    try:
        distrito_nd = Distrito.query.filter_by(clave="ND").one()
        materia_nd = Materia.query.filter_by(clave="ND").one()
        municipio_default = Municipio.query.filter_by(estado_id=5, clave="030").one()  # Coahuila de Zaragoza, Saltillo
    except (MultipleResultsFound, NoResultFound):
        click.echo("AVISO: No se encontró el distrito, materia y/o municipio 'ND'.")
        sys.exit(1)
    click.echo("Alimentando autoridades: ", nl=False)
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            # Si autoridad_id NO es consecutivo, se inserta una autoridad "NO EXISTE"
            contador += 1
            autoridad_id = int(row["autoridad_id"])
            if autoridad_id != contador:
                Autoridad(
                    distrito_id=distrito_nd.id,
                    materia_id=materia_nd.id,
                    municipio_id=municipio_default.id,
                    clave=f"NE-{contador}",
                    descripcion="NO EXISTE",
                    descripcion_corta="NO EXISTE",
                    es_archivo_solicitante=False,
                    es_cemasc=False,
                    es_defensoria=False,
                    es_extinto=False,
                    es_jurisdiccional=False,
                    es_notaria=False,
                    es_organo_especializado=False,
                    es_revisor_escrituras=False,
                    organo_jurisdiccional="NO DEFINIDO",
                    directorio_edictos="",
                    directorio_glosas="",
                    directorio_listas_de_acuerdos="",
                    directorio_sentencias="",
                    audiencia_categoria="NO DEFINIDO",
                    limite_dias_listas_de_acuerdos=0,
                    datawarehouse_id=0,
                    sede="ND",
                    estatus="B",
                ).save()
                click.echo(click.style("!", fg="yellow"), nl=False)
                continue
            distrito_id = int(row["distrito_id"])
            materia_id = int(row["materia_id"])
            municipio_id = int(row["municipio_id"])
            clave = safe_clave(row["clave"])
            descripcion = safe_string(row["descripcion"], save_enie=True)
            descripcion_corta = safe_string(row["descripcion_corta"], save_enie=True)
            es_archivo_solicitante = row["es_archivo_solicitante"] == "1"
            es_cemasc = row["es_archivo_solicitante"] == "1"
            es_defensoria = row["es_archivo_solicitante"] == "1"
            es_extinto = row["es_archivo_solicitante"] == "1"
            es_jurisdiccional = row["es_jurisdiccional"] == "1"
            es_notaria = row["es_notaria"] == "1"
            es_organo_especializado = row["es_organo_especializado"] == "1"
            es_revisor_escrituras = row["es_revisor_escrituras"] == "1"
            organo_jurisdiccional = safe_string(row["organo_jurisdiccional"], save_enie=True)
            directorio_edictos = row["directorio_edictos"]
            directorio_glosas = row["directorio_glosas"]
            directorio_listas_de_acuerdos = row["directorio_listas_de_acuerdos"]
            directorio_sentencias = row["directorio_sentencias"]
            audiencia_categoria = row["audiencia_categoria"]
            limite_dias_listas_de_acuerdos = int(row["limite_dias_listas_de_acuerdos"])
            try:
                datawarehouse_id = int(row["datawarehouse_id"])
            except ValueError:
                datawarehouse_id = 0
            sede = row["sede"]
            estatus = row["estatus"]
            distrito = Distrito.query.get(distrito_id)
            if distrito is None:
                click.echo(click.style(f"  AVISO: distrito_id {distrito_id} no existe", fg="red"))
                sys.exit(1)
            materia = Materia.query.get(materia_id)
            if materia is None:
                click.echo(click.style(f"  AVISO: materia_id {materia_id} no existe", fg="red"))
                sys.exit(1)
            municipio = Municipio.query.get(municipio_id)
            if municipio is None:
                click.echo(click.style(f"  AVISO: municipio_id {municipio_id} no existe", fg="red"))
                sys.exit(1)
            Autoridad(
                distrito=distrito,
                materia=materia,
                municipio=municipio,
                clave=clave,
                descripcion=descripcion,
                descripcion_corta=descripcion_corta,
                es_archivo_solicitante=es_archivo_solicitante,
                es_cemasc=es_cemasc,
                es_defensoria=es_defensoria,
                es_extinto=es_extinto,
                es_jurisdiccional=es_jurisdiccional,
                es_notaria=es_notaria,
                es_organo_especializado=es_organo_especializado,
                es_revisor_escrituras=es_revisor_escrituras,
                organo_jurisdiccional=organo_jurisdiccional,
                directorio_edictos=directorio_edictos,
                directorio_glosas=directorio_glosas,
                directorio_listas_de_acuerdos=directorio_listas_de_acuerdos,
                directorio_sentencias=directorio_sentencias,
                audiencia_categoria=audiencia_categoria,
                limite_dias_listas_de_acuerdos=limite_dias_listas_de_acuerdos,
                datawarehouse_id=datawarehouse_id,
                sede=sede,
                estatus=estatus,
            ).save()
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} autoridades alimentadas.", fg="green"))
