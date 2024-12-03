"""
Materias, formularios
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from lib.safe_string import CLAVE_REGEXP


class MateriaForm(FlaskForm):
    """Formulario Materia"""

    clave = StringField("Clave (única de hasta 16 caracteres)", validators=[DataRequired(), Regexp(CLAVE_REGEXP)])
    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=64)])
    descripcion = TextAreaField("Descripción", validators=[Optional(), Length(max=1024)])
    en_sentencias = BooleanField("En Sentencias", validators=[Optional()])
    en_exh_exhortos = BooleanField("En Exhortos Electrónicos", validators=[Optional()])
    guardar = SubmitField("Guardar")
