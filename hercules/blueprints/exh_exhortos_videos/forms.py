"""
Exh_Exhorto_Videos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional


class ExhExhortoVideoForm(FlaskForm):
    """Formulario Nuevo Video"""

    titulo = StringField("Título", validators=[DataRequired(), Length(max=256)])
    descripcion = StringField("Descripción", validators=[Optional(), Length(max=1024)])
    url_acceso = StringField("URL", validators=[DataRequired(), Length(max=512)])
    guardar = SubmitField("Guardar")
