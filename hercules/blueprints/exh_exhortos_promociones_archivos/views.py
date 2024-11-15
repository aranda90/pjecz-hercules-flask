"""
Exhortos Promociones Archivos, vistas
"""

import json
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from lib.datatables import get_datatable_parameters, output_datatable_json
from lib.safe_string import safe_string, safe_message

from hercules.blueprints.bitacoras.models import Bitacora
from hercules.blueprints.modulos.models import Modulo
from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.usuarios.decorators import permission_required
from hercules.blueprints.exh_exhortos_promociones_archivos.models import ExhExhortoPromocionArchivo

MODULO = "EXH EXHORTOS PROMOCIONES ARCHIVOS"

exh_exhortos_promociones_archivos = Blueprint("exh_exhortos_promociones_archivos", __name__, template_folder="templates")


@exh_exhortos_promociones_archivos.before_request
@login_required
@permission_required(MODULO, Permiso.VER)
def before_request():
    """Permiso por defecto"""
