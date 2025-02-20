"""
Exhortos Actulizaciones, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, Optional


TIPOS_ACTUALIZACIONES = [
    ("AreaTurnado", "Área de Turnado"),
    ("NumeroExhorto", "Número de Exhorto"),
]


class ExhExhortoActualizacionForm(FlaskForm):
    """Formulario ExhExhortosActualizaciones"""

    origen_id = StringField("Origen ID", validators=[DataRequired(), Length(max=48)])
    tipo_actualizacion = SelectField("Tipo de Actualización", validators=[DataRequired()], choices=TIPOS_ACTUALIZACIONES)
    descripcion = TextAreaField("Descripción", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
