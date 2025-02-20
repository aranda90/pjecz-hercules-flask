"""
Alimentar Usuarios
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

import click
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.oficinas.models import Oficina
from hercules.blueprints.usuarios.models import Usuario
from hercules.extensions import pwd_context
from lib.pwgen import generar_contrasena
from lib.safe_string import safe_clave, safe_email, safe_string

USUARIOS_CSV = "seed/usuarios_roles.csv"


def alimentar_usuarios():
    """Alimentar Usuarios"""
    ruta = Path(USUARIOS_CSV)
    if not ruta.exists():
        click.echo(f"AVISO: {ruta.name} no se encontró.")
        sys.exit(1)
    if not ruta.is_file():
        click.echo(f"AVISO: {ruta.name} no es un archivo.")
        sys.exit(1)
    try:
        autoridad_nd = Autoridad.query.filter_by(clave="ND").one()
        oficina_nd = Oficina.query.filter_by(clave="ND").one()
    except (MultipleResultsFound, NoResultFound):
        click.echo("AVISO: No se encontró la autoridad y/o oficina 'ND'.")
        sys.exit(1)
    click.echo("Alimentando usuarios: ", nl=False)
    contador = 0
    with open(ruta, encoding="utf8") as puntero:
        rows = csv.DictReader(puntero)
        for row in rows:
            # Si usuario_id NO es consecutivo, se inserta un usuario "NO EXISTE"
            while True:
                contador += 1
                usuario_id = int(row["usuario_id"])
                if usuario_id == contador:
                    break
                Usuario(
                    autoridad_id=autoridad_nd.id,
                    oficina_id=oficina_nd.id,
                    email=f"no-existe-{contador}@server.com",
                    nombres="NO EXISTE",
                    apellido_paterno="",
                    apellido_materno="",
                    curp="",
                    puesto="",
                    workspace="EXTERNO",
                    estatus="B",
                    api_key="",
                    api_key_expiracion=datetime(year=2000, month=1, day=1),
                    contrasena=pwd_context.hash(generar_contrasena()),
                ).save()
                click.echo(click.style("0", fg="blue"), nl=False)
            autoridad_clave = safe_clave(row["autoridad_clave"])
            oficina_id = int(row["oficina_id"])
            email = safe_email(row["email"])
            nombres = safe_string(row["nombres"], save_enie=True)
            apellido_paterno = safe_string(row["apellido_paterno"], save_enie=True)
            apellido_materno = safe_string(row["apellido_materno"], save_enie=True)
            curp = safe_string(row["curp"])
            puesto = safe_string(row["puesto"], save_enie=True)
            workspace = safe_string(row["workspace"])
            estatus = row["estatus"]
            autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
            if autoridad is None:
                click.echo(click.style(f"  AVISO: autoridad_clave {autoridad_clave} no existe", fg="red"))
                sys.exit(1)
            oficina = Oficina.query.get(oficina_id)
            if oficina is None:
                click.echo(click.style(f"  AVISO: oficina_id {oficina_id} no existe", fg="red"))
                sys.exit(1)
            Usuario(
                autoridad=autoridad,
                oficina=oficina,
                email=email,
                nombres=nombres,
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno,
                curp=curp,
                puesto=puesto,
                workspace=workspace,
                estatus=estatus,
                api_key="",
                api_key_expiracion=datetime(year=2000, month=1, day=1),
                contrasena=pwd_context.hash(generar_contrasena()),
            ).save()
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} usuarios alimentados.", fg="green"))
