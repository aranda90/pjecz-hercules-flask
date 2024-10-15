"""
Ubicaciones de Expedientes, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, RadioField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from lib.safe_string import EXPEDIENTE_REGEXP
from hercules.blueprints.ubicaciones_expedientes.models import UbicacionExpediente


class UbicacionExpedienteNewForm(FlaskForm):
    """Formulario UbicacionExpedienteNew"""

    distrito = StringField("Distrito")  # Read only
    autoridad = StringField("Autoridad")  # Read only
    expediente = StringField("Expediente", validators=[DataRequired(), Length(max=16), Regexp(EXPEDIENTE_REGEXP)])
    ubicacion = RadioField("Ubicación", validators=[DataRequired()], choices=UbicacionExpediente.UBICACIONES.items())
    guardar = SubmitField("Guardar")


class UbicacionExpedienteEditForm(FlaskForm):
    """Formulario para editar Ubicación de Expediente"""

    expediente = StringField("Expediente", validators=[DataRequired(), Length(max=16), Regexp(EXPEDIENTE_REGEXP)])
    ubicacion = RadioField("Ubicación", validators=[DataRequired()], choices=UbicacionExpediente.UBICACIONES.items())
    guardar = SubmitField("Guardar")
