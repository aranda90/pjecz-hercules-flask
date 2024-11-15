"""
Exh Áreas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class ExhAreaForm(FlaskForm):
    """Formulario Área"""

    clave = StringField("Clave", validators=[DataRequired(), Length(max=16)])
    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    guardar = SubmitField("Guardar")
