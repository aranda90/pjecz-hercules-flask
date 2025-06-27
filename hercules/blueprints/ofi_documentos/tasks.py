"""
Ofi Documentos, tareas para ejecutar en el fondo
"""

import logging
import os
from datetime import datetime

import pytz
import sendgrid
from dotenv import load_dotenv
from sendgrid.helpers.mail import Content, Email, Mail

from hercules.app import create_app
from hercules.blueprints.ofi_documentos.models import OfiDocumento
from hercules.blueprints.ofi_documentos_destinatarios.models import OfiDocumentoDestinatario
from hercules.extensions import database
from lib.exceptions import MyAnyError, MyNotExistsError, MyNotValidParamError
from lib.tasks import set_task_error, set_task_progress

# Constantes
TIMEZONE = "America/Mexico_City"

# Bitácora logs/ofi_documentos.log
logs = logging.getLogger(__name__)
logs.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/ofi_documentos.log")
empunadura.setFormatter(formato)
logs.addHandler(empunadura)

# Cargar variables de entorno
load_dotenv()
HOST = os.getenv("HOST", "http://localhost:5000")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDGRID_FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "plataforma.web@pjecz.gob.mx")

# Cargar la aplicación para tener acceso a la base de datos
app = create_app()
app.app_context().push()
database.app = app


def enviar_mensaje(ofi_documento_id: int) -> str:
    """Enviar mensaje con el aviso de recepción de un oficio"""

    # Agregar mensaje de inicio
    mensaje = f"Inicia el envío del mensaje a los destinatarios del oficio {ofi_documento_id}"
    logs.info(mensaje)

    # Consultar y validar el oficio
    ofi_documento = OfiDocumento.query.filter(OfiDocumento.id == ofi_documento_id).first()
    if not ofi_documento:
        mensaje = f"El Oficio {ofi_documento_id} no existe"
        logs.error(mensaje)
        raise MyNotExistsError(mensaje)
    if ofi_documento.estatus != "A":
        mensaje = f"El Oficio {ofi_documento_id} no está activo"
        logs.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Consultar los destinatarios
    ofi_destinatarios = (
        OfiDocumentoDestinatario.query.filter(OfiDocumentoDestinatario.ofi_documento_id == ofi_documento_id)
        .filter(OfiDocumentoDestinatario.estatus == "A")
        .all()
    )

    # Elaborar el asunto del mensaje
    asunto_str = f"PJECZ Plataforma Web: Notificación de Oficio {ofi_documento.descripcion}"

    # Elaborar el contenido del mensaje
    fecha_elaboracion = datetime.now(tz=pytz.timezone(TIMEZONE)).strftime("%d/%b/%Y %H:%M")
    contenidos = []
    contenidos.append(f"<h2>{asunto_str}</h2>")
    contenidos.append(f"<p>Elaborado el {fecha_elaboracion}</p>")
    contenidos.append(
        f"<p>Ha recibido un nuevo oficio dentro de Plataforma Web: <a href='{HOST}/ofi_documentos/{ofi_documento_id}'>{ofi_documento.descripcion}</a></p>"
    )
    # logs.info(f"Se encontraron {len(bitacoras)} bitácoras del módulo {modulo_nombre} en las últimas 24 horas")
    contenido_html = "\n".join(contenidos)

    # Enviar el e-mail
    send_grid = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    remitente_email = Email(SENDGRID_FROM_EMAIL)
    contenido = Content("text/html", contenido_html)
    mail = Mail(
        from_email=remitente_email,
        subject=asunto_str,
        html_content=contenido,
    )
    for destinatario in ofi_destinatarios:
        if destinatario.con_copia == True:
            mail.add_cc(destinatario.usuario.email)
        else:
            mail.add_to(destinatario.usuario.email)
    # Enviar correo
    send_grid.client.mail.send.post(request_body=mail.get())

    # Entregar mensaje de término
    mensaje = f"Mensaje enviado"
    logs.info(mensaje)
    return mensaje


def lanzar_enviar_mensaje(ofi_documento_id: int) -> str:
    """Lanzar la tarea de enviar el mensaje de recepción de oficio"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Inicia tarea para enviar mensaje de recepción de oficio {ofi_documento_id}")

    # Ejecutar
    try:
        mensaje_termino = enviar_mensaje(ofi_documento_id)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de término
    set_task_progress(100, mensaje_termino)
    return mensaje_termino
