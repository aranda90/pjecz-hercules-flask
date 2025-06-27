"""
Safe String
"""

from datetime import date
import re
import uuid

from unidecode import unidecode

CLAVE_REGEXP = r"^[a-zA-Z0-9-]{1,16}$"
CONCEPTO_REGEXP = r"^[PD][a-zA-Z0-9]{2,3}$"
CONTRASENA_REGEXP = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,48}$"
CURP_REGEXP = r"^[a-zA-Z]{4}\d{6}[a-zA-Z]{6}[A-Z0-9]{2}$"
EMAIL_REGEXP = r"^[\w.-]+@[\w.-]+\.\w+$"
EXPEDIENTE_REGEXP = r"^\d+\/[12]\d\d\d(-[a-zA-Z0-9]+(-[a-zA-Z0-9]+)?)?$"
DIRECCION_IP_REGEXP = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
MAC_ADDRESS_REGEXP = r"([0-9A-Fa-f]{2}[:-]?){5}([0-9A-Fa-f]{2})"
NUMERO_PUBLICACION_REGEXP = r"^\d+/[12]\d\d\d$"
PLAZA_REGEXP = r"^[a-zA-Z0-9]{1,24}$"
QUINCENA_REGEXP = r"^\d{6}$"
RFC_REGEXP = r"^[a-zA-Z]{3,4}\d{6}[a-zA-Z0-9]{3}$"
SENTENCIA_REGEXP = r"^\d+/[12]\d\d\d$"
TELEFONO_REGEXP = r"^[0-9]{10}$"
TOKEN_REGEXP = r"^[a-zA-Z0-9_.=+-]+$"
URL_REGEXP = r"^(https?:\/\/)[0-9a-z-_]*(\.[0-9a-z-_]+)*(\.[a-z]+)+(:(\d+))?(\/[0-9a-z%-_]*)*?\/?$"


def extract_expediente_anio(input_str: str) -> int:
    """Extraer el anio AAAA del expediente NN/AAAA-XX como un entero"""
    # Validar que comience con un numero/anio
    inicio_str = re.match(r"^\d+\/[12]\d\d\d", input_str)
    if inicio_str is None:
        return 0
    # Entregar el anio como entero
    return int(inicio_str.group(0).split("/")[1])


def extract_expediente_num(input_str: str) -> int:
    """Extraer el numero NN del expediente NN/AAAA-XX como un entero"""
    # Validar que comience con un numero/anio
    inicio_str = re.match(r"^\d+\/[12]\d\d\d", input_str)
    if inicio_str is None:
        return 0
    # Entregar el numero como entero
    return int(inicio_str.group(0).split("/")[0])


def safe_clave(input_str, max_len=16, only_digits=False, separator="-") -> str:
    """Safe clave"""
    if not isinstance(input_str, str):
        return ""
    stripped = input_str.strip()
    if stripped == "":
        return ""
    if only_digits:
        clean_string = re.sub(r"[^0-9]+", separator, stripped)
    else:
        clean_string = re.sub(r"[^a-zA-Z0-9]+", separator, unidecode(stripped))
    without_spaces = re.sub(r"\s+", "", clean_string)
    final = without_spaces.upper()
    if len(final) > max_len:
        return final[:max_len]
    return final


def safe_curp(input_str, is_optional=False, search_fragment=False) -> str:
    """Safe CURP"""
    if not isinstance(input_str, str):
        return ""
    stripped = input_str.strip()
    if is_optional and stripped == "":
        return ""
    clean_string = re.sub(r"[^a-zA-Z0-9]+", " ", unidecode(stripped))
    without_spaces = re.sub(r"\s+", "", clean_string)
    final = without_spaces.upper()
    if search_fragment is False and re.match(CURP_REGEXP, final) is None:
        raise ValueError("CURP inválida")
    return final


def safe_email(input_str, search_fragment=False) -> str:
    """Safe string"""
    if not isinstance(input_str, str):
        return ""
    final = input_str.strip().lower()
    if final == "":
        return ""
    if search_fragment:
        if re.match(r"^[\w.-]*@*[\w.-]*\.*\w*$", final) is None:
            return ""
        return final
    if re.match(EMAIL_REGEXP, final) is None:
        raise ValueError("E-mail inválido")
    return final


def safe_expediente(input_str):
    """Convierte la cadena en un formato de expediente valido como 123/2023, 123/2023-II, 123/2023-II-2, 123/2023-F2"""
    if not isinstance(input_str, str) or input_str.strip() == "":
        return ""
    elementos = re.sub(r"[^a-zA-Z0-9]+", "|", unidecode(input_str.strip())).split("|")
    try:
        numero = int(elementos[0])
        ano = int(elementos[1])
    except (IndexError, ValueError) as error:
        raise ValueError
    if ano < 1900 or ano > date.today().year:
        raise ValueError
    extra_1 = ""
    if len(elementos) >= 3:
        extra_1 = "-" + elementos[2].upper()
    extra_2 = ""
    if len(elementos) >= 4:
        extra_2 = "-" + elementos[3].upper()
    limpio = f"{str(numero)}/{str(ano)}{extra_1}{extra_2}"
    if len(limpio) > 16:
        raise ValueError
    return limpio


def safe_quincena(input_str) -> str:
    """Safe quincena"""
    final = input_str.strip()
    if re.match(QUINCENA_REGEXP, final) is None:
        raise ValueError("Quincena invalida")
    return final


def safe_ip_address(input_str):
    """Safe IP address"""
    if not isinstance(input_str, str) or input_str.strip() == "":
        return ""
    input_str = input_str.strip()
    if re.match(DIRECCION_IP_REGEXP, input_str) is None:
        return ""
    return input_str


def safe_mac_address(input_str):
    """Safe MAC address"""
    if not isinstance(input_str, str) or input_str.strip() == "":
        return ""
    input_str = input_str.strip()
    if re.match(MAC_ADDRESS_REGEXP, input_str) is None:
        return ""
    en_mayusculas = input_str.upper()
    m = re.sub(r"[^0-9A-F]+", "", en_mayusculas)
    return f"{m[0:2]}:{m[2:4]}:{m[4:6]}:{m[6:8]}:{m[8:10]}:{m[10:12]}"


def safe_telefono(input_str):
    """Safe telefono, debe ser de 10 digitos"""
    if not isinstance(input_str, str) or input_str.strip() == "":
        return ""
    input_str = input_str.strip()
    if re.match(TELEFONO_REGEXP, input_str) is None:
        return ""
    return input_str


def safe_text(input_str, max_len=4096, to_uppercase=True):
    """Safe string"""
    if not isinstance(input_str, str):
        return ""
    new_string = re.sub(r"[^a-zA-Z0-9@\n()\?=\[\]:/_.-]+", " ", unidecode(input_str))
    final = new_string.strip()
    if to_uppercase:
        final = final.upper()
    if max_len == 0:
        return final
    return (final[:max_len] + "…") if len(final) > max_len else final


def safe_message(input_str, max_len=250, default_output_str="Sin descripción") -> str:
    """Safe message"""
    message = str(input_str)
    if message == "":
        return default_output_str
    return (message[:max_len] + "…") if len(message) > max_len else message


def safe_numero_publicacion(input_str):
    """Safe número publicación"""
    return safe_sentencia(input_str)


def safe_sentencia(input_str):
    """Safe sentencia"""
    if not isinstance(input_str, str) or input_str.strip() == "":
        return ""
    elementos = re.sub(r"[^0-9A-Z]+", "|", unidecode(input_str)).split("|")
    try:
        numero = int(elementos[0])
        ano = int(elementos[1])
    except (IndexError, ValueError) as error:
        raise error
    if numero <= 0:
        raise ValueError
    if ano < 1900 or ano > date.today().year:
        raise ValueError
    limpio = f"{str(numero)}/{str(ano)}"
    if len(limpio) > 16:
        raise ValueError
    return limpio


def safe_rfc(input_str, is_optional=False, search_fragment=False) -> str:
    """Safe RFC"""
    if not isinstance(input_str, str):
        return ""
    stripped = input_str.strip()
    if is_optional and stripped == "":
        return ""
    clean_string = re.sub(r"[^a-zA-Z0-9]+", " ", unidecode(stripped))
    without_spaces = re.sub(r"\s+", "", clean_string)
    final = without_spaces.upper()
    if search_fragment is False and re.match(RFC_REGEXP, final) is None:
        raise ValueError("RFC inválido")
    return final


def safe_string(input_str, max_len=250, do_unidecode=True, save_enie=False, to_uppercase=True) -> str:
    """Safe string"""
    if not isinstance(input_str, str):
        return ""
    if do_unidecode:
        new_string = re.sub(r"[^a-zA-Z0-9.()/-]+", " ", input_str)
        if save_enie:
            new_string = ""
            for char in input_str:
                if char == "ñ":
                    new_string += "ñ"
                elif char == "Ñ":
                    new_string += "Ñ"
                else:
                    new_string += unidecode(char)
        else:
            new_string = re.sub(r"[^a-zA-Z0-9.()/-]+", " ", unidecode(input_str))
    else:
        if save_enie is False:
            new_string = re.sub(r"[^a-záéíóúüA-ZÁÉÍÓÚÜ0-9.()/-]+", " ", input_str)
        else:
            new_string = re.sub(r"[^a-záéíóúüñA-ZÁÉÍÓÚÜÑ0-9.()/-]+", " ", input_str)
    removed_multiple_spaces = re.sub(r"\s+", " ", new_string)
    final = removed_multiple_spaces.strip()
    if to_uppercase:
        final = final.upper()
    if max_len == 0:
        return final
    return (final[:max_len] + "…") if len(final) > max_len else final


def safe_url(input_str):
    """Safe URL"""
    if not isinstance(input_str, str) or input_str.strip() == "":
        return ""
    input_str = input_str.strip()
    if re.match(URL_REGEXP, input_str) is None:
        return ""
    return input_str


def safe_uuid(input_str: str) -> str:
    """Safe UUID"""
    try:
        uuid.UUID(input_str)
        return input_str
    except ValueError:
        return ""
