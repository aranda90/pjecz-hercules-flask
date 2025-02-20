"""
Exh Exhortos Demo 02 Enviar

Esta es una demostración que va a insertar datos aleatorios en la base de datos para probar la interfaz de usuario.
"""

import random
import sys
from datetime import datetime

import click

from hercules.app import create_app
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.pwgen import generar_identificador

app = create_app()
app.app_context().push()
database.app = app

ARCHIVO_PRUEBA_PDF = "prueba-1.pdf"
ARCHIVO_PRUEBA_PDF_HASHSHA1 = "3a9a09bbb22a6da576b2868c4b861cae6b096050"
ARCHIVO_PRUEBA_PDF_HASHSHA256 = "df3d983d24a5002e7dcbff1629e25f45bb3def406682642643efc4c1c8950a77"
ESTADO_ORIGEN_ID = 5  # Coahuila de Zaragoza


def demo_enviar_exhorto(exhorto_origen_id: str) -> str:
    """Enviar un exhorto PENDIENTE o POR ENVIAR"""

    # Consultar el exhorto con el exhorto_origen_id
    exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).first()
    if exh_exhorto is None:
        click.echo(click.style(f"No existe el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Validar que el exhorto esté en estado "PENDIENTE" o "POR ENVIAR"
    if exh_exhorto.estado not in ("PENDIENTE", "POR ENVIAR"):
        click.echo(click.style(f"El exhorto {exhorto_origen_id} no está en estado PENDIENTE o POR ENVIAR", fg="red"))
        sys.exit(1)

    # Preparar el listado de partes
    partes = []
    for exh_exhorto_parte in exh_exhorto.exh_exhortos_partes:
        if exh_exhorto_parte.estatus == "A":
            partes.append(
                {
                    "nombre": exh_exhorto_parte.nombre,
                    "apellidoPaterno": exh_exhorto_parte.apellido_paterno,
                    "apellidoMaterno": exh_exhorto_parte.apellido_materno,
                    "genero": exh_exhorto_parte.genero,
                    "esPersonaMoral": exh_exhorto_parte.es_persona_moral,
                    "tipoParte": exh_exhorto_parte.tipo_parte,
                    "tipoParteNombre": exh_exhorto_parte.tipo_parte_nombre,
                }
            )

    # Validar que haya partes
    if len(partes) == 0:
        click.echo(click.style(f"No hay partes en el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Preparar el listado de archivos
    archivos = []
    for exh_exhorto_archivo in exh_exhorto.exh_exhortos_archivos:
        archivo = {
            "nombreArchivo": exh_exhorto_archivo.nombre_archivo,
            "hashSha1": exh_exhorto_archivo.hash_sha1,
            "hashSha256": exh_exhorto_archivo.hash_sha256,
            "tipoDocumento": exh_exhorto_archivo.tipo_documento,
        }
        archivos.append(archivo)

    # Validar que haya archivos
    if len(archivos) == 0:
        click.echo(click.style(f"No hay archivos en el exhorto {exhorto_origen_id}", fg="red"))
        sys.exit(1)

    # Consultar el municipio de destino porque municipio_destino_id es el ID de nuestra tabla municipios
    municipio_destino = Municipio.query.get(exh_exhorto.municipio_destino_id)

    # Preparar lo que se va a enviar
    datos = {
        "exhortoOrigenId": exh_exhorto.exhorto_origen_id,
        "municipioDestinoId": int(municipio_destino.clave),
        "materiaClave": exh_exhorto.materia_clave,
        "estadoOrigenId": int(ESTADO_ORIGEN_ID),
        "municipioOrigenId": int(exh_exhorto.municipio_origen.clave),
        "juzgadoOrigenId": exh_exhorto.juzgado_origen_id,
        "juzgadoOrigenNombre": exh_exhorto.juzgado_origen_nombre,
        "numeroExpedienteOrigen": exh_exhorto.numero_expediente_origen,
        "numeroOficioOrigen": exh_exhorto.numero_oficio_origen,
        "tipoJuicioAsuntoDelitos": exh_exhorto.tipo_juicio_asunto_delitos,
        "juezExhortante": exh_exhorto.juez_exhortante,
        "fojas": int(exh_exhorto.fojas),
        "diasResponder": int(exh_exhorto.dias_responder),
        "tipoDiligenciacionNombre": exh_exhorto.tipo_diligenciacion_nombre,
        "fechaOrigen": exh_exhorto.fecha_origen,
        "observaciones": exh_exhorto.observaciones,
    }

    # Mostrar lo que se va a enviar
    click.echo(click.style("Los datos del exhorto a enviar son...", fg="white"))
    click.echo(click.style(f"  exhortoOrigenId:          {datos['exhortoOrigenId']}", fg="green"))
    click.echo(click.style(f"  municipioDestinoId:       {datos['municipioDestinoId']}", fg="green"))
    click.echo(click.style(f"  materiaClave:             {datos['materiaClave']}", fg="green"))
    click.echo(click.style(f"  estadoOrigenId:           {datos['estadoOrigenId']}", fg="green"))
    click.echo(click.style(f"  municipioOrigenId:        {datos['municipioOrigenId']}", fg="green"))
    click.echo(click.style(f"  juzgadoOrigenId:          {datos['juzgadoOrigenId']}", fg="green"))
    click.echo(click.style(f"  juzgadoOrigenNombre:      {datos['juzgadoOrigenNombre']}", fg="green"))
    click.echo(click.style(f"  numeroExpedienteOrigen:   {datos['numeroExpedienteOrigen']}", fg="green"))
    click.echo(click.style(f"  numeroOficioOrigen:       {datos['numeroOficioOrigen']}", fg="green"))
    click.echo(click.style(f"  tipoJuicioAsuntoDelitos:  {datos['tipoJuicioAsuntoDelitos']}", fg="green"))
    click.echo(click.style(f"  juezExhortante:           {datos['juezExhortante']}", fg="green"))
    click.echo(click.style(f"  fojas:                    {datos['fojas']}", fg="green"))
    click.echo(click.style(f"  diasResponder:            {datos['diasResponder']}", fg="green"))
    click.echo(click.style(f"  tipoDiligenciacionNombre: {datos['tipoDiligenciacionNombre']}", fg="green"))
    click.echo(click.style(f"  fechaOrigen:              {datos['fechaOrigen']}", fg="green"))
    click.echo(click.style(f"  observaciones:            {datos['observaciones']}", fg="green"))

    # Mostrar las partes que se van a enviar
    click.echo(click.style("Las partes son...", fg="white"))
    for parte in partes:
        click.echo(click.style("Parte", fg="blue"))
        click.echo(click.style(f"  nombre:           {parte['nombre']}", fg="green"))
        click.echo(click.style(f"  apellidoPaterno:  {parte['apellidoPaterno']}", fg="green"))
        click.echo(click.style(f"  apellidoMaterno:  {parte['apellidoMaterno']}", fg="green"))
        click.echo(click.style(f"  genero:           {parte['genero']}", fg="green"))
        click.echo(click.style(f"  esPersonaMoral:   {parte['esPersonaMoral']}", fg="green"))
        click.echo(click.style(f"  tipoParte:        {parte['tipoParte']}", fg="green"))
        click.echo(click.style(f"  tipoParteNombre:  {parte['tipoParteNombre']}", fg="green"))

    # Mostrar los archivos que se van a enviar
    click.echo(click.style("Los archivos son...", fg="white"))
    for archivo in archivos:
        click.echo(click.style("Archivo", fg="blue"))
        click.echo(click.style(f"  nombreArchivo: {archivo['nombreArchivo']}", fg="green"))
        click.echo(click.style(f"  hashSha1:      {archivo['hashSha1']}", fg="green"))
        click.echo(click.style(f"  hashSha256:    {archivo['hashSha256']}", fg="green"))
        click.echo(click.style(f"  tipoDocumento: {archivo['tipoDocumento']}", fg="green"))

    # Esperar a que se presione ENTER para continuar
    input("Presiona ENTER para DEMOSTRAR que se va a enviar este exhorto...")

    # Elegir OTRO municipio al azar del estado de destino
    municipios_destinos = Municipio.query.filter_by(estado_id=municipio_destino.estado_id).all()
    nuevo_municipio_destino = random.choice(municipios_destinos)

    # Preparar los datos hipotéticos que se van a recibir como acuse
    acuse = {
        "exhortoOrigenId": exh_exhorto.exhorto_origen_id,
        "folioSeguimiento": generar_identificador(),
        "fechaHoraRecepcion": datetime.now(),
        "municipioAreaRecibeId": int(nuevo_municipio_destino.clave),
        "areaRecibeId": "ID-AREA-DEMO",
        "areaRecibeNombre": "NOMBRE DEL AREA QUE RECIBE",
        "urlInfo": f"https://fake.info/acuse/{exh_exhorto.exhorto_origen_id}",
    }

    # Mostrar el acuse recibido
    click.echo(click.style("He simulado que llegan estos datos como acuse...", fg="white"))
    click.echo(click.style(f"  exhortoOrigenId:       {acuse['exhortoOrigenId']}", fg="green"))
    click.echo(click.style(f"  folioSeguimiento:      {acuse['folioSeguimiento']}", fg="green"))
    click.echo(click.style(f"  fechaHoraRecepcion:    {acuse['fechaHoraRecepcion']}", fg="green"))
    click.echo(click.style(f"  municipioAreaRecibeId: {acuse['municipioAreaRecibeId']}", fg="green"))
    click.echo(click.style(f"  areaRecibeId:          {acuse['areaRecibeId']}", fg="green"))
    click.echo(click.style(f"  areaRecibeNombre:      {acuse['areaRecibeNombre']}", fg="green"))
    click.echo(click.style(f"  urlInfo:               {acuse['urlInfo']}", fg="green"))

    # Actualizar el exhorto con los datos del acuse
    click.echo(click.style("Actualizando el exhorto...", fg="yellow"))
    exh_exhorto.folio_seguimiento = acuse["folioSeguimiento"]
    exh_exhorto.acuse_fecha_hora_recepcion = acuse["fechaHoraRecepcion"]
    exh_exhorto.acuse_municipio_area_recibe_id = acuse["municipioAreaRecibeId"]
    exh_exhorto.acuse_area_recibe_id = acuse["areaRecibeId"]
    exh_exhorto.acuse_area_recibe_nombre = acuse["areaRecibeNombre"]
    exh_exhorto.acuse_url_info = acuse["urlInfo"]

    # Actualizar el exhorto con el estado "RECIBIDO CON EXITO"
    exh_exhorto.estado = "RECIBIDO CON EXITO"
    exh_exhorto.save()

    # Entregar mensaje final
    return f"DEMO Terminó enviar el exhorto {exhorto_origen_id}"
