"""
Financieros Vales, tareas en el fondo
"""

import json
import logging
import os
from datetime import datetime

import pytz
import requests
import sendgrid
from dotenv import load_dotenv
from sendgrid.helpers.mail import Content, Email, Mail, To

from hercules.app import create_app
from hercules.blueprints.fin_vales.models import FinVale
from hercules.blueprints.usuarios.models import Usuario
from hercules.extensions import database
from lib.exceptions import (
    MyAnyError,
    MyConnectionError,
    MyMissingConfigurationError,
    MyNotValidParamError,
    MyRequestError,
    MyResponseError,
    MyStatusCodeError,
)
from lib.safe_string import safe_string
from lib.tasks import set_task_error, set_task_progress

# Zona horaria
TIMEZONE = "America/Mexico_City"
local_tz = pytz.timezone(TIMEZONE)

# Cargar las variables de entorno
load_dotenv()
FIN_VALES_EFIRMA_SER_FIRMA_CADENA_URL = os.getenv("FIN_VALES_EFIRMA_SER_FIRMA_CADENA_URL", "")
FIN_VALES_EFIRMA_CAN_FIRMA_CADENA_URL = os.getenv("FIN_VALES_EFIRMA_CAN_FIRMA_CADENA_URL", "")
FIN_VALES_EFIRMA_QR_URL = os.getenv("FIN_VALES_EFIRMA_QR_URL", "")
FIN_VALES_EFIRMA_APP_ID = os.getenv("FIN_VALES_EFIRMA_APP_ID", "")
FIN_VALES_EFIRMA_APP_PASS = os.getenv("FIN_VALES_EFIRMA_APP_PASS", "")

# Roles que deben estar en la base de datos
ROL_SOLICITANTES = "FINANCIEROS SOLICITANTES"
ROL_AUTORIZANTES = "FINANCIEROS AUTORIZANTES"

TIMEOUT = 24  # Segundos de espera para la respuesta del motor de firma

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/fin_vales.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app


def solicitar(fin_vale_id: int, usuario_id: int, contrasena: str):
    """Firmar electronicamente el vale por quien solicita"""

    # Validar configuracion
    if FIN_VALES_EFIRMA_SER_FIRMA_CADENA_URL == "":
        mensaje = "Falta configurar FIN_VALES_EFIRMA_SER_FIRMA_CADENA_URL"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if FIN_VALES_EFIRMA_QR_URL == "":
        mensaje = "Falta configurar FIN_VALES_EFIRMA_QR_URL"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if FIN_VALES_EFIRMA_APP_ID == "":
        mensaje = "Falta configurar FIN_VALES_EFIRMA_APP_ID"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if FIN_VALES_EFIRMA_APP_PASS == "":
        mensaje = "Falta configurar FIN_VALES_EFIRMA_APP_PASS"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)

    # Consultar y validar el vale
    fin_vale = FinVale.query.get(fin_vale_id)
    if fin_vale is None:
        mensaje = f"No se encontró el vale {fin_vale_id}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if fin_vale.estatus != "A":
        mensaje = f"El vale {fin_vale_id} esta eliminado"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if fin_vale.estado != "CREADO":
        mensaje = f"El vale {fin_vale_id} no está en estado CREADO"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Consultar y validar el usuario
    solicita = Usuario.query.get(usuario_id)
    if solicita is None:
        mensaje = f"No se encontró el usuario {usuario_id} que solicita"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if solicita.efirma_registro_id is None or solicita.efirma_registro_id == 0:
        mensaje = f"El usuario {solicita.email} no tiene registro en el motor de firma"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if ROL_SOLICITANTES not in solicita.get_roles():
        mensaje = f"El usuario {solicita.email} no tiene el rol {ROL_SOLICITANTES}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Juntar los elementos del vale para armar la cadena
    elementos = {
        "id": fin_vale.id,
        "creado": fin_vale.creado.strftime("%Y-%m-%dT%H:%M:%S"),
        "justificacion": fin_vale.justificacion,
        "monto": fin_vale.monto,
        "solicito_nombre": solicita.nombre,
        "solicito_puesto": solicita.puesto,
        "solicito_email": solicita.email,
        "tipo": fin_vale.tipo,
    }

    # Preparar los datos que se van a enviar al motor de firma
    datos = {
        "cadenaOriginal": json.dumps(elementos),
        "idRegistro": solicita.efirma_registro_id,
        "contrasenaRegistro": contrasena,
        "idAplicacion": FIN_VALES_EFIRMA_APP_ID,
        "contrasenaAplicacion": FIN_VALES_EFIRMA_APP_PASS,
        "referencia": fin_vale_id,
        "verificarUrl": True,
    }

    # Enviar la solicitud al motor de firma
    try:
        response = requests.post(
            FIN_VALES_EFIRMA_SER_FIRMA_CADENA_URL,
            data=datos,
            timeout=TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = "Error de conexion al solicitar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyConnectionError(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = "Error porque la respuesta no tiene el estado 200 al solicitar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyStatusCodeError(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = "Error desconocido al solicitar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Tomar el texto de la respuesta
    texto = response.text

    # Si la contraseña es incorrecta, se registra el error
    if texto == "Contraseña incorrecta":
        mensaje = "Error porque la contraseña es incorrecta al solicitar el vale."
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Convertir el texto a un diccionario
    texto = response.text.replace('"{', "{").replace('}"', "}")
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        mensaje = "Error al solicitar el vale porque la respuesta no es JSON."
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Ejemplo de la respuesta
    #   "success": true,
    #   "folio": 000001,
    #   "mensaje": "La operación se ha realizado exitosamente.",
    #   "cadenaOriginal": "",
    #   "fecha": "27/06/2022 13:47:11",
    #   "selloDigital": "",
    #   "url": "https://servidor/eFirmaServicios/verificaFirmaCadena.do?verificar=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    #   "ip": "172.1.1.1",
    #   "huella": "Primer mensaje de prueba"

    # Si el motor de firma entrega "success" en false, se registra el error
    if datos["success"] is False:
        mensaje = "Error al solicitar el vale con este mensaje: " + str(datos["mensaje"])
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Actualizar el vale, ahora su estado es SOLICITADO
    fin_vale.solicito_nombre = solicita.nombre
    fin_vale.solicito_puesto = solicita.puesto
    fin_vale.solicito_email = solicita.email
    fin_vale.solicito_efirma_tiempo = datetime.strptime(datos["fecha"], "%d/%m/%Y %H:%M:%S")
    fin_vale.solicito_efirma_folio = datos["folio"]
    fin_vale.solicito_efirma_sello_digital = datos["selloDigital"]
    fin_vale.solicito_efirma_url = datos["url"]
    fin_vale.solicito_efirma_qr_url = f"{FIN_VALES_EFIRMA_QR_URL}?size=300&qrtext={datos['url']}"
    fin_vale.solicito_efirma_mensaje = datos["mensaje"]
    fin_vale.solicito_efirma_error = ""
    fin_vale.estado = "SOLICITADO"
    fin_vale.save()

    # Definir el remitente del mensaje de correo electronico
    remitente_email = Email(os.environ.get("SENDGRID_FROM_EMAIL", "plataforma.web@pjecz.gob.mx"))

    # Definir el destinatario del mensaje de correo electronico
    destinatario_email = To(fin_vale.usuario.email)

    # Definir el asunto del mensaje de correo electronico
    asunto = f"Vale de Gasolina {fin_vale_id} Solicitado"

    # Definir el contenido del mensaje de correo electronico
    host = os.environ.get("HOST", "http://127.0.0.1:5000")
    detalle_url = f"{host}/fin_vales/{fin_vale.id}"
    imprimir_url = f"{host}/fin_vales/imprimir/{fin_vale.id}"
    contenidos = []
    contenidos.append("<h2>Plataforma Hércules - Vales de Gasolina</h2>")
    contenidos.append(f"<p>La <a href='{detalle_url}'>solicitud del vale {fin_vale.id}</a> ya fue firmada.</p>")
    contenidos.append(f"<p><strong>Recomendamos siempre ahorrar papel e impresiones.</strong>")
    contenidos.append(f"Solo de ser necesario <a href='{imprimir_url}'>imprima esta página con la solicitud.</a></p>")
    contenidos.append("<p>Que tenga buen dia.</p>")
    contenidos.append(f"<p>Nota: Este mensaje fue creado por un programa. <strong>Favor de NO responder.</strong></p>")
    contenido = Content("text/html", "\n".join(contenidos))

    # Enviar el mensaje de correo electronico
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    if api_key != "":
        try:
            send_grid = sendgrid.SendGridAPIClient(api_key=api_key)
            mail = Mail(remitente_email, destinatario_email, asunto, contenido)
            send_grid.client.mail.send.post(request_body=mail.get())
        except Exception as error:
            mensaje = "Fallo el enviar el mensaje de correo electrónico. " + safe_string(str(error))
            bitacora.warning(mensaje)

    # Entregar
    mensaje = f"Se firmo electronicamente el vale {fin_vale_id} y ahora esta SOLICITADO"
    return mensaje


def lanzar_solicitar(fin_vale_id: int, usuario_id: int, contrasena: str):
    """Lanzar tarea para firmar electronicamente el vale por quien solicita"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia la tarea para firmar electronicamente el vale por quien solicita")

    # Ejecutar
    try:
        mensaje = solicitar(fin_vale_id, usuario_id, contrasena)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(progress=100, message=mensaje)
    return mensaje


def cancelar_solicitar(fin_vale_id: int, contrasena: str, motivo: str):
    """Cancelar la firma electronica de un vale por quien solicita"""

    # Validar configuracion
    if FIN_VALES_EFIRMA_CAN_FIRMA_CADENA_URL is None:
        mensaje = "Falta configurar FIN_VALES_EFIRMA_CAN_FIRMA_CADENA_URL"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if FIN_VALES_EFIRMA_APP_ID is None:
        mensaje = "Falta configurar FIN_VALES_EFIRMA_APP_ID"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if FIN_VALES_EFIRMA_APP_PASS is None:
        mensaje = "Falta configurar FIN_VALES_EFIRMA_APP_PASS"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)

    # Consultar y validar el vale
    fin_vale = FinVale.query.get(fin_vale_id)
    if fin_vale is None:
        mensaje = f"No se encontró el vale {fin_vale_id}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if fin_vale.estatus != "A":
        mensaje = f"El vale {fin_vale_id} esta eliminado"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if fin_vale.estado != "SOLICITADO":
        mensaje = f"El vale {fin_vale_id} no está en estado SOLICITADO"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if fin_vale.solicito_efirma_folio is None:
        mensaje = f"El vale {fin_vale_id} no tiene folio de solicitud"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Consultar al usuario que lo solicito
    solicito = Usuario.query.filter_by(email=fin_vale.solicito_email).first()
    if solicito is None:
        mensaje = f"No se encontró el usuario {fin_vale.solicito_email} que solicita"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if solicito.efirma_registro_id is None or solicito.efirma_registro_id == 0:
        mensaje = f"El usuario {fin_vale.solicito_email} no tiene registro en el motor de firma"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if ROL_SOLICITANTES not in solicito.get_roles():
        mensaje = f"El usuario {solicito.email} no tiene el rol {ROL_SOLICITANTES}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Preparar los datos que se van a enviar al motor de firma
    datos = {
        "idAplicacion": FIN_VALES_EFIRMA_APP_ID,
        "contrasenaAplicacion": FIN_VALES_EFIRMA_APP_PASS,
        "idRegistro": solicito.efirma_registro_id,
        "contrasenaRegistro": contrasena,
        "folios": fin_vale.solicito_efirma_folio,
    }

    # Enviar la cancelacion al motor de firma
    try:
        response = requests.post(
            FIN_VALES_EFIRMA_CAN_FIRMA_CADENA_URL,
            data=datos,
            timeout=TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = "Error de conexion al cancelar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyConnectionError(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = "Error porque la respuesta no tiene el estado 200 al cancelar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyStatusCodeError(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = "Error desconocido al cancelar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Tomar el texto de la respuesta
    texto = response.text

    # Si la contraseña es incorrecta, se registra el error
    if texto == "Contraseña incorrecta":
        mensaje = "Error porque la contraseña es incorrecta al cancelar el vale."
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Convertir el texto a un diccionario
    texto = response.text.replace('"{', "{").replace('}"', "}")
    try:
        _ = json.loads(texto)
    except json.JSONDecodeError:
        mensaje = "Error al cancelar el vale porque la respuesta no es JSON."
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Ejemplo de la respuesta
    #   "estatus": "SELLO CANCELADO"
    #   "fechaCancelado": 2022-07-04 12:39:08.0

    # Actualizar el vale, ahora su estado es CANCELADO POR SOLICITANTE
    fin_vale.estado = "CANCELADO POR SOLICITANTE"
    fin_vale.solicito_cancelo_tiempo = datetime.now()
    fin_vale.solicito_cancelo_motivo = safe_string(motivo, save_enie=True, to_uppercase=False)
    fin_vale.solicito_cancelo_error = ""
    fin_vale.save()

    # Entregar
    mensaje = f"Se cancelo la firma electronica del vale {fin_vale_id}"
    return mensaje


def lanzar_cancelar_solicitar(fin_vale_id: int, contrasena: str, motivo: str):
    """Lanzar tarea para cancelar la firma electronica de un vale por quien solicita"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia la tarea para cancelar la firma electronica de un vale por quien solicita")

    # Ejecutar
    try:
        mensaje = cancelar_solicitar(fin_vale_id, contrasena, motivo)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(progress=100, message=mensaje)
    return mensaje


def autorizar(fin_vale_id: int, usuario_id: int, contrasena: str):
    """Firmar electronicamente el vale por quien autoriza"""

    # Validar configuracion
    if FIN_VALES_EFIRMA_SER_FIRMA_CADENA_URL == "":
        mensaje = "Falta configurar FIN_VALES_EFIRMA_SER_FIRMA_CADENA_URL"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if FIN_VALES_EFIRMA_QR_URL == "":
        mensaje = "Falta configurar FIN_VALES_EFIRMA_QR_URL"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if FIN_VALES_EFIRMA_APP_ID == "":
        mensaje = "Falta configurar FIN_VALES_EFIRMA_APP_ID"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if FIN_VALES_EFIRMA_APP_PASS == "":
        mensaje = "Falta configurar FIN_VALES_EFIRMA_APP_PASS"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)

    # Consultar y validar el vale
    fin_vale = FinVale.query.get(fin_vale_id)
    if fin_vale is None:
        mensaje = f"No se encontró el vale {fin_vale_id}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if fin_vale.estatus != "A":
        mensaje = f"El vale {fin_vale_id} esta eliminado"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if fin_vale.estado != "SOLICITADO":
        mensaje = f"El vale {fin_vale_id} no está en estado SOLICITADO"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Consultar y validar el usuario
    autoriza = Usuario.query.get(usuario_id)
    if autoriza is None:
        mensaje = f"No se encontró el usuario {usuario_id} que autoriza"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if autoriza.efirma_registro_id is None or autoriza.efirma_registro_id == 0:
        mensaje = f"El usuario {autoriza.email} no tiene registro en el motor de firma"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if ROL_AUTORIZANTES not in autoriza.get_roles():
        mensaje = f"El usuario {autoriza.email} no tiene el rol {ROL_AUTORIZANTES}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Juntar los elementos del vale para armar la cadena
    elementos = {
        "id": fin_vale.id,
        "autorizo_nombre": autoriza.nombre,
        "autorizo_puesto": autoriza.puesto,
        "autorizo_email": autoriza.email,
        "creado": fin_vale.creado.strftime("%Y-%m-%dT%H:%M:%S"),
        "justificacion": fin_vale.justificacion,
        "monto": fin_vale.monto,
        "solicito_nombre": fin_vale.solicito_nombre,
        "solicito_puesto": fin_vale.solicito_puesto,
        "solicito_email": fin_vale.solicito_email,
        "tipo": fin_vale.tipo,
    }

    # Preparar los datos que se van a enviar al motor de firma
    datos = {
        "cadenaOriginal": json.dumps(elementos),
        "idRegistro": autoriza.efirma_registro_id,
        "contrasenaRegistro": contrasena,
        "idAplicacion": FIN_VALES_EFIRMA_APP_ID,
        "contrasenaAplicacion": FIN_VALES_EFIRMA_APP_PASS,
        "referencia": fin_vale_id,
        "verificarUrl": True,
    }

    # Enviar la solicitud al motor de firma
    try:
        response = requests.post(
            FIN_VALES_EFIRMA_SER_FIRMA_CADENA_URL,
            data=datos,
            timeout=TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = "Error de conexión al autorizar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyConnectionError(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = "Error porque la respuesta no tiene el estado 200 al autorizar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyStatusCodeError(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = "Error desconocido al autorizar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Tomar el texto de la respuesta
    texto = response.text

    # Si la contraseña es incorrecta, se registra el error
    if texto == "Contraseña incorrecta":
        mensaje = "Error porque la contraseña es incorrecta al autorizar el vale."
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Convertir el texto a un diccionario
    texto = response.text.replace('"{', "{").replace('}"', "}")
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        mensaje = "Error al autorizar el vale porque la respuesta no es JSON."
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Ejemplo de la respuesta
    #   "success": true,
    #   "folio": 000001,
    #   "mensaje": "La operación se ha realizado exitosamente.",
    #   "cadenaOriginal": "",
    #   "fecha": "27/06/2022 13:47:11",
    #   "selloDigital": "",
    #   "url": "https://servidor/eFirmaServicios/verificaFirmaCadena.do?verificar=ZhSsI%2FYUG9soc%2FkTfsWVvoUpylEwvoq%2F",
    #   "ip": "172.1.1.1",
    #   "huella": "Primer mensaje de prueba"

    # Si el motor de firma entrega "success" en false, se registra el error
    if datos["success"] is False:
        mensaje = "Error al solicitar el vale con este mensaje: " + str(datos["mensaje"])
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Actualizar el vale, ahora su estado es AUTORIZADO
    fin_vale.autorizo_nombre = autoriza.nombre
    fin_vale.autorizo_puesto = autoriza.puesto
    fin_vale.autorizo_email = autoriza.email
    fin_vale.autorizo_efirma_tiempo = datetime.strptime(datos["fecha"], "%d/%m/%Y %H:%M:%S")
    fin_vale.autorizo_efirma_folio = datos["folio"]
    fin_vale.autorizo_efirma_sello_digital = datos["selloDigital"]
    fin_vale.autorizo_efirma_url = datos["url"]
    fin_vale.autorizo_efirma_qr_url = f"{FIN_VALES_EFIRMA_QR_URL}?size=300&qrtext={datos['url']}"
    fin_vale.autorizo_efirma_mensaje = datos["mensaje"]
    fin_vale.autorizo_efirma_error = ""
    fin_vale.estado = "AUTORIZADO"
    fin_vale.save()

    # Definir el remitente del mensaje de correo electronico
    remitente_email = Email(os.environ.get("SENDGRID_FROM_EMAIL", "plataforma.web@pjecz.gob.mx"))

    # Definir el destinatario del mensaje de correo electrónico
    destinatario_email = To(fin_vale.usuario.email)

    # Definir el asunto del mensaje de correo electrónico
    asunto = f"Vale de Gasolina {fin_vale_id} Autorizado"

    # Definir el contenido del mensaje de correo electrónico
    host = os.environ.get("HOST", "http://127.0.0.1:5000")
    detalle_url = f"{host}/fin_vales/{fin_vale.id}"
    imprimir_url = f"{host}/fin_vales/imprimir/{fin_vale.id}"
    contenidos = []
    contenidos.append("<h2>Vale de Gasolina</h2>")
    contenidos.append(f"<p>La <a href='{detalle_url}'>autorización del vale {fin_vale.id}</a> ya fue firmada.</p>")
    contenidos.append(f"<p><strong>Recomendamos siempre ahorrar papel e impresiones.</strong>")
    contenidos.append(f"Solo de ser necesario <a href='{imprimir_url}'>imprima esta página con la solicitud.</a></p>")
    contenidos.append("<p>Que tenga buen dia.</p>")
    contenidos.append(f"<p>Nota: Este mensaje fue creado por un programa. <strong>Favor de NO responder.</strong></p>")
    contenido = Content("text/html", "\n".join(contenidos))

    # Enviar el mensaje de correo electronico
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    if api_key != "":
        try:
            send_grid = sendgrid.SendGridAPIClient(api_key=api_key)
            mail = Mail(remitente_email, destinatario_email, asunto, contenido)
            send_grid.client.mail.send.post(request_body=mail.get())
        except Exception as error:
            mensaje = "Fallo el enviar el mensaje de correo electrónico. " + safe_string(str(error))
            bitacora.warning(mensaje)

    # Entregar
    mensaje = f"Se firmo electrónicamente el vale {fin_vale_id} y ahora esta AUTORIZADO"
    return mensaje


def lanzar_autorizar(fin_vale_id: int, usuario_id: int, contrasena: str):
    """Lanzar tarea para firmar electronicamente el vale por quien autoriza"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia la tarea para firmar electronicamente el vale por quien autoriza")

    # Ejecutar
    try:
        mensaje = autorizar(fin_vale_id, usuario_id, contrasena)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(progress=100, message=mensaje)
    return mensaje


def cancelar_autorizar(fin_vale_id: int, contrasena: str, motivo: str):
    """Cancelar la firma electronica de un vale por quien autoriza"""

    # Validar configuracion
    if FIN_VALES_EFIRMA_CAN_FIRMA_CADENA_URL is None:
        mensaje = "Falta configurar FIN_VALES_EFIRMA_CAN_FIRMA_CADENA_URL"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if FIN_VALES_EFIRMA_APP_ID is None:
        mensaje = "Falta configurar FIN_VALES_EFIRMA_APP_ID"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)
    if FIN_VALES_EFIRMA_APP_PASS is None:
        mensaje = "Falta configurar FIN_VALES_EFIRMA_APP_PASS"
        bitacora.error(mensaje)
        raise MyMissingConfigurationError(mensaje)

    # Consultar y validar el vale
    fin_vale = FinVale.query.get(fin_vale_id)
    if fin_vale is None:
        mensaje = f"No se encontró el vale {fin_vale_id}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if fin_vale.estatus != "A":
        mensaje = f"El vale {fin_vale_id} esta eliminado"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if fin_vale.estado != "AUTORIZADO":
        mensaje = f"El vale {fin_vale_id} no está en estado AUTORIZADO"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if fin_vale.autorizo_efirma_folio is None:
        mensaje = f"El vale {fin_vale_id} no tiene folio de autorizacion"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Consultar al usuario que lo autorizo
    autorizo = Usuario.query.filter_by(email=fin_vale.autorizo_email).first()
    if autorizo is None:
        mensaje = f"No se encontró el usuario {fin_vale.autorizo_email} que autorizo"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if autorizo.efirma_registro_id is None or autorizo.efirma_registro_id == 0:
        mensaje = f"El usuario {fin_vale.autorizo_email} no tiene registro en el motor de firma"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)
    if ROL_AUTORIZANTES not in autorizo.get_roles():
        mensaje = f"El usuario {autorizo.email} no tiene el rol {ROL_AUTORIZANTES}"
        bitacora.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Preparar los datos que se van a enviar al motor de firma
    datos = {
        "idAplicacion": FIN_VALES_EFIRMA_APP_ID,
        "contrasenaAplicacion": FIN_VALES_EFIRMA_APP_PASS,
        "idRegistro": autorizo.efirma_registro_id,
        "contrasenaRegistro": contrasena,
        "folios": fin_vale.autorizo_efirma_folio,
    }

    # Enviar la cancelacion al motor de firma
    try:
        response = requests.post(
            FIN_VALES_EFIRMA_CAN_FIRMA_CADENA_URL,
            data=datos,
            timeout=TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as error:
        mensaje = "Error de conexion al cancelar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyConnectionError(mensaje)
    except requests.exceptions.HTTPError as error:
        mensaje = "Error porque la respuesta no tiene el estado 200 al cancelar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyStatusCodeError(mensaje)
    except requests.exceptions.RequestException as error:
        mensaje = "Error desconocido al cancelar el vale. " + safe_string(str(error))
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyRequestError(mensaje)

    # Tomar el texto de la respuesta
    texto = response.text

    # Si la contraseña es incorrecta, se registra el error
    if texto == "Contraseña incorrecta":
        mensaje = "Error porque la contraseña es incorrecta al cancelar el vale."
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Convertir el texto a un diccionario
    texto = response.text.replace('"{', "{").replace('}"', "}")
    try:
        _ = json.loads(texto)
    except json.JSONDecodeError:
        mensaje = "Error al cancelar el vale porque la respuesta no es JSON."
        fin_vale.solicito_efirma_error = mensaje
        fin_vale.save()
        bitacora.error(mensaje)
        raise MyResponseError(mensaje)

    # Ejemplo de la respuesta
    #   "estatus": "SELLO CANCELADO"
    #   "fechaCancelado": 2022-07-04 12:39:08.0

    # Actualizar el vale, ahora su estado es CANCELADO POR AUTORIZADOR
    fin_vale.estado = "CANCELADO POR AUTORIZADOR"
    fin_vale.autorizo_cancelo_tiempo = datetime.now()
    fin_vale.autorizo_cancelo_motivo = safe_string(motivo, save_enie=True, to_uppercase=False)
    fin_vale.autorizo_cancelo_error = ""
    fin_vale.save()

    # Entregar
    mensaje = f"Se cancelo la firma electronica del vale {fin_vale_id}"
    return mensaje


def lanzar_cancelar_autorizar(fin_vale_id: int, contrasena: str, motivo: str):
    """Lanzar tarea para cancelar la firma electronica de un vale por quien autoriza"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Inicia la tarea para cancelar la firma electronica de un vale por quien autoriza")

    # Ejecutar
    try:
        mensaje = cancelar_autorizar(fin_vale_id, contrasena, motivo)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de termino
    set_task_progress(progress=100, message=mensaje)
    return mensaje
