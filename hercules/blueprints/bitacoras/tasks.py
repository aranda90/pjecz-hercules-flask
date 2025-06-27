"""
Bitácoras, tareas para ejecutar en el fondo
"""

import logging
import os
from datetime import datetime, timedelta

import pytz
import sendgrid
from dotenv import load_dotenv
from sendgrid.helpers.mail import Content, Email, Mail, To

from hercules.app import create_app
from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.extensions import database
from lib.exceptions import MyAnyError, MyNotExistsError, MyNotValidParamError
from lib.tasks import set_task_error, set_task_progress

# Constantes
TIMEZONE = "America/Mexico_City"

# Bitácora logs/bitacoras.log
logs = logging.getLogger(__name__)
logs.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/bitacoras.log")
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


def enviar_reporte_diario(modulo_nombre: str, to_email: str, horas: int = 24) -> str:
    """Enviar mensaje con el reporte del módulo dado"""

    # Agregar mensaje de inicio
    mensaje = f"Inicia el envío del mensaje con reporte del módulo {modulo_nombre} en las últimas {horas} horas"
    logs.info(mensaje)

    # Consultar y validar el módulo
    modulo = Modulo.query.filter(Modulo.nombre == modulo_nombre).first()
    if not modulo:
        mensaje = f"El módulo {modulo_nombre} no existe"
        logs.error(mensaje)
        raise MyNotExistsError(mensaje)
    if modulo.estatus != "A":
        mensaje = f"El módulo {modulo_nombre} no está activo"
        logs.error(mensaje)
        raise MyNotValidParamError(mensaje)

    # Definir el tiempo para filtrar a partir de las últimas horas
    desde_dt = datetime.now() - timedelta(hours=horas)

    # Consultar la bitácora filtrando por el módulo y las últimas horas
    bitacoras = (
        Bitacora.query.filter(Bitacora.creado >= desde_dt)
        .filter(Bitacora.modulo_id == modulo.id)
        .filter(Bitacora.estatus == "A")
        .order_by(Bitacora.creado.desc())
        .all()
    )

    # Si no hay bitácoras, entregar mensaje de término
    if bitacoras is None or len(bitacoras) == 0:
        mensaje_termino = f"No se encontraron bitácoras del módulo {modulo_nombre} en las últimas {horas} horas"
        set_task_progress(100, mensaje_termino)
        return mensaje_termino

    # Elaborar el asunto del mensaje
    asunto_str = f"PJECZ Plataforma Web: Reporte de Bitácora del módulo {modulo_nombre} en las últimas {horas} horas"

    # Elaborar el contenido del mensaje
    fecha_elaboracion = datetime.now(tz=pytz.timezone(TIMEZONE)).strftime("%d/%b/%Y %H:%M")
    contenidos = []
    contenidos.append(f"<h2>{asunto_str}</h2>")
    contenidos.append(f"<p>Elaborado el {fecha_elaboracion}</p>")
    contenidos.append("<ul>")
    for bitacora in bitacoras:
        contenidos.append(f"<li>{bitacora.usuario.nombre} - {bitacora.descripcion}</li>")
    contenidos.append("</ul>")
    contenido_html = "\n".join(contenidos)

    # Enviar el e-mail
    send_grid = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    remitente_email = Email(SENDGRID_FROM_EMAIL)
    destinatario_email = To(to_email)
    contenido = Content("text/html", contenido_html)
    mail = Mail(remitente_email, destinatario_email, asunto_str, contenido)
    send_grid.client.mail.send.post(request_body=mail.get())

    # Entregar mensaje de término
    mensaje = f"Mensaje enviado a {to_email} con {len(bitacoras)} bitácoras"
    logs.info(mensaje)
    return mensaje


def lanzar_enviar_reporte_diario(modulo_nombre: str, to_email: str, horas: int = 24) -> str:
    """Lanzar la tarea de enviar el reporte diario del módulo dado"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, f"Inicia tarea para enviar el reporte diario del módulo {modulo_nombre}")

    # Ejecutar
    try:
        mensaje_termino = enviar_reporte_diario(modulo_nombre, to_email, horas)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo y entregar el mensaje de término
    set_task_progress(100, mensaje_termino)
    return mensaje_termino
