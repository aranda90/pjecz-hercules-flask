"""
CLI Soportes_Tickets

- reporte: Reporte de tickets atendidos y cerrados a un archivo CSV
"""

import sys
import re
import csv
import calendar
from datetime import datetime, timedelta
from pathlib import Path

import click

from sqlalchemy import or_

from hercules.app import create_app
from hercules.blueprints.soportes_tickets.models import SoporteTicket
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.funcionarios.models import Funcionario
from hercules.extensions import database

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Soportes_Tickets"""


@click.command()
@click.argument("anio_mes", type=str)
@click.option("--output", default="reporte_soportes_tickets.csv", type=str, help="Archivo CSV a escribir")
def generar_sicgd_csv(anio_mes, output):
    """Generar CSV para SICGD Soporte Tickets en el Sistema de Plataforma Web"""
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
    # Consultar tickets
    click.echo("Elaborando reporte de tickets...")
    contador = 0
    soportes_tickets = SoporteTicket.query
    if desde:
        soportes_tickets = soportes_tickets.filter(SoporteTicket.creado >= f"{desde} 00:00:00")
    if hasta:
        soportes_tickets = soportes_tickets.filter(SoporteTicket.creado <= f"{hasta} 23:59:59")
    soportes_tickets = soportes_tickets.filter(or_(SoporteTicket.estado == "TERMINADO", SoporteTicket.estado == "CERRADO"))
    # joins con tablas foraneas
    soportes_tickets = soportes_tickets.join(Usuario)
    soportes_tickets = soportes_tickets.join(Funcionario)
    soportes_tickets = soportes_tickets.order_by(SoporteTicket.creado).all()
    with open(ruta, "w", encoding="utf8") as puntero:
        respaldo = csv.writer(puntero)
        respaldo.writerow(
            [
                "Fecha",
                "Fecha de respuesta",
                "Usuario",
                "Soporte Técnico",
                "Descripción",
                "Solución",
                "Estado",
            ]
        )
        for soporte_ticket in soportes_tickets:
            # Recortar líneas largas
            descripcion = soporte_ticket.descripcion.replace("\n", " ")
            soluciones = soporte_ticket.soluciones.replace("\n", " ")
            if len(descripcion) > 32:
                descripcion = descripcion[0:32] + "..."
            if len(soluciones) > 32:
                soluciones = soluciones[0:32] + "..."
            # Escribir la linea
            respaldo.writerow(
                [
                    soporte_ticket.creado.strftime("%Y-%m-%d %H:%M:%S"),
                    soporte_ticket.resolucion.strftime("%Y-%m-%d %H:%M:%S"),
                    soporte_ticket.usuario.nombre,
                    soporte_ticket.funcionario.nombre,
                    descripcion,
                    soluciones,
                    soporte_ticket.estado,
                ]
            )
            contador += 1
            if contador % 100 == 0:
                click.echo(f"  Van {contador}...")
    click.echo(f"  {contador} en {ruta.name}")


cli.add_command(generar_sicgd_csv)
