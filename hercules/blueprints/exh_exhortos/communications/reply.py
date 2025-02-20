"""
Communications, Responder Exhorto
"""

import time
from datetime import datetime

import requests

from hercules.app import create_app
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos.communications import bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.exceptions import (
    MyAnyError,
    MyBucketNotFoundError,
    MyConnectionError,
    MyFileNotFoundError,
    MyNotExistsError,
    MyNotValidParamError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs
from lib.pwgen import generar_identificador

app = create_app()
app.app_context().push()
database.app = app

TIMEOUT = 60  # segundos


def responder_exhorto(exh_exhorto_id: int) -> tuple[str, str, str]:
    """Responder exhortos"""
    bitacora.info("Inicia responder exhorto al PJ externo.")

    # Consultar el exhorto
    exh_exhorto = ExhExhorto.query.get(exh_exhorto_id)

    # Validar que exista el exhorto
    if exh_exhorto is None:
        mensaje_advertencia = f"No existe el exhorto con ID {exh_exhorto_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Validar que su estado
    if exh_exhorto.estado not in ("TRANSFERIDO", "PROCESANDO", "DILIGENCIADO"):
        mensaje_advertencia = f"El exhorto con ID {exh_exhorto_id} no tiene el estado TRANSFERIDO, PROCESANDO o DILIGENCIADO"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Consultar el Estado de destino a partir del ID del Municipio en municipio_destino_id
    municipio = Municipio.query.get(exh_exhorto.municipio_destino_id)
    if municipio is None:
        mensaje_advertencia = f"No existe el municipio con ID {exh_exhorto.municipio_destino_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)
    estado = Estado.query.get(municipio.estado_id)
    if estado is None:
        mensaje_advertencia = f"No existe el estado con ID {municipio.estado_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Consultar el ExhExterno con el ID del Estado, tomar el primero porque solo debe haber uno
    exh_externo = ExhExterno.query.filter_by(estado_id=estado.id).first()
    if exh_externo is None:
        mensaje_advertencia = f"No hay datos en exh_externos del estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Si exh_externo no tiene API-key
    if exh_externo.api_key is None or exh_externo.api_key == "":
        mensaje_advertencia = f"No tiene API-key en exh_externos el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Si exh_externo no tiene endpoint para enviar exhortos
    if exh_externo.endpoint_recibir_respuesta_exhorto is None or exh_externo.endpoint_recibir_respuesta_exhorto == "":
        mensaje_advertencia = f"No tiene endpoint para enviar respuestas el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Si exh_externo no tiene endpoint para enviar archivos
    if (
        exh_externo.endpoint_recibir_respuesta_exhorto_archivo is None
        or exh_externo.endpoint_recibir_respuesta_exhorto_archivo == ""
    ):
        mensaje_advertencia = f"No tiene endpoint para enviar archivos de respuestas el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Bucle para juntar los datos de los archivos que SI sean respuesta
    archivos = []
    for archivo in exh_exhorto.exh_exhortos_archivos:
        if archivo.es_respuesta is False:
            continue
        archivos.append(
            {
                "nombreArchivo": str(archivo.nombre_archivo),
                "hashSha1": str(archivo.hash_sha1),
                "hashSha256": str(archivo.hash_sha256),
                "tipoDocumento": int(archivo.tipo_documento),
            }
        )

    # Validar que haya archivos
    if len(archivos) == 0:
        mensaje_advertencia = f"No hay archivos de respuesta en el exhorto con ID {exh_exhorto_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Bucle para juntar los datos de los videos
    videos = []
    for video in exh_exhorto.exh_exhortos_videos:
        videos.append(
            {
                "titulo": str(video.titulo),
                "descripcion": str(video.descripcion),
                "fecha": str(video.fecha.strftime("%Y-%m-%d %H:%M:%S")),
                "urlAcceso": str(video.url_acceso),
            }
        )

    # Si no hay videos, entonces definir videos como None
    if len(videos) == 0:
        videos = None

    # Generar identificador para respuesta_origien_id
    respuesta_origen_id = generar_identificador()

    # Definir los datos de la respuesta del exhorto
    payload_for_json = {
        "exhortoId": str(exh_exhorto.exhorto_origen_id),
        "respuestaOrigenId": respuesta_origen_id,
        "municipioTurnadoId": int(exh_exhorto.respuesta_municipio_turnado_id),
        "areaTurnadoId": str(exh_exhorto.respuesta_area_turnado_id),
        "areaTurnadoNombre": str(exh_exhorto.respuesta_area_turnado_nombre),
        "numeroExhorto": str(exh_exhorto.respuesta_numero_exhorto),
        "tipoDiligenciado": int(exh_exhorto.respuesta_tipo_diligenciado),
        "observaciones": str(exh_exhorto.respuesta_observaciones),
        "archivos": archivos,
        "videos": videos,
    }

    # Informar a la bitácora que se va a responder el exhorto
    mensaje = "Pasan las validaciones y comienza el envío de la respuesta."
    bitacora.info(mensaje)

    # Enviar el exhorto
    contenido = None
    mensaje_advertencia = ""
    try:
        respuesta = requests.post(
            url=exh_externo.endpoint_recibir_respuesta_exhorto,
            headers={"X-Api-Key": exh_externo.api_key},
            timeout=TIMEOUT,
            json=payload_for_json,
        )
        respuesta.raise_for_status()
        contenido = respuesta.json()
    except requests.exceptions.ConnectionError:
        mensaje_advertencia = "No hubo respuesta del servidor al enviar la respuesta"
    except requests.exceptions.HTTPError as error:
        mensaje_advertencia = f"Status Code {str(error)} al enviar la respuesta"
    except requests.exceptions.RequestException:
        mensaje_advertencia = "Falla desconocida al enviar la respuesta"

    # Terminar si hubo mensaje_advertencia
    if mensaje_advertencia != "":
        bitacora.warning(mensaje_advertencia)
        raise MyConnectionError(mensaje_advertencia)

    # Terminar si el contenido de la respuesta no es valido
    if not ("success", "message", "errors", "data") in contenido:
        mensaje_advertencia = "Falló la validación de success, message, errors y data"
        bitacora.warning(mensaje_advertencia)
        raise MyConnectionError(mensaje_advertencia)

    # Terminar si success es FALSO
    if contenido["success"] is False:
        mensaje_advertencia = f"Falló el envío de la respuesta: {','.join(contenido['errors'])}"
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia)

    # Informar a la bitácora que terminó el envío de la respuesta
    mensaje = "Termina el envío de la respuesta."
    bitacora.info(mensaje)

    # Informar a la bitácora que se van a enviar los archivos de la respuesta
    mensaje = "Comienza el envío de los archivos de la respuesta."
    bitacora.info(mensaje)

    # Definir los datos que se van a incluir en el envío de los archivos
    payload_for_data = {
        "exhortoOrigenId": exh_exhorto.exhorto_origen_id,
        "respuestaOrigenId": exh_exhorto.respuesta_origen_id,
    }

    # Mandar los archivos de la respuesta con multipart/form-data (ETAPA 3)
    data = None
    for archivo in exh_exhorto.exh_exhortos_archivos:
        # Si el archivo no es respuesta, entonces continuar
        if archivo.es_respuesta is False:
            continue
        # Informar al bitácora que se va a enviar el archivo
        bitacora.info(f"Enviando el archivo {archivo.nombre_archivo}.")
        # Pausa de 2 segundos entre envios de archivos
        time.sleep(2)
        # Obtener el contenido del archivo desde GCStorage
        try:
            archivo_contenido = get_file_from_gcs(
                bucket_name=app.config["CLOUD_STORAGE_DEPOSITO"],
                blob_name=get_blob_name_from_url(archivo.url),
            )
        except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
            mensaje_error = f"Falla al tratar de bajar el archivo del storage {str(error)}"
            bitacora.error(mensaje_error)
            raise MyFileNotFoundError(mensaje_error)
        # Enviar el archivo
        contenido = None
        mensaje_advertencia = ""
        try:
            respuesta = requests.post(
                url=exh_externo.endpoint_recibir_respuesta_exhorto_archivo,
                headers={"X-Api-Key": exh_externo.api_key},
                timeout=TIMEOUT,
                files={"archivo": (archivo.nombre_archivo, archivo_contenido, "application/pdf")},
                data=payload_for_data,
            )
            respuesta.raise_for_status()
            contenido = respuesta.json()
        except requests.exceptions.ConnectionError:
            mensaje_advertencia = "No hubo respuesta del servidor al enviar el archivo de la respuesta"
        except requests.exceptions.HTTPError as error:
            mensaje_advertencia = f"Status Code {str(error)} al enviar el archivo de la respuesta"
        except requests.exceptions.RequestException:
            mensaje_advertencia = "Falla desconocida al enviar el archivo de la respuesta"
        # Terminar si hubo mensaje_advertencia
        if mensaje_advertencia != "":
            bitacora.warning(mensaje_advertencia)
            raise MyAnyError(mensaje_advertencia)
        # Validar el contenido de la respuesta
        if not ("success", "message", "errors", "data") in contenido:
            mensaje_advertencia = "Falló la validación de success, message, errors y data"
            bitacora.warning(mensaje_advertencia)
            raise MyConnectionError(mensaje_advertencia)
        # Si success es FALSO, mandar a la bitácora el listado de errores y terminar
        if contenido["success"] is False:
            mensaje_advertencia = f"Falló el envío del archivo: {','.join(contenido['errors'])}"
            bitacora.warning(mensaje_advertencia)
            raise MyAnyError(mensaje_advertencia)
        # Tomar el data que llega por enviar el archivo
        data = contenido["data"]

    # Informar a la bitácora que terminó el envío los archivos
    mensaje = "Termina el envío de los archivos."
    bitacora.info(mensaje)

    # Validar que el ULTIMO data tenga el acuse
    if "acuse" not in data or data["acuse"] is None:
        mensaje_advertencia = "Falló porque la respuesta NO tiene acuse"
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia)
    acuse = data["acuse"]

    # Inicializar listado de errores para acumular fallos si los hubiera
    errores = []

    # Validar que el acuse tenga "exhortoOrigenId"
    try:
        acuse_exhorto_origen_id = str(acuse["exhortoOrigenId"])
        bitacora.info("Acuse exhortoOrigenId: %s", acuse_exhorto_origen_id)
    except KeyError:
        errores.append("Faltó exhortoOrigenId en el acuse")

    # Validar que el acuse tenga "respuestaOrigenId"
    try:
        acuse_respuesta_origen_id = str(acuse["respuestaOrigenId"])
        bitacora.info("Acuse respuestaOrigenId: %s", acuse_respuesta_origen_id)
    except KeyError:
        errores.append("Faltó respuestaOrigenId en el acuse")

    # Validar que el acuse tenga "fechaHoraRecepcion"
    try:
        acuse_fecha_hora_recepcion_str = str(acuse["fechaHoraRecepcion"])
        acuse_fecha_hora_recepcion = datetime.strptime(acuse_fecha_hora_recepcion_str, "%Y-%m-%d %H:%M:%S")
        bitacora.info("Acuse fechaHoraRecepcion: %s", acuse_fecha_hora_recepcion_str)
    except (KeyError, ValueError):
        errores.append("Faltó o es incorrecta fechaHoraRecepcion en el acuse")

    # Terminar si hubo errores
    if len(errores) > 0:
        mensaje_advertencia = ", ".join(errores)
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia)

    # Actualizar el estado a CONTESTADO
    exh_exhorto.estado = "CONTESTADO"
    exh_exhorto.save()

    # Elaborar mensaje_termino
    mensaje_termino = f"Termina responder exhorto con ID {exh_exhorto_id} al PJ externo."
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
