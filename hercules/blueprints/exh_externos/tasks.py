"""
Exh Externos, tareas en el fondo
"""

import logging

import requests

from hercules.app import create_app
from hercules.blueprints.exh_externos.models import ExhExterno
from hercules.extensions import database
from lib.exceptions import MyAnyError, MyEmptyError, MyNotExistsError
from lib.safe_string import safe_clave, safe_string
from lib.tasks import set_task_error, set_task_progress

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/exh_externos.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)

app = create_app()
app.app_context().push()
database.app = app

TIMEOUT = 30  # 30 segundos


def probar_endpoints(clave: str) -> tuple[str, str, str]:
    """Probar endpoints"""
    bitacora.info("Inicia probar_endpoints")

    # Limpiar clave
    clave = safe_clave(clave)

    # Si no se proporciona la clave
    exh_externos = []
    if clave == "":
        # Probar todos los exh externos
        exh_externos = ExhExterno.query.filter_by(estatus="A").all()
    else:
        # Consultar exh externo a partir de la clave
        exh_externo = ExhExterno.query.filter_by(clave=safe_clave(clave)).filter_by(estatus="A").first()
        if exh_externo is None:
            mensaje_advertencia = f"ERROR: No existe o ha sido eliminado el externo con clave {clave}"
            bitacora.warning(mensaje_advertencia)
            raise MyNotExistsError(mensaje_advertencia)
        exh_externos.append(exh_externo)

    # Validar que haya exh externos
    if len(exh_externos) == 0:
        mensaje_advertencia = "No hay externos para probar"
        bitacora.warning(mensaje_advertencia)
        raise MyEmptyError(mensaje_advertencia)

    # Inicializar listado de mensajes de termino
    mensajes_termino = []

    # Probar endpoints de consultar materias
    bitacora.info("Por probar %s endpoints de consultar materias...", len(exh_externos))
    contador_exitosos = 0
    contador_total = 0
    for exh_externo in exh_externos:
        if exh_externo.api_key == "":
            mensaje_advertencia = f"No hay api_key para {exh_externo.clave}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue
        if exh_externo.endpoint_consultar_materias == "":
            mensaje_advertencia = f"No hay endpoint_consultar_materias para {exh_externo.clave}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue
        bitacora.info("Probando %s...", exh_externo.clave)
        mensaje_advertencia = ""
        contador_total += 1
        try:
            response = requests.get(
                exh_externo.endpoint_consultar_materias,
                headers={"X-Api-Key": exh_externo.api_key},
                timeout=TIMEOUT,
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError as error:
            mensaje_advertencia = f"Error de conexión {str(error)} para {exh_externo.clave}"
        except requests.exceptions.Timeout:
            mensaje_advertencia = f"Se acabó el tiempo de espera para {exh_externo.clave}"
        except requests.exceptions.HTTPError as error:
            mensaje_advertencia = f"Error HTTP {str(error)} para {exh_externo.clave}"
        except requests.exceptions.RequestException as error:
            mensaje_advertencia = f"Error de request {str(error)} para {exh_externo.clave}"
        if mensaje_advertencia != "":
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue
        respuesta = response.json()
        consulta_materias_exitosa = False
        if "success" in respuesta:
            consulta_materias_exitosa = bool(respuesta["success"])
        else:
            mensaje_advertencia = f"La respuesta no tiene 'success' al consultar materias para {exh_externo.clave}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue
        if consulta_materias_exitosa is False:
            mensaje_advertencia = f"La consulta de materias no fue exitosa para {exh_externo.clave}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue
        if "data" not in respuesta:
            mensaje_advertencia = f"La respuesta no tiene 'data' para {exh_externo.clave}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue
        materias = []  # Este dict se va a guardar como JSON con clave y nombre para cada una
        for materia in respuesta["data"]:
            if "clave" not in materia:
                mensaje_advertencia = f"La respuesta no tiene 'clave' para {exh_externo.clave}"
                mensajes_termino.append(mensaje_advertencia)
                bitacora.warning(mensaje_advertencia)
                continue
            clave = safe_clave(materia["clave"])
            if clave == "":
                mensaje_advertencia = f"Una clave de materia no es válida para {exh_externo.clave}"
                mensajes_termino.append(mensaje_advertencia)
                bitacora.warning(mensaje_advertencia)
                continue
            if "nombre" not in materia:
                mensaje_advertencia = f"Un nombre de materia no es válido para para {exh_externo.clave}"
                mensajes_termino.append(mensaje_advertencia)
                bitacora.warning(mensaje_advertencia)
                continue
            nombre = safe_string(materia["nombre"], save_enie=True)
            materias.append({"clave": clave, "nombre": nombre})
        if len(materias) == 0:
            mensaje_advertencia = f"La respuesta no contiene claves de materias para {exh_externo.clave}"
            mensajes_termino.append(mensaje_advertencia)
            bitacora.warning(mensaje_advertencia)
            continue
        if exh_externo.materias is None or exh_externo.materias != materias:
            exh_externo.materias = materias
            exh_externo.save()
            mensaje = f"Se actualizaron las materias de {exh_externo.clave}"
            mensajes_termino.append(mensaje)
            bitacora.info(mensaje)
        else:
            mensaje = f"No cambiaron las materias para {exh_externo.clave}"
            mensajes_termino.append(mensaje)
            bitacora.info(mensaje)
        contador_exitosos += 1

    # Elaborar mensaje final
    mensaje_final = f"Termina probar endpoints con {contador_exitosos} consultas exitosas."
    mensajes_termino.append(mensaje_final)
    bitacora.info(mensaje_final)

    # Entregar mensaje_termino, nombre_archivo y url_publica
    return "\n".join(mensajes_termino), "", ""


def lanzar_probar_endpoints(clave: str):
    """Lanzar tarea en el fondo para probar externos"""

    # Iniciar la tarea en el fondo
    set_task_progress(0, "Se ha lanzado exh_externos.probar_endpoints")

    # Ejecutar
    try:
        mensaje_termino, nombre_archivo, url_publica = probar_endpoints(clave)
    except MyAnyError as error:
        mensaje_error = str(error)
        set_task_error(mensaje_error)
        return mensaje_error

    # Terminar la tarea en el fondo
    set_task_progress(100, mensaje_termino, nombre_archivo, url_publica)

    # Entregar mensaje de termino
    return mensaje_termino
