"""
Exhortos Actulizaciones, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class ExhExhortoActualizacionNewForm(FlaskForm):
    """Formulario ExhExhortosActualizaciones"""

    origen_id = StringField("Origen ID", validators=[DataRequired(), Length(max=48)])
    tipo_actualizacion = StringField("Tipo de Actualización", validators=[DataRequired(), Length(max=48)])
    descripcion = TextAreaField("Descripción", validators=[DataRequired(), Length(max=256)])
    crear = SubmitField("Crear")
