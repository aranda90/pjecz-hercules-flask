"""
Ofi Plantillas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Optional


class OfiPlantillaForm(FlaskForm):
    """Formulario OfiPlantilla"""

    descripcion = StringField("Descripción", validators=[DataRequired()])
    autor = SelectField("Autor", coerce=int, validate_choice=False, validators=[DataRequired()])
    contenido_md = TextAreaField("Contenido MD", validators=[Optional()], render_kw={"rows": 10})
    contenido_html = TextAreaField("Contenido HTML", validators=[Optional()], render_kw={"rows": 10})
    contenido_sfdt = TextAreaField("Contenido SFDT", validators=[Optional()], render_kw={"rows": 10})
    esta_archivado = BooleanField("Está Archivada", validators=[Optional()])
    guardar = SubmitField("Guardar")
