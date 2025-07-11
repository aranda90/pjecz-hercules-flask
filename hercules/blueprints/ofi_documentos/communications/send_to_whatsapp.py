"""
Communications, enviar un mensaje por WhatsApp
"""

import requests

from hercules.app import create_app
from hercules.blueprints.ofi_documentos.communications import bitacora
from hercules.blueprints.ofi_documentos.models import OfiDocumento
from hercules.extensions import database
from lib.exceptions import MyConnectionError, MyNotExistsError, MyIsDeletedError, MyNotValidParamError
from lib.safe_string import safe_uuid

app = create_app()
app.app_context().push()
database.app = app

TIMEOUT = 60  # segundos


def enviar_a_whatsapp(ofi_documento_id: str) -> tuple[str, str, str]:
    """Enviar un mensaje por WhatsApp"""
    mensajes = []
    mensaje_info = f"Inicia enviar un mensaje por WhatsApp el oficio {ofi_documento_id}"
    mensajes.append(mensaje_info)
    bitacora.info(mensaje_info)

    # Consultar el oficio
    ofi_documento_id = safe_uuid(ofi_documento_id)
    if not ofi_documento_id:
        raise MyNotValidParamError("ID de oficio inválido")
    ofi_documento = OfiDocumento.query.get(ofi_documento_id)
    if not ofi_documento:
        raise MyNotExistsError("El oficio no existe")

    # Validar el estatus, que no esté eliminado
    if ofi_documento.estatus != "A":
        raise MyIsDeletedError("El oficio está eliminado")

    # Elaborar mensaje_termino
    mensaje_termino = "Termina enviar un mensaje por WhatsApp."
    mensajes.append(mensaje_termino)
    bitacora.info(mensaje_termino)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes), "", ""
