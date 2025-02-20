"""
Respaldar Usuarios-Roles
"""

import csv
import sys
from pathlib import Path

import click

from hercules.blueprints.usuarios.models import Usuario

USUARIOS_ROLES_CSV = "seed/usuarios_roles.csv"


def respaldar_usuarios_roles():
    """Respaldar Usuarios-Roles"""
    ruta = Path(USUARIOS_ROLES_CSV)
    if ruta.exists():
        click.echo(f"AVISO: {USUARIOS_ROLES_CSV} ya existe, no voy a sobreescribirlo.")
        sys.exit(1)
    click.echo("Respaldando usuarios-roles: ", nl=False)
    contador = 0
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "usuario_id",
                "autoridad_clave",
                "oficina_id",
                "email",
                "nombres",
                "apellido_paterno",
                "apellido_materno",
                "curp",
                "puesto",
                "roles",
                "workspace",
                "estatus",
            ]
        )
        for usuario in Usuario.query.order_by(Usuario.id).all():
            roles_list = []
            for usuario_rol in usuario.usuarios_roles:
                if usuario_rol.estatus == "A":
                    roles_list.append(usuario_rol.rol.nombre)
            respaldo.writerow(
                [
                    usuario.id,
                    usuario.autoridad.clave,
                    usuario.oficina_id,
                    usuario.email,
                    usuario.nombres,
                    usuario.apellido_paterno,
                    usuario.apellido_materno,
                    usuario.curp,
                    usuario.puesto,
                    ",".join(roles_list),
                    usuario.workspace,
                    usuario.estatus,
                ]
            )
            contador += 1
            click.echo(click.style(".", fg="green"), nl=False)
    click.echo()
    click.echo(click.style(f"  {contador} usuarios-roles respaldados.", fg="green"))
