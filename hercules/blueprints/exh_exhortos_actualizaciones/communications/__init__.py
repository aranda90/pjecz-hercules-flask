"""
Communications init
"""

import logging

bitacora = logging.getLogger(__name__)
bitacora.setLevel(logging.INFO)
formato = logging.Formatter("%(asctime)s:%(levelname)s:%(message)s")
empunadura = logging.FileHandler("logs/exh_exhortos_actualizaciones.log")
empunadura.setFormatter(formato)
bitacora.addHandler(empunadura)
