"""
Ofi Documentos Destinatarios, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, Optional


class OfiDocumentoDestinatarioForm(FlaskForm):
    """Formulario OfiDocumentoDestinatario"""

    ofi_documento = StringField("Oficio")  # Read-Only
    usuario = SelectField("Usuario", coerce=int, validate_choice=False, validators=[DataRequired()])
    con_copia = BooleanField("Con Copia", validators=[Optional()])
    guardar = SubmitField("Guardar")
