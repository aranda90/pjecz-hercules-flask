"""
CLI Edictos

- actualizar: Actualizar el estatus de los edictos a partir de un archivo CSV
- exportar: Exportar el ID y el estatus de todos los edictos a un archivo CSV
- refrescar: Refrescar la tabla edictos con los archivos en GCStorage
"""

import csv
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

import click
from dateutil.tz import tzlocal
from dotenv import load_dotenv
from faker import Faker
from google.cloud import storage
from google.cloud.exceptions import NotFound
from hashids import Hashids

from hercules.app import create_app
from hercules.blueprints.autoridades.models import Autoridad
from hercules.blueprints.edictos.models import Edicto
from hercules.blueprints.edictos_acuses.models import EdictoAcuse
from hercules.extensions import database
from lib.safe_string import safe_clave, safe_string

load_dotenv()
SALT = os.environ.get("SALT")
CLOUD_STORAGE_DEPOSITO_EDICTOS = os.environ.get("CLOUD_STORAGE_DEPOSITO_EDICTOS")

app = create_app()
app.app_context().push()
database.app = app


@click.group()
def cli():
    """Edictos"""


@click.command()
@click.argument("archivo_csv", type=click.Path(exists=True))
@click.option("--probar", is_flag=True, help="Probar sin cambiar la BD")
def actualizar(archivo_csv, probar):
    """Actualizar el estatus de los edictos a partir de un archivo CSV"""

    # Leer el archivo CSV y actualizar la base de datos
    contador = 0
    click.echo("Actualizando edictos: ", nl=False)
    with open(archivo_csv, "r", encoding="utf8") as puntero:
        lector = csv.DictReader(puntero)
        for renglon in lector:
            id_valor = int(renglon["id"])
            estatus_valor = renglon["estatus"]
            edicto = Edicto.query.get(id_valor)
            if edicto is None:
                click.echo(click.style("!", fg="red"), nl=False)
                continue
            if edicto.estatus != estatus_valor:
                if estatus_valor == "A":
                    if probar is True:
                        edicto.estatus = estatus_valor
                        edicto.save()
                    contador += 1
                    click.echo(click.style("A", fg="green"), nl=False)
                elif estatus_valor == "B":
                    if probar is True:
                        edicto.estatus = estatus_valor
                        edicto.save()
                    contador += 1
                    click.echo(click.style("B", fg="yellow"), nl=False)
                else:
                    click.echo(click.style("?", fg="red"), nl=False)
                continue
            click.echo(click.style(".", fg="blue"), nl=False)

    # Mensaje final
    click.echo()
    if probar is True:
        click.echo(click.style("Terminó en modo PROBAR: No hay cambios en la base de datos.", fg="white"))
    click.echo(click.style(f"Se actualizaron {contador} edictos", fg="green"))


@click.command()
@click.argument("autoridad_clave", type=str)
@click.option("--cantidad", default=10, type=int, help="Cantidad de edictos a insertar")
def demo_insertar_edictos(autoridad_clave, cantidad):
    """Insertar edictos de demostración"""

    # Consultar la autoridad
    autoridad = Autoridad.query.filter_by(clave=autoridad_clave).first()
    if not autoridad:
        click.echo(click.style(f"No existe la autoridad con clave {autoridad_clave}", fg="red"))
        sys.exit(1)

    # Preparar el Faker
    faker = Faker("es_MX")

    # Insertar los edictos
    click.echo(f"Insertando {cantidad} edictos de demostración para {autoridad_clave}: ", nl=False)
    for i in range(1, cantidad + 1):
        # Preparar la fecha
        fecha = date.today()

        # Preparar la descripción
        descripcion = f"Edicto {faker.sentence()}"

        # Preparar el expediente, con un numero al azar y el año actual
        expediente = f"{faker.random_int(min=1, max=9999)}/{fecha.year}"

        # Preparar el número de publicación
        numero_publicacion = f"1/{fecha.year}"

        # Preparar el archivo
        archivo = f"{fecha.year}-{fecha.month}-{fecha.day}-0001-0001-DESCRIPCION-IDHASED.pdf"

        # Preparar la URL
        url = f"https://storage.googleapis.com/hercules-edictos/autoridad/demo/{archivo}"

        # Insertar el edicto
        tiempo_local = datetime.now(tzlocal())
        edicto = Edicto(
            creado=tiempo_local,
            modificado=tiempo_local,
            autoridad=autoridad,
            fecha=fecha,
            descripcion=descripcion,
            expediente=expediente,
            numero_publicacion=numero_publicacion,
            archivo=archivo,
            url=url,
        )
        edicto.save()
        click.echo(click.style("+", fg="green"), nl=False)

        # Insertar de 1 a 3 republicaciones, con el modelo EdictoAcuse, con fechas siguientes
        fecha_acuse = fecha
        for j in range(1, faker.random_int(min=1, max=3 + 1)):
            fecha_acuse = fecha_acuse + timedelta(days=faker.random_int(min=fecha.day + 1, max=fecha.day + 3))
            EdictoAcuse(
                edicto_id=edicto.id,
                fecha=fecha_acuse,
            ).save()
            click.echo(click.style("-", fg="yellow"), nl=False)

    # Poner avance de linea
    click.echo()

    # Mostrar mensaje final con la cantidad de edictos insertados
    click.echo(click.style(f"Se insertaron {cantidad} edictos de demostración para {autoridad_clave}", fg="green"))


@click.command()
@click.argument("archivo_csv", type=click.Path(exists=False))
def exportar(archivo_csv):
    """Exportar el ID y el estatus de todos los edictos a un archivo CSV"""

    # Consultar TODOS los edictos
    edictos = Edicto.query.order_by(Edicto.id).all()

    # Crear el archivo CSV
    contador = 0
    with open(archivo_csv, mode="w", encoding="utf8") as puntero:
        escritor = csv.DictWriter(puntero, fieldnames=["id", "estatus"])
        escritor.writeheader()
        for edicto in edictos:
            escritor.writerow({"id": edicto.id, "estatus": edicto.estatus})
            contador += 1

    # Mensaje final
    click.echo(click.style(f"Se escribieron {contador} renglones en {archivo_csv}", fg="green"))


@click.command()
@click.option("--clave", default="", type=str, help="Clave de la autoridad")
@click.option("--probar", is_flag=True, help="Probar sin cambiar la BD")
@click.option("--eliminar", is_flag=True, help="CUIDADO: Eliminar (A->B si NO hay archivo en GCS)")
@click.option("--eliminar-recuperar", is_flag=True, help="CUIDADO: Eliminar y recuperar (B->A si hay archivo en GCS)")
def refrescar(clave, probar, eliminar, eliminar_recuperar):
    """Refrescar edictos con los archivos en GCStorage"""

    # Si eliminar_recuperar es verdadero, siempre limpiar será verdadero
    if eliminar_recuperar is True:
        eliminar = True

    # Validar que exista el depósito
    try:
        bucket = storage.Client().get_bucket(CLOUD_STORAGE_DEPOSITO_EDICTOS)
    except NotFound as error:
        click.echo(click.style(f"No existe el depósito {CLOUD_STORAGE_DEPOSITO_EDICTOS}", fg="red"))
        sys.exit(1)

    # Preparar expresión regular para "NO" letras y digitos
    letras_digitos_regex = re.compile("[^0-9a-zA-Z]+")

    # Preparar expresión regular para hashid
    hashid_regexp = re.compile("[0-9a-zA-Z]{8}")

    # Para descifrar los hash ids
    hashids = Hashids(salt=SALT, min_length=8)

    # Para validar la fecha
    anos_limite = 20
    hoy = date.today()
    hoy_dt = datetime(year=hoy.year, month=hoy.month, day=hoy.day)
    limite_dt = datetime(year=hoy.year - anos_limite, month=1, day=1)

    # Inicializar contadores
    contador_incorrectos = 0
    contador_insertados = 0
    contador_presentes = 0
    contador_recuperados = 0
    contador_eliminados = 0

    # Inicializar listado de autoridades
    autoridades = []

    # Si viene la autoridad, validar
    autoridad = None
    if clave != "":
        clave = safe_clave(clave)
        autoridad = Autoridad.query.filter_by(clave=clave).first()
        if not autoridad:
            click.echo(click.style(f"No existe la autoridad con clave {clave}", fg="red"))
            sys.exit(1)
        if autoridad.estatus != "A":
            click.echo(click.style(f"La autoridad con clave {clave} está eliminada", fg="red"))
            sys.exit(1)
        autoridades = [autoridad]

    # Si NO hay filtro por autoridad, consultar TODAS las autoridades jurisdiccionales
    if autoridad is None:
        autoridades = (
            Autoridad.query.filter(Autoridad.es_jurisdiccional == True)
            .filter(Autoridad.estatus == "A")
            .order_by(Autoridad.clave)
            .all()
        )
        if len(autoridades) == 0:
            click.echo(click.style("No hay autoridades jurisdiccionales", fg="red"))
            sys.exit(1)
        click.echo(f"Encontré {len(autoridades)} autoridades jurisdiccionales")

    #
    # Bucle por autoridades
    #
    for autoridad in autoridades:
        # Consultar los edictos (activos e inactivos) de la autoridad
        edictos = Edicto.query.filter(Edicto.autoridad == autoridad).all()

        # Buscar los archivos en el subdirectorio
        subdirectorio = autoridad.directorio_edictos
        if subdirectorio == "":
            click.echo(click.style(f"Se omite {autoridad.clave} porque no tiene subdirectorio para edictos", fg="yellow"))
            continue
        blobs = list(bucket.list_blobs(prefix=subdirectorio))
        archivos_cantidad = len(blobs)
        if archivos_cantidad == 0:
            click.echo(click.style(f"No hay archivos en el subdirectorio {subdirectorio} para insertar", fg="blue"))

        #
        # Bucle por los archivos en el depósito para insertar nuevos edictos
        #
        if archivos_cantidad > 0:
            click.echo(f"Tomando {archivos_cantidad} edictos en el subdirectorio {subdirectorio} para insertar: ", nl=False)
            for blob in blobs:
                # Saltar si no es un archivo PDF
                ruta = Path(blob.name)
                if ruta.suffix.lower() != ".pdf":
                    click.echo(click.style("[Bad pdf]", fg="red"))
                    contador_incorrectos += 1
                    continue

                # Saltar y quitar de la lista de edictos si se encuentra
                esta_en_bd = False
                for indice, edicto in enumerate(edictos):
                    if blob.public_url == edicto.url:
                        edictos.pop(indice)
                        esta_en_bd = True
                        break
                if esta_en_bd:
                    contador_presentes += 1
                    click.echo(click.style(".", fg="blue"), nl=False)
                    continue

                # A partir de aquí tenemos un archivo NUEVO que NO está en la base de datos
                # El nombre del archivo para un edicto debe ser como
                # AAAA-MM-DD-EEEE-EEEE-NUMP-NUMP-DESCRIPCION-BLA-BLA-IDHASED.pdf

                # Separar elementos del nombre del archivo
                nombre_sin_extension = ruta.name[:-4]
                elementos = re.sub(letras_digitos_regex, "-", nombre_sin_extension).strip("-").split("-")

                # Tomar la fecha
                try:
                    ano = int(elementos.pop(0))
                    mes = int(elementos.pop(0))
                    dia = int(elementos.pop(0))
                    fecha = date(ano, mes, dia)
                except (IndexError, ValueError):
                    click.echo(click.style("[Bad date]", fg="red"), nl=False)
                    contador_incorrectos += 1
                    continue

                # Descartar fechas en el futuro o muy en el pasado
                if not limite_dt <= datetime(year=fecha.year, month=fecha.month, day=fecha.day) <= hoy_dt:
                    click.echo(click.style("[Out of range]", fg="red"), nl=False)
                    contador_incorrectos += 1
                    continue

                # Tomar el expediente
                try:
                    numero = int(elementos[0])
                    ano = int(elementos[1])
                    expediente = str(numero) + "/" + str(ano)
                    elementos.pop(0)
                    elementos.pop(0)
                except (IndexError, ValueError):
                    expediente = ""

                # Tomar el número publicación
                try:
                    numero = int(elementos[0])
                    ano = int(elementos[1])
                    numero_publicacion = str(numero) + "/" + str(ano)
                    elementos.pop(0)
                    elementos.pop(0)
                except (IndexError, ValueError):
                    numero_publicacion = ""

                # Tomar la descripción, sin el hash del id de estar presente
                if len(elementos) > 1:
                    if re.match(hashid_regexp, elementos[-1]) is None:
                        descripcion = safe_string(" ".join(elementos))
                    else:
                        decodificado = hashids.decode(elementos[-1])
                        if isinstance(decodificado, tuple) and len(decodificado) > 0:
                            descripcion = safe_string(" ".join(elementos[:-1]))
                        else:
                            descripcion = safe_string(" ".join(elementos))
                else:
                    descripcion = "SIN DESCRIPCION"

                # Insertar EL EDICTO
                if probar is False:
                    tiempo_local = blob.time_created.astimezone(tzlocal())
                    Edicto(
                        creado=tiempo_local,
                        modificado=tiempo_local,
                        autoridad=autoridad,
                        fecha=fecha,
                        descripcion=descripcion,
                        expediente=expediente,
                        numero_publicacion=numero_publicacion,
                        archivo=ruta.name,
                        url=blob.public_url,
                    ).save()
                click.echo(click.style("+", fg="green"), nl=False)
                contador_insertados += 1

            # Poner avance de linea
            click.echo()

        # Si NO hay que limpiar, continuar
        if (eliminar is False) and (eliminar_recuperar is False):
            continue

        # Si NO hay edictos
        if len(edictos) == 0:
            click.echo(click.style(f"No hay edictos de {autoridad.clave} para buscar por URL y cambiar su estatus", fg="blue"))
            continue

        #
        # Bucle por los edictos restantes que se van a buscar por su URL
        #
        click.echo(f"Buscando por URL {len(edictos)} edictos de {autoridad.clave} para cambiar su estatus: ", nl=False)
        for edicto in edictos:
            # Validar el URL
            if edicto.url == "":
                click.echo(click.style("[Empty URL]", fg="yellow"), nl=False)
                contador_incorrectos += 1
                if probar is False:
                    edicto.estatus = "B"
                    edicto.save()
                continue

            # Obtener el archivo en el depósito a partir del URL
            parsed_url = urlparse(edicto.url)
            try:
                blob_name_complete = parsed_url.path[1:]  # Extract path and remove the first slash
                blob_name = "/".join(blob_name_complete.split("/")[1:])  # Remove first directory, it's the bucket name
            except IndexError as error:
                click.echo(click.style("[Bad URL]", fg="yellow"), nl=False)
                if probar is False:
                    edicto.estatus = "B"
                    edicto.save()
                contador_incorrectos += 1
                continue
            blob = bucket.get_blob(unquote(blob_name))  # Get the file

            # Si NO existe el archivo y está en estatus A, se elimina
            if eliminar is True and blob is None and edicto.estatus == "A":
                if probar is False:
                    edicto.estatus = "B"
                    edicto.save()
                click.echo(click.style("B", fg="yellow"), nl=False)
                contador_eliminados += 1
                continue

            # Si SI existe el archivo y está en estatus B, se recupera
            if eliminar_recuperar is True and blob and edicto.estatus == "B":
                if probar is False:
                    edicto.estatus = "A"
                    edicto.save()
                click.echo(click.style("A", fg="green"), nl=False)
                contador_recuperados += 1
                continue

            # No hay que cambiar nada
            click.echo(click.style(".", fg="blue"), nl=False)

        # Poner avance de linea
        click.echo()

    # Mensaje final
    click.echo()
    if probar is True:
        click.echo(click.style("Terminó en modo PROBAR: No hay cambios en la base de datos.", fg="white"))
    if contador_presentes > 0:
        click.echo(click.style(f"Se encontraron {contador_presentes} edictos", fg="green"))
    if contador_insertados > 0:
        click.echo(click.style(f"Se insertaron {contador_insertados} edictos", fg="green"))
    if contador_incorrectos > 0:
        click.echo(click.style(f"Hubo {contador_incorrectos} archivos incorrectos", fg="yellow"))
    if contador_recuperados > 0:
        click.echo(click.style(f"Se recuperaron {contador_recuperados} edictos (estatus cambio a A)", fg="green"))
    if contador_eliminados > 0:
        click.echo(click.style(f"Se eliminaron {contador_eliminados} edictos (estatus cambio a B)", fg="green"))


cli.add_command(actualizar)
cli.add_command(demo_insertar_edictos)
cli.add_command(exportar)
cli.add_command(refrescar)
