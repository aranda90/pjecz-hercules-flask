"""
CLI Ubicaciones Expedientes

- actualizar: Actualizar ubicaciones de expedientes con la información de arc_documentos
- eliminar: Eliminar las ubicaciones de expedientes de una autoridad
"""

import sys

import click

from hercules.app import create_app
from hercules.blueprints.arc_documentos.models import ArcDocumento
from hercules.blueprints.arc_documentos_tipos.models import ArcDocumentoTipo
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.ubicaciones_expedientes.models import UbicacionExpediente
from hercules.extensions import database
from lib.safe_string import safe_clave

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Ubicaciones Expedientes"""


@click.command()
@click.argument("autoridad_clave", type=str)
def actualizar(autoridad_clave):
    """Actualizar ubicaciones de expedientes con la información de arc_documentos"""

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

    # Inicializar contadores
    contador_agregados = 0
    contador_actualizados = 0
    contador_duplicados_eliminados = 0

    # Bucle por cada arc_documento
    for arc_documento in arc_documentos.all():
        # Consultar en ubicaciones de expedientes, con la autoridad dada dicho expediente
        ubicaciones_expedientes = (
            session.query(UbicacionExpediente)
            .filter(UbicacionExpediente.autoridad_id == autoridad.id)
            .filter(UbicacionExpediente.expediente == arc_documento.expediente)
            .filter(UbicacionExpediente.estatus == "A")
            .order_by(UbicacionExpediente.id)
        )

        # Si la ubicación en Archivo es REMESA, entonces en UdE será ARCHIVO
        la_ubicacion = arc_documento.ubicacion
        if la_ubicacion == "REMESA":
            la_ubicacion = "ARCHIVO"

        # Si NO hay ubicaciones de expedientes, crear una nueva
        if ubicaciones_expedientes.count() == 0:
            datos = {
                "autoridad": autoridad,
                "expediente": arc_documento.expediente,
                "ubicacion": la_ubicacion,
            }
            session.add(UbicacionExpediente(**datos))
            contador_agregados += 1
            click.echo(click.style(f"  He agregado {datos['expediente']} a {datos['ubicacion']}", fg="green"))
            continue

        # Si hay más de un resultado, dar de baja los demás
        ubicaciones_expedientes = ubicaciones_expedientes.all()
        ubicacion_expediente = ubicaciones_expedientes[0]
        if len(ubicaciones_expedientes) > 1:
            for ubicacion_expediente in ubicaciones_expedientes[1:]:
                ubicacion_expediente.estatus = "B"
                session.add(ubicacion_expediente)
                contador_duplicados_eliminados += 1
                click.echo(click.style(f"  He eliminado {ubicacion_expediente.expediente} por estar duplicado", fg="red"))

        # Si la ubicación es diferente, actualizar
        if ubicacion_expediente.ubicacion != la_ubicacion:
            ubicacion_expediente.ubicacion = la_ubicacion
            session.add(ubicacion_expediente)
            contador_actualizados += 1
            click.echo(click.style(f"  He actualizado {ubicacion_expediente.expediente} a {la_ubicacion}", fg="yellow"))

    # Guardar los cambios
    session.commit()

    # Mostrar contadores
    click.echo(f"Actualizar ubicaciones de expedientes para {autoridad_clave} ha terminado")
    click.echo(f"  {contador_agregados} agregados")
    click.echo(f"  {contador_actualizados} actualizados")
    click.echo(f"  {contador_duplicados_eliminados} duplicados eliminados")


@click.command()
@click.argument("autoridad_clave", type=str)
def eliminar(autoridad_clave):
    """Eliminar todas las ubicaciones de expedientes de una autoridad"""

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

    # Consultar las ubicaciones de expedientes de la autoridad
    ubicaciones_expedientes = session.query(UbicacionExpediente).filter_by(autoridad=autoridad)

    # Si no hay ubicaciones de expedientes, terminar
    cantidad = ubicaciones_expedientes.count()
    if cantidad == 0:
        click.echo(f"No hay ubicaciones de expedientes para la autoridad {autoridad_clave}")
        sys.exit(1)

    # Eliminar todas las ubicaciones de expedientes de la autoridad
    click.echo(f"Eliminando {cantidad} ubicaciones de expedientes de {autoridad_clave}...")
    ubicaciones_expedientes.delete()
    session.commit()


cli.add_command(actualizar)
cli.add_command(eliminar)
