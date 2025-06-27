"""
Communications, Enviar Exhorto
"""

import os
import time
from datetime import datetime

from dotenv import load_dotenv
import requests
import pytz

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


def enviar_exhorto(exh_exhorto_id: int) -> tuple[str, str, str]:
    """Enviar exhorto"""
    mensajes = []
    mensaje_info = "Inicia enviar el exhorto al PJ externo."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Consultar el exhorto
    exh_exhorto = ExhExhorto.query.get(exh_exhorto_id)

    # Validar que exista el exhorto
    if exh_exhorto is None:
        mensaje_error = f"No existe el exhorto con ID {exh_exhorto_id}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Validar su estado
    if exh_exhorto.estado not in ("POR ENVIAR", "RECHAZADO"):
        mensaje_error = f"El exhorto NO se puede enviar porque su estado es {exh_exhorto.estado}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Consultar el Estado de DESTINO a partir de municipio_destino_id, porque es a quien se le envía el exhorto
    # La columna municipio_destino_id NO es clave foránea, por eso se tiene que hacer las consultas de esta manera
    municipio = Municipio.query.get(exh_exhorto.municipio_destino_id)
    if municipio is None:
        mensaje_error = f"No existe el municipio con ID {exh_exhorto.municipio_destino_id}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)
    estado = Estado.query.get(municipio.estado_id)
    if estado is None:
        mensaje_error = f"No existe el estado con ID {municipio.estado_id}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

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

    # Si exh_externo no tiene endpoint para enviar exhortos
    if exh_externo.endpoint_recibir_exhorto is None or exh_externo.endpoint_recibir_exhorto == "":
        mensaje_error = f"No tiene endpoint para enviar exhortos el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Si exh_externo no tiene endpoint para enviar archivos
    if exh_externo.endpoint_recibir_exhorto_archivo is None or exh_externo.endpoint_recibir_exhorto_archivo == "":
        mensaje_error = f"No tiene endpoint para enviar archivos el estado {estado.nombre}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Consultar el municipio de municipio_destino_id para enviar su clave INEGI
    municipio_destino = Municipio.query.get(exh_exhorto.municipio_destino_id)
    if municipio_destino is None:
        mensaje_error = f"No existe municipio_destino_id {exh_exhorto.municipio_destino_id}"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Bucle para juntar las partes
    partes = []
    for parte in exh_exhorto.exh_exhortos_partes:
        if parte.estatus != "A":
            continue
        # Genero es opcional, si no es M o F se deja como None
        genero = None
        if parte.genero in ("M", "F"):
            genero = parte.genero
        # Tipo Parte es entero, debe ser 0, 1 o 2
        tipo_parte = 0
        if parte.tipo_parte in (0, 1, 2):
            tipo_parte = parte.tipo_parte
        # Tipo Parte Nombre es opcional, si Tipo Parte es 0 se usa
        tipo_parte_nombre = None
        if tipo_parte == 0:
            tipo_parte_nombre = parte.tipo_parte_nombre
        # Correo electrónico es opcional, si no se tiene se deja como None
        correo_electronico = None
        if parte.correo_electronico is not None and parte.correo_electronico != "":
            correo_electronico = parte.correo_electronico
        # Teléfono es opcional, si no se tiene se deja como None
        telefono = None
        if parte.telefono is not None and parte.telefono != "":
            telefono = parte.telefono
        partes.append(
            {
                "nombre": parte.nombre,
                "apellidoPaterno": parte.apellido_paterno,
                "apellidoMaterno": parte.apellido_materno,
                "genero": genero,
                "esPersonaMoral": parte.es_persona_moral,
                "tipoParte": tipo_parte,
                "tipoParteNombre": tipo_parte_nombre,
                "correoElectronico": correo_electronico,
                "telefono": telefono,
            }
        )

    # Validar que haya al menos una parte
    if len(partes) == 0:
        mensaje_error = "No hay partes en el exhorto"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Bucle para juntar los archivos
    archivos = []
    for archivo in exh_exhorto.exh_exhortos_archivos:
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

    # Validar que haya al menos un archivo
    if len(archivos) == 0:
        mensaje_error = "No hay archivos en el exhorto"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Bucle para juntar los promoventes
    promoventes = []
    for promovente in exh_exhorto.exh_exhortos_promoventes:
        if promovente.estatus != "A":
            continue
        # Genero es opcional, si no es M o F se deja como None
        genero = None
        if promovente.genero in ("M", "F"):
            genero = promovente.genero
        # Tipo Parte es entero, debe ser 0, 1 o 2
        tipo_parte = 0
        if promovente.tipo_parte in (0, 1, 2):
            tipo_parte = promovente.tipo_parte
        # Tipo Parte Nombre es opcional, si Tipo Parte es 0 se usa
        tipo_parte_nombre = None
        if tipo_parte == 0:
            tipo_parte_nombre = promovente.tipo_parte_nombre
        # Correo electrónico es opcional, si no se tiene se deja como None
        correo_electronico = None
        if promovente.correo_electronico is not None and promovente.correo_electronico != "":
            correo_electronico = promovente.correo_electronico
        # Teléfono es opcional, si no se tiene se deja como None
        telefono = None
        if promovente.telefono is not None and promovente.telefono != "":
            telefono = promovente.telefono
        promoventes.append(
            {
                "nombre": promovente.nombre,
                "apellidoPaterno": promovente.apellido_paterno,
                "apellidoMaterno": promovente.apellido_materno,
                "genero": genero,
                "esPersonaMoral": promovente.es_persona_moral,
                "tipoParte": tipo_parte,
                "tipoParteNombre": tipo_parte_nombre,
                "correoElectronico": correo_electronico,
                "telefono": telefono,
            }
        )

    # Validar que haya al menos un promovente
    if len(promoventes) == 0:
        mensaje_error = "No hay promoventes en el exhorto"
        bitacora.error(mensaje_error)
        raise MyNotExistsError(mensaje_error)

    # Cambiar fecha_origen de UTC a tiempo local
    utc_tz = pytz.utc
    local_tz = pytz.timezone(TZ)
    fecha_origen_local = exh_exhorto.fecha_origen.replace(tzinfo=utc_tz).astimezone(local_tz)

    # Definir los datos del exhorto a enviar
    payload_for_json = {
        "exhortoOrigenId": str(exh_exhorto.exhorto_origen_id),
        "municipioDestinoId": int(municipio_destino.clave),
        "materiaClave": str(exh_exhorto.materia_clave),
        "estadoOrigenId": int(exh_exhorto.municipio_origen.estado.clave),
        "municipioOrigenId": int(exh_exhorto.municipio_origen.clave),
        "juzgadoOrigenId": str(exh_exhorto.juzgado_origen_id),
        "juzgadoOrigenNombre": str(exh_exhorto.juzgado_origen_nombre),
        "numeroExpedienteOrigen": str(exh_exhorto.numero_expediente_origen),
        "numeroOficioOrigen": str(exh_exhorto.numero_oficio_origen),
        "tipoJuicioAsuntoDelitos": str(exh_exhorto.tipo_juicio_asunto_delitos),
        "juezExhortante": str(exh_exhorto.juez_exhortante),
        "partes": partes,
        "fojas": int(exh_exhorto.fojas),
        "diasResponder": int(exh_exhorto.dias_responder),
        "tipoDiligenciaId": str(exh_exhorto.tipo_diligencia_id),
        "tipoDiligenciacionNombre": str(exh_exhorto.tipo_diligenciacion_nombre),
        "fechaOrigen": fecha_origen_local.strftime("%Y-%m-%d %H:%M:%S"),
        "observaciones": str(exh_exhorto.observaciones),
        "archivos": archivos,
        "promoventes": promoventes,
    }

    # Conservar el paquete que se va enviar en la base de datos
    exh_exhorto.paquete_enviado = payload_for_json
    exh_exhorto.save()

    # Informar a la bitácora que va a comenzar el envío del exhorto
    mensaje_info = "Comienza el envío del exhorto con los siguientes datos:"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)
    for key, value in payload_for_json.items():
        mensaje_info = f"- {key}: {value}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)

    # Enviar el exhorto
    contenido = None
    mensaje_advertencia = ""
    try:
        respuesta = requests.post(
            url=exh_externo.endpoint_recibir_exhorto,
            headers={"X-Api-Key": exh_externo.api_key},
            timeout=TIMEOUT,
            json=payload_for_json,
        )
        respuesta.raise_for_status()
        contenido = respuesta.json()
    except requests.exceptions.ConnectionError:
        mensaje_advertencia = "No hubo respuesta del servidor al enviar el exhorto"
    except requests.exceptions.HTTPError as error:
        mensaje_advertencia = f"Status Code {str(error)} al enviar el exhorto"
    except requests.exceptions.RequestException:
        mensaje_advertencia = "Falla desconocida al enviar el exhorto"

    # Terminar si hubo mensaje_advertencia
    if mensaje_advertencia != "":
        bitacora.warning(mensaje_advertencia)
        raise MyConnectionError(mensaje_advertencia + "\n" + "\n".join(mensajes))

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
        mensaje_advertencia = f"Falló el envío del exhorto porque 'success' es falso: {','.join(contenido['errors'])}"
        bitacora.warning(mensaje_advertencia)
        raise MyNotValidAnswerError(mensaje_advertencia + "\n" + "\n".join(mensajes))

    # Informar a la bitácora que terminó el envío del exhorto
    mensaje_info = "Termina el envío del exhorto."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Informar a la bitácora que se van a enviar los archivos
    mensaje_info = "Comienza el envío de los archivos."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Definir los datos que se van a incluir en el envío de los archivos
    payload_for_data = {"exhortoOrigenId": str(exh_exhorto.exhorto_origen_id)}
    mensaje_info = f"- exhortoOrigenId: {payload_for_data['exhortoOrigenId']}"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Mandar los archivos del exhorto con multipart/form-data (ETAPA 3)
    data = None
    for archivo in exh_exhorto.exh_exhortos_archivos:
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
        # Actualizar el archivo del exhorto al estado RECIBIDO
        archivo.estado = "RECIBIDO"
        archivo.save()
        # Tomar el data que llega por enviar el archivo
        data = contenido["data"]

    # Informar a la bitácora que terminó el envío los archivos
    mensaje_info = "Termina el envío de los archivos."
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Validar que el ULTIMO data tenga el acuse
    if "acuse" not in data or data["acuse"] is None:
        mensaje_advertencia = "Falló porque la respuesta NO tiene acuse"
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia + "\n" + "\n".join(mensajes))
    acuse = data["acuse"]

    # Conservar el acuse recibido en la base de datos
    exh_exhorto.acuse_recibido = acuse
    exh_exhorto.save()

    # Inicializar listado de advertencias para acumular fallos en el acuse si los hubiera
    advertencias = []

    # Validar que el acuse tenga "exhortoOrigenId"
    try:
        acuse_exhorto_origen_id = str(acuse["exhortoOrigenId"])
        mensaje_info = f"- acuse exhortoOrigenId: {acuse_exhorto_origen_id}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        advertencias.append("Faltó exhortoOrigenId en el acuse")

    # Validar que en acuse tenga "folioSeguimiento"
    try:
        acuse_folio_seguimiento = str(acuse["folioSeguimiento"])
        mensaje_info = f"- acuse folioSeguimiento: {acuse_folio_seguimiento}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        advertencias.append("Faltó folioSeguimiento en el acuse")

    # Validar que en acuse tenga "fechaHoraRecepcion"
    try:
        acuse_fecha_hora_recepcion_str = str(acuse["fechaHoraRecepcion"])
        acuse_fecha_hora_recepcion = datetime.strptime(acuse_fecha_hora_recepcion_str, "%Y-%m-%d %H:%M:%S")
        mensaje_info = f"- acuse fechaHoraRecepcion: {acuse_fecha_hora_recepcion_str}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
        acuse_fecha_hora_recepcion = acuse_fecha_hora_recepcion.replace(tzinfo=local_tz).astimezone(utc_tz)
    except (KeyError, ValueError):
        advertencias.append("Faltó o es incorrecta fechaHoraRecepcion en el acuse")

    # Puede venir "municipioAreaRecibeId" en acuse porque es opcional
    acuse_municipio_area_recibe_id = None
    try:
        acuse_municipio_area_recibe_id = int(acuse["municipioAreaRecibeId"])
        mensaje_info = f"- acuse municipioAreaRecibeId: {acuse_municipio_area_recibe_id}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except (KeyError, ValueError):
        pass

    # Puede venir "areaRecibeId" en acuse porque es opcional
    acuse_area_recibe_id = None
    try:
        acuse_area_recibe_id = str(acuse["areaRecibeId"])
        mensaje_info = f"- acuse areaRecibeId: {acuse_area_recibe_id}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        pass

    # Puede venir "areaRecibeNombre" en acuse porque es opcional
    acuse_area_recibe_nombre = None
    try:
        acuse_area_recibe_nombre = str(acuse["areaRecibeNombre"])
        mensaje_info = f"- acuse areaRecibeNombre: {acuse_area_recibe_nombre}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        pass

    # Puede venir "urlInfo" en acuse porque es opcional
    acuse_url_info = None
    try:
        acuse_url_info = str(acuse["urlInfo"])
        mensaje_info = f"- acuse urlInfo: {acuse_url_info}"
        mensajes.append(mensaje_info)
        bitacora.info(mensaje_info)
    except KeyError:
        pass

    # Si hubo advertencias
    if len(advertencias) > 0:
        mensaje_advertencia = ", ".join(advertencias)
        bitacora.warning(mensaje_advertencia)
        # raise MyAnyError(mensaje_advertencia + "\n" + "\n".join(mensajes))

    # Actualizar el exhorto con los datos del acuse
    exh_exhorto.estado_anterior = exh_exhorto.estado
    exh_exhorto.estado = "RECIBIDO CON EXITO"
    exh_exhorto.folio_seguimiento = acuse_folio_seguimiento
    exh_exhorto.acuse_fecha_hora_recepcion = acuse_fecha_hora_recepcion
    exh_exhorto.acuse_municipio_area_recibe_id = acuse_municipio_area_recibe_id
    exh_exhorto.acuse_area_recibe_id = acuse_area_recibe_id
    exh_exhorto.acuse_area_recibe_nombre = acuse_area_recibe_nombre
    exh_exhorto.acuse_url_info = acuse_url_info
    exh_exhorto.save()

    # Elaborar mensaje final
    mensaje_termino = f"Termina enviar el exhorto con ID {exh_exhorto_id} al PJ externo."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensajes, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
