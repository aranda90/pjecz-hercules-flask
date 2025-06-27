"""
Communications, Enviar Respuesta
"""

import os
import time
from datetime import datetime

from dotenv import load_dotenv
import requests
import pytz

from hercules.app import create_app
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos_respuestas.communications import bitacora
from hercules.blueprints.exh_exhortos_respuestas.models import ExhExhortoRespuesta
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.exceptions import (
    MyAnyError,
    MyBucketNotFoundError,
    MyConnectionError,
    MyFileNotFoundError,
    MyNotExistsError,
    MyNotValidAnswerError,
    MyNotValidParamError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs

load_dotenv()
TIMEOUT = int(os.getenv("TIMEOUT", "60"))  # Tiempo de espera de la comunicación con el PJ externo
TZ = os.getenv("TZ", "America/Mexico_City")  # Zona horaria para convertir a tiempo local

app = create_app()
app.app_context().push()
database.app = app


def enviar_respuesta(exh_exhorto_respuesta_id: int) -> tuple[str, str, str]:
    """Enviar respuesta"""
    mensajes = []
    mensaje_info = "Inicia enviar respuesta"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Consultar la respuesta
    exh_exhorto_respuesta = ExhExhortoRespuesta.query.get(exh_exhorto_respuesta_id)

    # Validar que exista la respuesta
    if exh_exhorto_respuesta is None:
        mensaje_error = f"No existe la respuesta con ID {exh_exhorto_respuesta_id}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Validar su estado
    if exh_exhorto_respuesta.estado not in ("POR ENVIAR", "RECHAZADO"):
        mensaje_error = f"La respuesta NO se puede enviar porque su estado es {exh_exhorto_respuesta.estado}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Consultar el estado de ORIGEN a partir de municipio_origen_id, es a quien se le enviará la respuesta
    municipio = exh_exhorto_respuesta.exh_exhorto.municipio_origen  # Es una columna foránea
    estado = municipio.estado

    # Consultar el ExhExterno, tomar el primero porque solo debe haber uno
    exh_externo = ExhExterno.query.filter_by(estado_id=estado.id).first()
    if exh_externo is None:
        mensaje_error = f"No hay datos en exh_externos del estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Si exh_externo no tiene API-key
    if exh_externo.api_key is None or exh_externo.api_key == "":
        mensaje_error = f"No tiene API-key en exh_externos el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Si exh_externo no tiene endpoint para enviar respuestas
    if exh_externo.endpoint_recibir_respuesta_exhorto is None or exh_externo.endpoint_recibir_respuesta_exhorto == "":
        mensaje_error = f"No tiene endpoint para enviar respuestas el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Si exh_externo no tiene endpoint para enviar archivos
    if (
        exh_externo.endpoint_recibir_respuesta_exhorto_archivo is None
        or exh_externo.endpoint_recibir_respuesta_exhorto_archivo == ""
    ):
        mensaje_error = f"No tiene endpoint para enviar archivos de respuestas el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Bucle para juntar los archivos
    archivos = []
    for archivo in exh_exhorto_respuesta.exh_exhortos_respuestas_archivos:
        if archivo.estatus != "A" or archivo.estado == "CANCELADO":
            continue
        archivos.append(
            {
                "nombreArchivo": str(archivo.nombre_archivo),
                "hashSha1": str(archivo.hash_sha1),
                "hashSha256": str(archivo.hash_sha256),
                "tipoDocumento": int(archivo.tipo_documento),
            }
        )

    # Validar que tenga archivos
    if len(archivos) == 0:
        mensaje_error = "No hay archivos en la respuesta"
        bitacora.error(mensaje_error)
        raise MyAnyError(mensaje_error)

    # Bucle para juntar los videos
    videos = []
    for video in exh_exhorto_respuesta.exh_exhortos_respuestas_videos:
        if video.estatus != "A":
            continue
        videos.append(
            {
                "titulo": str(video.titulo),
                "descripcion": str(video.descripcion),
                "fecha": video.fecha.strftime("%Y-%m-%d"),
                "urlAcceso": video.url_acceso,
            }
        )

    # Definir los datos de la respuesta a enviar
    payload_for_json = {
        "exhortoId": exh_exhorto_respuesta.exh_exhorto.exhorto_origen_id,
        "respuestaOrigenId": exh_exhorto_respuesta.respuesta_origen_id,
        "municipioTurnadoId": int(exh_exhorto_respuesta.municipio_turnado_id),
        "areaTurnadoId": exh_exhorto_respuesta.area_turnado_id,  # Puede ser nulo
        "areaTurnadoNombre": exh_exhorto_respuesta.area_turnado_nombre,
        "numeroExhorto": exh_exhorto_respuesta.numero_exhorto,  # Puede ser nulo
        "tipoDiligenciado": exh_exhorto_respuesta.tipo_diligenciado,  # Puede ser nulo, 0, 1, o 2
        "observaciones": exh_exhorto_respuesta.observaciones,  # Puede ser nulo
        "archivos": archivos,
        "videos": videos,
    }

    # Conservar el paquete que se va enviar en la base de datos
    exh_exhorto_respuesta.paquete_enviado = payload_for_json
    exh_exhorto_respuesta.save()

    # Informar a la bitácora que se va a enviar la respuesta
    mensaje_info = "Comienza el envío de la respuesta."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)
    for key, value in payload_for_json.items():
        mensaje_info = f"- {key}: {value}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)

    # Enviar la respuesta
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
        mensaje_advertencia = "No hubo respuesta del servidor al enviar la actualización"
    except requests.exceptions.HTTPError as error:
        mensaje_advertencia = f"Status Code {str(error)} al enviar la actualización"
    except requests.exceptions.RequestException:
        mensaje_advertencia = "Falla desconocida al enviar la actualización"

    # Terminar si hubo mensaje_advertencia
    if mensaje_advertencia != "":
        bitacora.warning(mensaje_advertencia)
        raise MyConnectionError(mensaje_advertencia + "\n" + "\n".join(mensajes))

    # Terminar si NO es correcta estructura de la respuesta
    mensajes_advertencias = []
    if "success" not in contenido or not isinstance(contenido["success"], bool):
        mensajes_advertencias.append("Falta 'success' en la respuesta de la API")
    if "message" not in contenido:
        mensajes_advertencias.append("Falta 'message' en la respuesta de la API")
    if "errors" not in contenido:
        mensajes_advertencias.append("Falta 'errors' en la respuesta de la API")
    if "data" not in contenido:
        mensajes_advertencias.append("Falta 'data' en la respuesta de la API")
    if len(mensajes_advertencias) > 0:
        mensaje_advertencia = ", ".join(mensajes_advertencias)
        bitacora.warning(mensaje_advertencia)
        raise MyNotValidAnswerError(mensaje_advertencia + "\n" + "\n".join(mensajes))
    if contenido["message"]:
        mensaje_info = f"- message: {contenido['message']}"
        bitacora.info(mensaje_info)
        mensajes.append(mensaje_info)

    # Terminar si success es FALSO
    if contenido["success"] is False:
        mensaje_advertencia = f"Falló el envío de la respuesta porque 'success' es falso: {','.join(contenido['errors'])}"
        bitacora.warning(mensaje_advertencia)
        raise MyNotValidAnswerError(mensaje_advertencia + "\n" + "\n".join(mensajes))

    # Informar a la bitácora que terminó el envío de la respuesta
    mensaje_info = "Termina el envío de la respuesta."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Informar a la bitácora que se van a enviar los archivos de la respuesta
    mensaje_info = "Comienza el envío de los archivos de la respuesta."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Definir los datos que se van a incluir en el envío de los archivos
    payload_for_data = {
        "exhortoId": exh_exhorto_respuesta.exh_exhorto.exhorto_origen_id,
        "respuestaOrigenId": exh_exhorto_respuesta.respuesta_origen_id,
    }
    mensaje_info = f"- exhortoId: {payload_for_data['exhortoId']}"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)
    mensaje_info = f"- respuestaOrigenId: {payload_for_data['respuestaOrigenId']}"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Mandar los archivos con multipart/form-data
    data = None
    for archivo in exh_exhorto_respuesta.exh_exhortos_respuestas_archivos:
        # Pausa de 1 segundo entre envios de archivos
        time.sleep(1)
        # Informar al bitácora que se va a enviar el archivo
        mensaje_info = f"Enviando el archivo {archivo.nombre_archivo}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
        # Obtener el contenido del archivo desde GCStorage
        try:
            archivo_contenido = get_file_from_gcs(
                bucket_name=app.config["CLOUD_STORAGE_DEPOSITO"],
                blob_name=get_blob_name_from_url(archivo.url),
            )
        except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
            mensaje_error = f"Falla al tratar de bajar el archivo del storage {str(error)}"
            bitacora.error(mensaje_error)
            raise MyFileNotFoundError(mensaje_error.upper() + "\n" + "\n".join(mensajes))
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
            mensaje_advertencia = "No hubo respuesta del servidor al enviar el archivo"
        except requests.exceptions.HTTPError as error:
            mensaje_advertencia = f"Status Code {str(error)} al enviar el archivo"
        except requests.exceptions.RequestException:
            mensaje_advertencia = "Falla desconocida al enviar el archivo"
        # Terminar si hubo mensaje_advertencia
        if mensaje_advertencia != "":
            bitacora.warning(mensaje_advertencia)
            raise MyAnyError(mensaje_advertencia + "\n" + "\n".join(mensajes))
        # Terminar si NO es correcta estructura de la respuesta
        mensajes_advertencias = []
        if "success" not in contenido or not isinstance(contenido["success"], bool):
            mensajes_advertencias.append("Falta 'success' en la respuesta")
        if "message" not in contenido:
            mensajes_advertencias.append("Falta 'message' en la respuesta")
        if "errors" not in contenido:
            mensajes_advertencias.append("Falta 'errors' en la respuesta")
        if "data" not in contenido:
            mensajes_advertencias.append("Falta 'data' en la respuesta")
        if len(mensajes_advertencias) > 0:
            mensaje_advertencia = ", ".join(mensajes_advertencias)
            bitacora.warning(mensaje_advertencia)
            raise MyNotValidAnswerError(mensaje_advertencia + "\n" + "\n".join(mensajes))
        if contenido["message"]:
            mensaje_info = f"- message: {contenido['message']}"
            bitacora.info(mensaje_info)
            mensajes.append(mensaje_info)
        # Terminar si success es FALSO
        if contenido["success"] is False:
            mensaje_advertencia = f"Falló el envío del archivo porque 'success' es falso: {','.join(contenido['errors'])}"
            bitacora.warning(mensaje_advertencia)
            raise MyNotValidAnswerError(mensaje_advertencia + "\n" + "\n".join(mensajes))
        # Actualizar el archivo de la promoción al estado RECIBIDO
        archivo.estado = "RECIBIDO"
        archivo.save()
        # Tomar el data que llega por enviar el archivo
        data = contenido["data"]

    # Informar a la bitácora que terminó el envío los archivos
    mensaje_info = "Termina el envío de los archivos de la respuesta."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Validar que el ULTIMO data tenga el acuse
    if "acuse" not in data or data["acuse"] is None:
        mensaje_advertencia = "Falló porque la respuesta NO tiene acuse"
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia + "\n" + "\n".join(mensajes))
    acuse = data["acuse"]

    # Conservar el acuse recibido en la base de datos
    exh_exhorto_respuesta.acuse_recibido = acuse
    exh_exhorto_respuesta.save()

    # Inicializar listado de advertencias para acumular fallos en el acuse si los hubiera
    advertencias = []

    # Validar que el acuse tenga exhortoId
    try:
        acuse_exhorto_id = str(acuse["exhortoId"])
        mensaje_info = f"- acuse exhortoId: {acuse_exhorto_id}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        advertencias.append("Faltó exhortoId en el acuse")

    # Validar que el acuse tenga respuestaOrigenId
    try:
        acuse_respuesta_origen_id = str(acuse["respuestaOrigenId"])
        mensaje_info = f"- acuse respuestaOrigenId: {acuse_respuesta_origen_id}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        advertencias.append("Faltó respuestaOrigenId en el acuse")

    # Validar que el acuse tenga fechaHoraRecepcion
    try:
        acuse_fecha_hora_recepcion_str = str(acuse["fechaHoraRecepcion"])
        acuse_fecha_hora_recepcion = datetime.strptime(acuse_fecha_hora_recepcion_str, "%Y-%m-%d %H:%M:%S")
        mensaje_info = f"- acuse fechaHoraRecepcion: {acuse_fecha_hora_recepcion_str}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
        local_tz = pytz.timezone(TZ)
        acuse_fecha_hora_recepcion = acuse_fecha_hora_recepcion.replace(tzinfo=local_tz).astimezone(pytz.utc)
    except (KeyError, ValueError):
        advertencias.append("Faltó o es incorrecta fechaHoraRecepcion en el acuse")

    # Si hubo advertencias
    if len(advertencias) > 0:
        mensaje_advertencia = ", ".join(advertencias)
        bitacora.warning(mensaje_advertencia)
        # raise MyAnyError(mensaje_advertencia + "\n" + "\n".join(mensajes))

    # Actualizar la respuesta con los datos del acuse
    exh_exhorto_respuesta.estado_anterior = exh_exhorto_respuesta.estado
    exh_exhorto_respuesta.estado = "ENVIADO"
    exh_exhorto_respuesta.exh_exhorto.estado = "RESPONDIDO"  # Actualizar el exhorto con el estado RESPONDIDO
    exh_exhorto_respuesta.save()

    # Elaborar mensaje final
    mensaje_termino = f"Termina enviar la respuesta con ID {exh_exhorto_respuesta_id} al PJ externo."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
