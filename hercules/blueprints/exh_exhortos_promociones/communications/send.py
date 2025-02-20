"""
Communications, Enviar Promocion
"""

import time
from datetime import datetime

import requests

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
    MyNotValidParamError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs
from lib.pwgen import generar_identificador

app = create_app()
app.app_context().push()
database.app = app

TIMEOUT = 60  # segundos


def enviar_promocion(exh_exhorto_promocion_id: int) -> tuple[str, str, str]:
    """Enviar promoción"""
    bitacora.info("Inicia enviar promoción")

    # Consultar la promoción
    exh_exhorto_promocion = ExhExhortoPromocion.query.get(exh_exhorto_promocion_id)

    # Validar que exista la promoción
    if exh_exhorto_promocion is None:
        mensaje_advertencia = f"No existe la promoción con ID {exh_exhorto_promocion_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Validar que su estado sea POR ENVIAR
    if exh_exhorto_promocion.estado != "PENDIENTE":
        mensaje_advertencia = f"La promoción con ID {exh_exhorto_promocion_id} no tiene el estado PENDIENTE"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Consultar el Estado de destino a partir del ID del Municipio en municipio_destino_id
    municipio = Municipio.query.get(exh_exhorto_promocion.exh_exhorto.municipio_destino_id)
    if municipio is None:
        mensaje_advertencia = f"No existe el municipio con ID {exh_exhorto_promocion.exh_exhorto.municipio_destino_id}"
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

    # Si exh_externo no tiene endpoint para enviar promociones
    if exh_externo.endpoint_recibir_promocion is None or exh_externo.endpoint_recibir_promocion == "":
        mensaje_advertencia = f"No tiene endpoint para enviar promociones el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Si exh_externo no tiene endpoint para enviar archivos
    if exh_externo.endpoint_recibir_promocion_archivo is None or exh_externo.endpoint_recibir_promocion_archivo == "":
        mensaje_advertencia = f"No tiene endpoint para enviar archivos de promociones el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

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
        "folioSeguimiento": exh_exhorto_promocion.exh_exhorto.folio_seguimiento,
        "folioOrigenPromocion": exh_exhorto_promocion.folio_origen_promocion,
        "promoventes": promoventes,
        "fojas": int(exh_exhorto_promocion.fojas),
        "fechaOrigen": exh_exhorto_promocion.fecha_origen.strftime("%Y-%m-%d %H:%M:%S"),
        "observaciones": str(exh_exhorto_promocion.observaciones),
        "archivos": archivos,
    }

    # Informar a la bitácora que se va a enviar la promoción
    mensaje = "Pasan las validaciones y comienza el envío de la promoción."
    bitacora.info(mensaje)

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
        raise MyConnectionError(mensaje_advertencia)

    # Terminar si el contenido de la respuesta no es valido
    if not ("success", "message", "errors", "data") in contenido:
        mensaje_advertencia = "Falló la validación de success, message, errors y data"
        bitacora.warning(mensaje_advertencia)
        raise MyConnectionError(mensaje_advertencia)

    # Terminar si success es FALSO
    if contenido["success"] is False:
        mensaje_advertencia = f"Falló el envío del exhorto: {','.join(contenido['errors'])}"
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia)

    # Informar a la bitácora que terminó el envío la promoción
    mensaje = "Termina el envío la promoción."
    bitacora.info(mensaje)

    # Informar a la bitácora que se van a enviar los archivos de la promoción
    mensaje = "Comienza el envío de los archivos de la promoción."
    bitacora.info(mensaje)

    # Generar identificador para el folio de seguimiento
    folio_seguimiento = generar_identificador()

    # Definir los datos que se van a incluir en el envío de los archivos
    payload_for_data = {
        "folioOrigenPromocion": exh_exhorto_promocion.exh_exhorto.exhorto_origen_id,
        "folioSeguimiento": folio_seguimiento,
    }

    # Mandar los archivos del exhorto con multipart/form-data (ETAPA 3)
    data = None
    for archivo in exh_exhorto_promocion.exh_exhortos_promociones_archivos:
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
                url=exh_externo.endpoint_recibir_exhorto_archivo,
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
    mensaje = "Termina el envío de los archivos de la promoción."
    bitacora.info(mensaje)

    # Validar que el ULTIMO data tenga el acuse
    if "acuse" not in data:
        mensaje_advertencia = "Falló porque la respuesta NO tiene acuse"
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia)
    acuse = data["acuse"]
    if data["acuse"] is None:
        mensaje_advertencia = "Falló porque la respuesta NO tiene acuse"
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia)

    # Inicializar listado de errores para acumular fallos si los hubiera
    errores = []

    # Validar que el acuse tenga folioOrigenPromocion
    try:
        folio_origen_promocion = str(acuse["folioOrigenPromocion"])
        bitacora.info("Acuse folioOrigenPromocion: %s", folio_origen_promocion)
    except KeyError:
        errores.append("Faltó folioOrigenPromocion en el acuse")

    # Validar que el acuse tenga folioPromocionRecibida
    try:
        folio_promocion_recibida = str(acuse["folioPromocionRecibida"])
        bitacora.info("Acuse folioPromocionRecibida: %s", folio_promocion_recibida)
    except KeyError:
        errores.append("Faltó folioPromocionRecibida en el acuse")

    # Validar que el acuse tenga fechaHoraRecepcion
    try:
        fecha_hora_recepcion_str = str(acuse["fechaHoraRecepcion"])
        acuse_fecha_hora_recepcion = datetime.strptime(fecha_hora_recepcion_str, "%Y-%m-%d %H:%M:%S")
        bitacora.info("Acuse fechaHoraRecepcion: %s", fecha_hora_recepcion_str)
    except (KeyError, ValueError):
        errores.append("Faltó o es incorrecta fechaHoraRecepcion en el acuse")

    # Terminar si hubo errores
    if len(errores) > 0:
        mensaje_advertencia = ", ".join(errores)
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia)

    # Actualizar el estado a ENVIADO
    exh_exhorto_promocion.estado = "ENVIADO"
    exh_exhorto_promocion.save()

    # Elaborar mensaje final
    mensaje_termino = f"Termina enviar la promoción con ID {exh_exhorto_promocion_id} al PJ externo."
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
