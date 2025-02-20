"""
Exhortos Promociones, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class ExhExhortoPromocionNewForm(FlaskForm):
    """Formulario ExhExhortoPromocionNew"""

    folio_origen = StringField("Folio Origen")  # ReadOnly
    fojas = IntegerField("Fojas", validators=[DataRequired()])
    observaciones = TextAreaField("Observaciones", validators=[Optional()])
    crear = SubmitField("Crear")


class ExhExhortoPromocionEditForm(FlaskForm):
    """Formulario ExhExhortoPromocionEdit"""

    fecha_origen = StringField("Fecha Origen")  # Read-Only
    fojas = IntegerField("Fojas", validators=[DataRequired()])
    observaciones = TextAreaField("Observaciones", validators=[Optional()])
    guardar = SubmitField("Guardar")
