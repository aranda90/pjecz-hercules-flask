"""
Communications, Enviar Actualizacion
"""

from datetime import datetime

import requests

from hercules.app import create_app
from hercules.blueprints.estados.models import Estado
from hercules.blueprints.exh_exhortos.communications import bitacora
from hercules.blueprints.exh_exhortos.models import ExhExhorto
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.blueprints.municipios.models import Municipio
from hercules.extensions import database
from lib.exceptions import MyAnyError, MyConnectionError, MyNotExistsError
from lib.pwgen import generar_identificador

app = create_app()
app.app_context().push()
database.app = app

TIMEOUT = 60  # segundos


def enviar_actualizacion(exh_exhorto_actualizacion_id: int) -> tuple[str, str, str]:
    """Enviar actualización"""
    bitacora.info("Inicia enviar la actualización al PJ externo")

    # Consultar la actualización
    exh_exhorto_actualizacion = ExhExhorto.query.get(exh_exhorto_actualizacion_id)

    # Validar que exista la actualización
    if exh_exhorto_actualizacion is None:
        mensaje_advertencia = f"No existe la actualización con ID {exh_exhorto_actualizacion_id}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Validar que su estado sea POR ENVIAR
    if exh_exhorto_actualizacion.estado != "PENDIENTE":
        mensaje_advertencia = f"La actualización con ID {exh_exhorto_actualizacion_id} no tiene el estado PENDIENTE"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Consultar el Estado de destino a partir del ID del Municipio en municipio_destino_id
    municipio = Municipio.query.get(exh_exhorto_actualizacion.exh_exhorto.municipio_destino_id)
    if municipio is None:
        mensaje_advertencia = f"No existe el municipio con ID {exh_exhorto_actualizacion.exh_exhorto.municipio_destino_id}"
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

    # Si exh_externo no tiene endpoint para enviar actualizaciones
    if exh_externo.endpoint_actualizar_exhorto is None or exh_externo.endpoint_actualizar_exhorto == "":
        mensaje_advertencia = f"No tiene endpoint para enviar actualizaciones el estado {estado.nombre}"
        bitacora.error(mensaje_advertencia)
        raise MyNotExistsError(mensaje_advertencia)

    # Generar un identificador único para la actualización
    actualizacion_origen_id = generar_identificador()

    # Definir los datos de la actualización a enviar
    payload_for_json = {
        "exhortoId": exh_exhorto_actualizacion.exh_exhorto.exhorto_origen_id,
        "actualizacionOrigenId": actualizacion_origen_id,
        "tipoActualizacion": str(exh_exhorto_actualizacion.tipo_actualizacion),
        "fechaHora": exh_exhorto_actualizacion.fecha_hora.strftime("%Y-%m-%d %H:%M:%S"),
        "descripcion": str(exh_exhorto_actualizacion.descripcion),
    }

    # Informar a la bitácora que se va a enviar la actualización
    mensaje = "Pasan las validaciones y comienza el envío de la actualización."
    bitacora.info(mensaje)

    # Enviar la actualización
    contenido = None
    mensaje_advertencia = ""
    try:
        respuesta = requests.post(
            url=exh_externo.endpoint_actualizar_exhorto,
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

    # Informar a la bitácora que terminó el envío la actualización
    mensaje = "Termina el envío la actualización."
    bitacora.info(mensaje)

    # Tomar la confirmación de la actualización
    confirmacion = contenido["data"]

    # Inicializar listado de errores para acumular fallos si los hubiera
    errores = []

    # Validar que la confirmación tenga exhortoId
    try:
        confirmacion_exhorto_id = str(confirmacion["exhortoId"])
        bitacora.info("Confirmación exhortoId: %s", confirmacion_exhorto_id)
    except KeyError:
        errores.append("Faltó exhortoId en la confirmación")

    # Validar que la confirmación tenga actualizacionOrigenId
    try:
        confirmacion_actulaizacion_origen_id = str(confirmacion["actualizacionOrigenId"])
        bitacora.info("Confirmación actualizacionOrigenId: %s", confirmacion_actulaizacion_origen_id)
    except KeyError:
        errores.append("Faltó actualizacionOrigenId en la confirmación")

    # Validar que la confirmación tenga fechaHora
    try:
        confirmacion_fecha_hora_str = str(confirmacion["fechaHora"])
        confirmacion_fecha_hora = datetime.strptime(confirmacion_fecha_hora_str, "%Y-%m-%d %H:%M:%S")
        bitacora.info("Acuse fechaHora: %s", confirmacion_fecha_hora_str)
    except KeyError:
        errores.append("Faltó o es incorrecta fechaHora en la confirmación")

    # Terminar si hubo errores
    if len(errores) > 0:
        mensaje_advertencia = ", ".join(errores)
        bitacora.warning(mensaje_advertencia)
        raise MyAnyError(mensaje_advertencia)

    # Actualizar el estado a ENVIADO
    exh_exhorto_actualizacion.estado = "ENVIADO"
    exh_exhorto_actualizacion.save()

    # Elaborar mensaje_termino
    mensaje_termino = "Termina enviar la actualización al PJ externo"
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return mensaje_termino, "", ""
