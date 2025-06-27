"""
Folio
"""

import re

FOLIO_REGEXP = r"^(\w+[-\/])*(\d+)\/(\d{4})$"


def validar_folio(input_str: str) -> list[int]:
    """Validar folio y extraer el número y año del folio NN/AAAA"""
    if not isinstance(input_str, str):
        raise ValueError("El folio debe ser una cadena de texto")
    input_str = input_str.strip()
    if input_str == "":
        raise ValueError("El folio no puede estar vacío")
    match = re.match(FOLIO_REGEXP, input_str)
    if match is None:
        raise ValueError(f"El folio '{input_str}' no es válido. Debe seguir el formato NN/AAAA.")
    # Extraer el número y año del folio
    folio_num = int(match.group(2))
    folio_anio = int(match.group(3))
    return folio_num, folio_anio
