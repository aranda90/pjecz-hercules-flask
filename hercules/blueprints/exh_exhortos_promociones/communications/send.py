"""
Communications, Enviar Promocion
"""

import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

from hercules.app import create_app
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos.communications import bitacora
from hercules.blueprints.exh_exhortos_promociones.models import ExhExhortoPromocion
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

app = create_app()
app.app_context().push()
database.app = app

load_dotenv()
ESTADO_CLAVE = os.getenv("ESTADO_CLAVE", "")

TIMEOUT = 60  # segundos


def enviar_promocion(exh_exhorto_promocion_id: int) -> tuple[str, str, str]:
    """Enviar promoción"""
    mensajes = []
    mensaje_info = "Inicia enviar promoción"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Consultar la promoción
    exh_exhorto_promocion = ExhExhortoPromocion.query.get(exh_exhorto_promocion_id)

    # Validar que exista la promoción
    if exh_exhorto_promocion is None:
        mensaje_error = f"No existe la promoción con ID {exh_exhorto_promocion_id}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Validar que su estado sea POR ENVIAR
    if exh_exhorto_promocion.estado != "PENDIENTE":
        mensaje_error = f"La promoción con ID {exh_exhorto_promocion_id} no tiene el estado PENDIENTE"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Validar que este definida la variable de entorno ESTADO_CLAVE
    if ESTADO_CLAVE == "":
        mensaje_error = "No está definida la variable de entorno ESTADO_CLAVE"
        bitacora.error(mensaje_error)
        raise MyNotValidParamError(mensaje_error)

    # Las promociones pueden ser de ORIGEN a DESTINO o de DESTINO a ORIGEN
    # Por lo hay qu determinar si es de ORIGEN a DESTINO o de DESTINO a ORIGEN
    sentido = "ORIGEN A DESTINO"  # Por defecto, se asume que es de ORIGEN a DESTINO

    # Tomar el estado de ORIGEN a partir de municipio_origen
    municipio = exh_exhorto_promocion.exh_exhorto.municipio_origen  # Es una columna foránea
    estado = municipio.estado
    # Si el estado no es el mismo que el de la clave, entonces es de DESTINO a ORIGEN
    if estado.clave == ESTADO_CLAVE:
        sentido = "DESTINO A ORIGEN"
        # Consultar el Estado de DESTINO a partir de municipio_destino_id, porque es a quien se le envía el exhorto
        # La columna municipio_destino_id NO es clave foránea, por eso se tiene que hacer las consultas de esta manera
        municipio = Municipio.query.get(exh_exhorto_promocion.exh_exhorto.municipio_destino_id)
        if municipio is None:
            mensaje_error = f"No existe el municipio con ID {exh_exhorto_promocion.exh_exhorto.municipio_destino_id}"
            bitacora.error(mensaje_error)
            raise MyNotExistsError(mensaje_error)
        estado = Estado.query.get(municipio.estado_id)
        if estado is None:
            mensaje_error = f"No existe el estado con ID {municipio.estado_id}"
            bitacora.error(mensaje_error)
            raise MyNotExistsError(mensaje_error)

    # Informar a la bitácora el sentido de la promoción
    mensaje_info = f"El sentido de esta promoción es {sentido}."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

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

    # Si exh_externo no tiene endpoint para enviar promociones
    if exh_externo.endpoint_recibir_promocion is None or exh_externo.endpoint_recibir_promocion == "":
        mensaje_error = f"No tiene endpoint para enviar promociones el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Si exh_externo no tiene endpoint para enviar archivos
    if exh_externo.endpoint_recibir_promocion_archivo is None or exh_externo.endpoint_recibir_promocion_archivo == "":
        mensaje_error = f"No tiene endpoint para enviar archivos de promociones el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Bucle para juntar los promoventes
    promoventes = []
    for promovente in exh_exhorto_promocion.exh_exhortos_promociones_promoventes:
        promoventes.append(
            {
                "nombre": str(promovente.nombre),
                "apellidoPaterno": str(promovente.apellido_paterno),
                "apellidoMaterno": str(promovente.apellido_materno),
                "genero": str(promovente.genero),
                "esPersonaMoral": bool(promovente.es_persona_moral),
                "tipoParte": int(promovente.tipo_parte),
                "tipoParteNombre": str(promovente.tipo_parte_nombre),
            }
        )

    # Bucle para juntar los archivos
    archivos = []
    for archivo in exh_exhorto_promocion.exh_exhortos_promociones_archivos:
        archivos.append(
            {
                "nombreArchivo": str(archivo.nombre_archivo),
                "hashSha1": str(archivo.hash_sha1),
                "hashSha256": str(archivo.hash_sha256),
                "tipoDocumento": int(archivo.tipo_documento),
            }
        )

    # Definir los datos de la promoción a enviar
    payload_for_json = {
        "folioSeguimiento": str(exh_exhorto_promocion.exh_exhorto.folio_seguimiento),
        "folioOrigenPromocion": str(exh_exhorto_promocion.folio_origen_promocion),
        "promoventes": promoventes,
        "fojas": int(exh_exhorto_promocion.fojas),
        "fechaOrigen": exh_exhorto_promocion.fecha_origen.strftime("%Y-%m-%d %H:%M:%S"),
        "observaciones": str(exh_exhorto_promocion.observaciones),
        "archivos": archivos,
    }

    # Informar a la bitácora que se va a enviar la promoción
    mensaje_info = "Comienza el envío de la promoción con los siguientes datos:"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)
    for key, value in payload_for_json.items():
        mensaje_info = f"- {key}: {value}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)

    # Enviar la promoción
    contenido = None
    mensaje_advertencia = ""
    try:
        respuesta = requests.post(
            url=exh_externo.endpoint_recibir_promocion,
            headers={"X-Api-Key": exh_externo.api_key},
            timeout=TIMEOUT,
            json=payload_for_json,
        )
        respuesta.raise_for_status()
        contenido = respuesta.json()
    except requests.exceptions.ConnectionError:
        mensaje_advertencia = "No hubo respuesta del servidor al enviar la promoción"
    except requests.exceptions.HTTPError as error:
        mensaje_advertencia = f"Status Code {str(error)} al enviar la promoción"
    except requests.exceptions.RequestException:
        mensaje_advertencia = "Falla desconocida al enviar la promoción"

    # Terminar si hubo mensaje_advertencia
    if mensaje_advertencia != "":
        bitacora.warning(mensaje_advertencia)
        raise MyConnectionError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))

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
        raise MyNotValidAnswerError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))
    if contenido["message"]:
        mensaje_info = f"- message: {contenido['message']}"
        bitacora.info(mensaje_info)
        mensajes.append(mensaje_info)

    # Terminar si success es FALSO
    if contenido["success"] is False:
        mensaje_advertencia = f"Falló el envío de la promoción porque 'success' es falso: {','.join(contenido['errors'])}"
        bitacora.warning(mensaje_advertencia)
        raise MyNotValidAnswerError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))

    # Informar a la bitácora que terminó el envío de la promoción
    mensaje_info = "Termina el envío de la promoción."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Informar a la bitácora que se van a enviar los archivos de la promoción
    mensaje_info = "Comienza el envío de los archivos de la promoción."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Definir los datos que se van a incluir en el envío de los archivos
    payload_for_data = {
        "folioSeguimiento": str(exh_exhorto_promocion.exh_exhorto.folio_seguimiento),
        "folioOrigenPromocion": str(exh_exhorto_promocion.folio_origen_promocion),
    }
    mensaje_info = f"- folioSeguimiento: {payload_for_data['folioSeguimiento']}"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)
    mensaje_info = f"- folioOrigenPromocion: {payload_for_data['folioOrigenPromocion']}"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Mandar los archivos del exhorto con multipart/form-data (ETAPA 3)
    data = None
    for archivo in exh_exhorto_promocion.exh_exhortos_promociones_archivos:
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
                url=exh_externo.endpoint_recibir_promocion_archivo,
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
            raise MyAnyError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))
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
            raise MyNotValidAnswerError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))
        if contenido["message"]:
            mensaje_info = f"- message: {contenido['message']}"
            bitacora.info(mensaje_info)
            mensajes.append(mensaje_info)
        # Terminar si success es FALSO
        if contenido["success"] is False:
            mensaje_advertencia = f"Falló el envío del archivo porque 'success' es falso: {','.join(contenido['errors'])}"
            bitacora.warning(mensaje_advertencia)
            raise MyNotValidAnswerError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))
        # Actualizar el archivo de la promoción al estado RECIBIDO
        archivo.estado = "RECIBIDO"
        archivo.save()
        # Tomar el data que llega por enviar el archivo
        data = contenido["data"]

    # Informar a la bitácora que terminó el envío los archivos
    mensaje_info = "Termina el envío de los archivos de la promoción."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Validar que el ULTIMO data tenga el acuse
    if "acuse" not in data or data["acuse"] is None:
        mensaje_advertencia = "Falló porque la respuesta NO tiene acuse"
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))
    acuse = data["acuse"]

    # Inicializar listado de errores para acumular fallos si los hubiera
    errores = []

    # Validar que el acuse tenga folioOrigenPromocion
    try:
        folio_origen_promocion = str(acuse["folioOrigenPromocion"])
        mensaje_info = f"- acuse folioOrigenPromocion: {folio_origen_promocion}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        errores.append("Faltó folioOrigenPromocion en el acuse")

    # Validar que el acuse tenga folioPromocionRecibida
    try:
        folio_promocion_recibida = str(acuse["folioPromocionRecibida"])
        mensaje_info = f"- acuse folioPromocionRecibida: {folio_promocion_recibida}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        errores.append("Faltó folioPromocionRecibida en el acuse")

    # Validar que el acuse tenga fechaHoraRecepcion
    try:
        fecha_hora_recepcion_str = str(acuse["fechaHoraRecepcion"])
        acuse_fecha_hora_recepcion = datetime.strptime(fecha_hora_recepcion_str, "%Y-%m-%d %H:%M:%S")
        mensaje_info = f"- acuse fechaHoraRecepcion: {fecha_hora_recepcion_str}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except (KeyError, ValueError):
        errores.append("Faltó o es incorrecta fechaHoraRecepcion en el acuse")

    # Terminar si hubo errores
    if len(errores) > 0:
        mensaje_advertencia = ", ".join(errores)
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia.upper() + "\n" + "\n".join(mensajes))

    # Actualizar la promoción con los datos del acuse
    exh_exhorto_promocion.estado = "ENVIADO"
    exh_exhorto_promocion.save()

    # Elaborar mensaje final
    mensaje_termino = f"Termina enviar la promoción con ID {exh_exhorto_promocion_id} al PJ externo."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
