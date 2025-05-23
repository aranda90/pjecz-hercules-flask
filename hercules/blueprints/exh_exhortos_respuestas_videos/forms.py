"""
Exh Exhortos Respuestas Videos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class ExhExhortoRespuestaVideoForm(FlaskForm):
    """Formulario Nuevo Video"""

    titulo = StringField("Título", validators=[DataRequired(), Length(max=256)])
    descripcion = TextAreaField("Descripción", validators=[Optional(), Length(max=1024)], render_kw={"rows": 5})
    url_acceso = StringField("URL de acceso", validators=[DataRequired(), Length(max=512)])
    guardar = SubmitField("Guardar")
