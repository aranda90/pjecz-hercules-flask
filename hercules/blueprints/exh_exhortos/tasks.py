"""
Exh Exhortos, tareas en el fondo
"""

import logging
import time
from datetime import datetime, timedelta

import requests

from hercules.app import create_app
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.exceptions import (
    MyAnyError,
    MyBucketNotFoundError,
    MyEmptyError,
    MyFileNotFoundError,
    MyNotExistsError,
    MyNotValidParamError,
)
from lib.google_cloud_storage import get_blob_name_from_url, get_file_from_gcs
from lib.tasks import set_task_error, set_task_progress

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/exh_exhortos.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app

CANTIDAD_MAXIMA_INTENTOS = 3
SEGUNDOS_ESPERA_ENTRE_INTENTOS = 60  # 1 minuto
TIMEOUT = 30  # 30 segundos


def consultar(exh_exhorto_id: int) -> tuple[str, str, str]:
    """Consultar exhortos"""
    bitacora.info("Inicia consultar")

    # Elaborar mensaje_termino
    mensaje_termino = "Termina consultar"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""


def lanzar_consultar(exh_exhorto_id):
    """Lanzar tarea en el fondo para consultar exhortos"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado exh_exhortos.consultar")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = consultar(exh_exhorto_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino


def enviar(exhorto_origen_id: str = "") -> tuple[str, str, str]:
    """Enviar exhortos"""
    bitacora.info("Inicia enviar")

    # Inicializar el listado de exhortos a enviar
    exh_exhortos = []

    # Si no se proporciona el exhorto_origen_id
    if exhorto_origen_id == "":
        # Consultar todos los exhortos con estado POR ENVIAR
        exh_exhortos = ExhExhorto.query.filter_by(estado="POR ENVIAR").filter_by(estatus="A").all()
    else:
        # Consultar el exhorto con exhorto_origen_id
        exh_exhorto = ExhExhorto.query.filter_by(exhorto_origen_id=exhorto_origen_id).filter_by(estatus="A").first()
        if exh_exhorto is None:
            mensaje_advertencia = f"No existe el exhorto con ID {exhorto_origen_id}"
            bitacora.warning(mensaje_advertencia)
            raise MyNotExistsError(mensaje_advertencia)
        if exh_exhorto.estado != "POR ENVIAR":
            mensaje_advertencia = f"El exhorto con ID {exhorto_origen_id} no está en estado POR ENVIAR"
            bitacora.warning(mensaje_advertencia)
            raise MyNotExistsError(mensaje_advertencia)
        exh_exhortos.append(exh_exhorto)

    # Validar que haya exhortos POR ENVIAR
    if len(exh_exhortos) == 0:
        mensaje_advertencia = "AVISO: No hay exhortos por enviar"
        bitacora.warning(mensaje_advertencia)
        raise MyEmptyError(mensaje_advertencia)

    # Obtener el tiempo actual
    tiempo_actual = datetime.now()

    # Inicializar listado de mensajes de termino
    mensajes_termino = []

    # Bucle de exhortos POR ENVIAR
    exhortos_omitidos_contador = 0
    exhortos_procesados_contador = 0
    for exh_exhorto in exh_exhortos:
        # Si por_enviar_tiempo_anterior mas SEGUNDOS_ESPERA_ENTRE_INTENTOS es mayor al tiempo actual, entonces se omite
        if (
            exh_exhorto.por_enviar_tiempo_anterior is not None
            and tiempo_actual < exh_exhorto.por_enviar_tiempo_anterior + timedelta(seconds=SEGUNDOS_ESPERA_ENTRE_INTENTOS)
        ):
            mensaje_advertencia = f"Se omite el exhorto {exh_exhorto.exhorto_origen_id} por tiempo de espera"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            exhortos_omitidos_contador += 1
            continue  # Pasar al siguiente exhorto

        # Informar al loggin que se va a enviar el exhorto
        mensaje = f"Enviando el exhorto {exh_exhorto.exhorto_origen_id}..."
        mensajes_termino.append(mensaje)
        bitacora.info(mensaje)

        # Consultar el Estado de destino a partir del ID del Municipio en municipio_destino_id
        municipio = Municipio.query.get(exh_exhorto.municipio_destino_id)
        if municipio is None:
            mensaje_advertencia = f"No existe el municipio con ID {exh_exhorto.municipio_destino_id}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto
        estado = Estado.query.get(municipio.estado_id)
        if estado is None:
            mensaje_advertencia = f"No existe el estado con ID {municipio.estado_id}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto

        # Consultar el ExhExterno con el ID del Estado, tomar el primero porque solo debe haber uno
        exh_externo = ExhExterno.query.filter_by(estado_id=estado.id).first()
        if exh_externo is None:
            mensaje_advertencia = f"No hay datos en exh_externos del estado {estado.nombre}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto

        # Si exh_externo no tiene API-key
        if exh_externo.api_key is None or exh_externo.api_key == "":
            mensaje_advertencia = f"No tiene API-key en exh_externos el estado {estado.nombre}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto

        # Si exh_externo no tiene endpoint para enviar exhortos
        if exh_externo.endpoint_recibir_exhorto is None or exh_externo.endpoint_recibir_exhorto == "":
            mensaje_advertencia = f"No tiene endpoint para enviar exhortos el estado {estado.nombre}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto

        # Si exh_externo no tiene endpoint para enviar archivos
        if exh_externo.endpoint_recibir_exhorto_archivo is None or exh_externo.endpoint_recibir_exhorto_archivo == "":
            mensaje_advertencia = f"No tiene endpoint para enviar archivos el estado {estado.nombre}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto

        # Consultar el municipio de municipio_destino_id para enviar su clave INEGI
        municipio_destino = Municipio.query.get(exh_exhorto.municipio_destino_id)
        if municipio_destino is None:
            mensaje_advertencia = f"No existe municipio_destino_id {exh_exhorto.municipio_destino_id}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto

        # Bucle para juntar los datos de las partes
        partes = []
        for exh_exhorto_parte in exh_exhorto.exh_exhortos_partes:
            partes.append(
                {
                    "nombre": str(exh_exhorto_parte.nombre),
                    "apellidoPaterno": str(exh_exhorto_parte.apellido_paterno),
                    "apellidoMaterno": str(exh_exhorto_parte.apellido_materno),
                    "genero": str(exh_exhorto_parte.genero),
                    "esPersonaMoral": bool(exh_exhorto_parte.es_persona_moral),
                    "tipoParte": int(exh_exhorto_parte.tipo_parte),
                    "tipoParteNombre": str(exh_exhorto_parte.tipo_parte_nombre),
                }
            )

        # Bucle para juntar los datos de los archivos exh_exhortos_archivos
        archivos = []
        for exh_exhorto_archivo in exh_exhorto.exh_exhortos_archivos:
            archivos.append(
                {
                    "nombreArchivo": str(exh_exhorto_archivo.nombre_archivo),
                    "hashSha1": str(exh_exhorto_archivo.hash_sha1),
                    "hashSha256": str(exh_exhorto_archivo.hash_sha256),
                    "tipoDocumento": int(exh_exhorto_archivo.tipo_documento),
                }
            )

        # Definir los datos del exhorto
        datos_exhorto = {
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
            "tipoDiligenciacionNombre": str(exh_exhorto.tipo_diligenciacion_nombre),
            "fechaOrigen": exh_exhorto.fecha_origen.strftime("%Y-%m-%dT%H:%M:%S"),
            "observaciones": str(exh_exhorto.observaciones),
            "archivos": archivos,
        }

        # Enviar el exhorto (ETAPA 2)
        mensaje_advertencia = ""
        try:
            response = requests.post(
                exh_externo.endpoint_recibir_exhorto,
                headers={"X-Api-Key": exh_externo.api_key},
                timeout=TIMEOUT,
                json=datos_exhorto,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            mensaje_advertencia = "No hubo respuesta del servidor al enviar el exhorto"
        except requests.exceptions.HTTPError as error:
            mensaje_advertencia = f"Status Code {str(error)} al enviar el exhorto"
        except requests.exceptions.RequestException:
            mensaje_advertencia = "Falla desconocida al enviar el exhorto"

        # Si NO se comunicó con éxito...
        if mensaje_advertencia != "":
            # Actualizar por_enviar_tiempo_anterior
            exh_exhorto.por_enviar_tiempo_anterior = tiempo_actual
            # Incrementar por_enviar_intentos
            exh_exhorto.por_enviar_intentos += 1
            # Si el exhorto excede CANTIDAD_MAXIMA_INTENTOS, entonces cambiar el estado a INTENTOS AGOTADOS
            if exh_exhorto.por_enviar_intentos > CANTIDAD_MAXIMA_INTENTOS:
                exh_exhorto.estado = "INTENTOS AGOTADOS"
                mensaje_advertencia += ". Cambio el estado a INTENTOS AGOTADOS"
            else:
                mensaje_advertencia += f". Van {exh_exhorto.por_enviar_intentos} intentos"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            # Guardar los cambios en por_enviar_tiempo_anterior, por_enviar_intentos y estado
            exh_exhorto.save()
            continue  # Pasar al siguiente exhorto

        # Tomar success de la respuesta
        exhorto_enviado_con_exito = False
        respuesta = response.json()
        if "success" in respuesta:
            exhorto_enviado_con_exito = bool(respuesta["success"])
        else:
            exh_exhorto.estado = "RECHAZADO"
            exh_exhorto.save()
            mensaje_advertencia = "La respuesta no tiene 'success' al enviar el exhorto. Cambio el estado a RECHAZADO"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto

        # Si NO se envió con éxito...
        if exhorto_enviado_con_exito is False:
            exh_exhorto.estado = "RECHAZADO"
            exh_exhorto.save()
            mensaje_advertencia = "El envío del exhorto no fue exitoso. Cambio el estado a RECHAZADO"
            if "message" in respuesta:
                mensaje_advertencia += f"MENSAJE: {str(respuesta['message'])}"
            if "errors" in respuesta:
                mensaje_advertencia += f"ERRORES: {str(respuesta['errors'])}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto

        # Mandar los archivos del exhorto con multipart/form-data (ETAPA 3)
        todos_los_archivos_enviados_con_exito = True
        for exh_exhorto_archivo in exh_exhorto.exh_exhortos_archivos:
            # Informar al loggin que se va a enviar el archivo
            mensaje = f"Enviando archivo {exh_exhorto_archivo.nombre_archivo}..."
            bitacora.info(mensaje)

            # Pausa de 2 segundos entre envios de archivos
            time.sleep(2)

            # Obtener el contenido del archivo desde Google Storage
            try:
                archivo_contenido = get_file_from_gcs(
                    bucket_name=app.config["CLOUD_STORAGE_DEPOSITO"],
                    blob_name=get_blob_name_from_url(exh_exhorto_archivo.url),
                )
            except (MyBucketNotFoundError, MyFileNotFoundError, MyNotValidParamError) as error:
                mensaje_error = f"Falla al tratar de bajar el archivo del storage {str(error)}"
                mensajes_termino.append(mensaje_advertencia)
                bitacora.error(mensaje_error)
                todos_los_archivos_enviados_con_exito = False
                break  # Salir del bucle de archivos

            # Enviar el archivo
            mensaje_advertencia = ""
            try:
                response = requests.post(
                    url=exh_externo.endpoint_recibir_exhorto_archivo,
                    headers={"X-Api-Key": exh_externo.api_key},
                    timeout=TIMEOUT,
                    data={"exhortoOrigenId": exh_exhorto.exhorto_origen_id},
                    files={"archivo": (exh_exhorto_archivo.nombre_archivo, archivo_contenido, "application/pdf")},
                )
                response.raise_for_status()
            except requests.exceptions.ConnectionError:
                mensaje_advertencia = "No hubo respuesta del servidor al enviar el archivo"
            except requests.exceptions.HTTPError as error:
                mensaje_advertencia = f"Status Code {str(error)} al enviar el archivo"
            except requests.exceptions.RequestException:
                mensaje_advertencia = "Falla desconocida al enviar el archivo"

            # Si NO se comunicó con éxito...
            if mensaje_advertencia != "":
                # Actualizar por_enviar_tiempo_anterior
                exh_exhorto.por_enviar_tiempo_anterior = tiempo_actual
                # Incrementar por_enviar_intentos
                exh_exhorto.por_enviar_intentos += 1
                # Si el exhorto excede CANTIDAD_MAXIMA_INTENTOS, entonces cambiar el estado a INTENTOS AGOTADOS
                if exh_exhorto.por_enviar_intentos > CANTIDAD_MAXIMA_INTENTOS:
                    exh_exhorto.estado = "INTENTOS AGOTADOS"
                    mensaje_advertencia += ". Cambio el estado a INTENTOS AGOTADOS"
                else:
                    mensaje_advertencia += f". Van {exh_exhorto.por_enviar_intentos} intentos"
                mensajes_termino.append(mensaje_advertencia)
                bitacora.warning(mensaje_advertencia)
                # Guardar los cambios en por_enviar_tiempo_anterior, por_enviar_intentos y estado
                exh_exhorto.save()
                todos_los_archivos_enviados_con_exito = False
                break  # Salir del bucle de archivos

            # Tomar success de la respuesta
            archivo_enviado_con_exito = False
            respuesta = response.json()
            if "success" in respuesta:
                archivo_enviado_con_exito = bool(respuesta["success"])
            else:
                mensaje_advertencia = "La respuesta no tiene 'success' al enviar el archivo"
                mensajes_termino.append(mensaje_advertencia)
                bitacora.warning(mensaje_advertencia)
                todos_los_archivos_enviados_con_exito = False
                break  # Salir del bucle de archivos

            # Si NO se envió con éxito...
            if archivo_enviado_con_exito is False:
                mensaje_advertencia = "El envío del archivo del exhorto no fue exitoso"
                if "message" in respuesta:
                    mensaje_advertencia += f"MENSAJE: {str(respuesta['message'])}"
                if "errors" in respuesta:
                    mensaje_advertencia += f"ERRORES: {str(respuesta['errors'])}"
                mensajes_termino.append(mensaje_advertencia)
                bitacora.warning(mensaje_advertencia)
                todos_los_archivos_enviados_con_exito = False
                break  # Salir del bucle de archivos

        # Si todos_los_archivos_enviados_con_exito es falso, cambiar estado a RECHAZADO
        if todos_los_archivos_enviados_con_exito is False:
            exh_exhorto.estado = "RECHAZADO"
            exh_exhorto.save()
            mensaje_advertencia = "Cambio el estado a RECHAZADO por falla al enviar archivos"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto

        # Validar que en la ultima respuesta tenga "data"
        if "data" not in respuesta:
            exh_exhorto.estado = "RECHAZADO"
            exh_exhorto.save()
            mensaje_advertencia = "Cambio el estado a RECHAZADO porque la respuesta no tiene 'data'"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto
        data = respuesta["data"]

        # Validar que en data tenga "acuse"
        if "acuse" not in data:
            exh_exhorto.estado = "RECHAZADO"
            exh_exhorto.save()
            mensaje_advertencia = "Cambio el estado a RECHAZADO porque la respuesta no tiene 'acuse'"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue  # Pasar al siguiente exhorto
        acuse = data["acuse"]

        # Inicializar mensaje_advertencia como texto vacio, si falta algo obligado se llenará
        mensaje_advertencia = ""

        # Validar que en acuse tenga "exhortoOrigenId"
        try:
            acuse_exhorto_origen_id = str(acuse["exhortoOrigenId"])
            if acuse_exhorto_origen_id != str(exh_exhorto.exhorto_origen_id):
                mensaje_advertencia = "exhortoOrigenId no coincide en el acuse"
            bitacora.info("Acuse exhortoOrigenId: %s", acuse_exhorto_origen_id)
        except KeyError:
            mensaje_advertencia = "Faltó exhortoOrigenId en el acuse"

        # Validar que en acuse tenga "folioSeguimiento"
        try:
            acuse_folio_seguimiento = str(acuse["folioSeguimiento"])
            bitacora.info("Acuse folioSeguimiento: %s", acuse_folio_seguimiento)
        except KeyError:
            mensaje_advertencia = "Faltó folioSeguimiento en el acuse"

        # Validar que en acuse tenga "fechaHoraRecepcion"
        try:
            acuse_fecha_hora_recepcion_str = str(acuse["fechaHoraRecepcion"])
            bitacora.info("Acuse fechaHoraRecepcion: %s", acuse_fecha_hora_recepcion_str)
        except KeyError:
            mensaje_advertencia = "Faltó fechaHoraRecepcion en el acuse"
        try:
            acuse_fecha_hora_recepcion = datetime.strptime(acuse_fecha_hora_recepcion_str, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            try:
                acuse_fecha_hora_recepcion = datetime.strptime(acuse_fecha_hora_recepcion_str, "%Y-%m-%dT%H:%M:%S.%f")
            except ValueError:
                try:
                    acuse_fecha_hora_recepcion = datetime.strptime(acuse_fecha_hora_recepcion_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        acuse_fecha_hora_recepcion = datetime.strptime(acuse_fecha_hora_recepcion_str, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        mensaje_advertencia = "fechaHoraRecepcion en formato incorrecto"

        # Puede venir "municipioAreaRecibeId" en acuse porque es opcional
        acuse_municipio_area_recibe_id = None
        try:
            acuse_municipio_area_recibe_id = int(acuse["municipioAreaRecibeId"])
            bitacora.info("Acuse municipioAreaRecibeId: %s", acuse_municipio_area_recibe_id)
        except (KeyError, ValueError):
            pass

        # Puede venir "areaRecibeId" en acuse porque es opcional
        acuse_area_recibe_id = None
        try:
            acuse_area_recibe_id = str(acuse["areaRecibeId"])
            bitacora.info("Acuse areaRecibeId: %s", acuse_area_recibe_id)
        except KeyError:
            pass

        # Puede venir "areaRecibeNombre" en acuse porque es opcional
        acuse_area_recibe_nombre = None
        try:
            acuse_area_recibe_nombre = str(acuse["areaRecibeNombre"])
            bitacora.info("Acuse areaRecibeNombre: %s", acuse_area_recibe_nombre)
        except KeyError:
            pass

        # Puede venir "urlInfo" en acuse porque es opcional
        acuse_url_info = None
        try:
            acuse_url_info = str(acuse["urlInfo"])
            bitacora.info("Acuse urlInfo: %s", acuse_url_info)
        except KeyError:
            pass

        # Si falta algo obligado en el acuse, cambiar estado a RECHAZADO
        if mensaje_advertencia != "":
            exh_exhorto.estado = "RECHAZADO"
            exh_exhorto.save()
            mensaje_advertencia += ". Cambio el estado a RECHAZADO"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue

        # Actualizar el exhorto, principalmente cambiar el estado a RECIBIDO CON EXITO
        exh_exhorto.estado = "RECIBIDO CON EXITO"
        exh_exhorto.folio_seguimiento = acuse_folio_seguimiento
        exh_exhorto.acuse_fecha_hora_recepcion = acuse_fecha_hora_recepcion
        exh_exhorto.acuse_municipio_area_recibe_id = acuse_municipio_area_recibe_id
        exh_exhorto.acuse_area_recibe_id = acuse_area_recibe_id
        exh_exhorto.acuse_area_recibe_nombre = acuse_area_recibe_nombre
        exh_exhorto.acuse_url_info = acuse_url_info
        exh_exhorto.save()

        # Agregar mensaje de éxito a la bitácora
        mensaje = "El exhorto se envió con éxito. Cambio el estado a RECIBIDO CON EXITO"
        mensajes_termino.append(mensaje)
        bitacora.info(mensaje)

        # Pausa de 2 segundos entre envios de exhortos
        time.sleep(2)

        # Incrementar contador_recibidos_con_exito
        exhortos_procesados_contador += 1

    # Elaborar mensaje final
    mensaje_final = f"Termina enviar exhortos con {exhortos_procesados_contador} exhortos procesados."
    mensajes_termino.append(mensaje_final)
    bitacora.info(mensaje_final)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes_termino), "", ""


def lanzar_enviar(exhorto_origen_id: str):
    """Lanzar tarea en el fondo para enviar exhortos"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado exh_exhortos.enviar")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = enviar(exhorto_origen_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino
