"""
CLI Inv Equipos
"""

import sys

import click

from hercules.blueprints.inv_equipos.tasks import exportar_reporte_xlsx as exportar_reporte_xlsx_task


@click.group()
def cli():
    """Inv Equipos"""


@click.command()
@click.argument("tipo", type=str)
def exportar_reporte_xlsx(tipo: str):
    """Exportar reporte XLSX de equipos por tipo"""

    # Ejecutar la tarea
    try:
        mensaje_termino, _, _ = exportar_reporte_xlsx_task(tipo)
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mostrar mensaje de termino
    click.echo(click.style(mensaje_termino, fg="green"))


cli.add_command(exportar_reporte_xlsx)
