"""
Exh Exhortos Promoventes, formularios
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, RadioField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from hercules.blueprints.exh_exhortos_promoventes.models import ExhExhortoPromovente

from lib.safe_string import TELEFONO_REGEXP


class ExhExhortoPromoventeForm(FlaskForm):
    """Formulario para agregar o editar un promovente"""

    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=256)])
    apellido_paterno = StringField("Apellido Paterno", validators=[Optional(), Length(max=256)])
    apellido_materno = StringField("Apellido Materno", validators=[Optional(), Length(max=256)])
    genero = RadioField("Genero", coerce=str, choices=ExhExhortoPromovente.GENEROS.items(), validators=[DataRequired()])
    es_persona_moral = BooleanField("Es Persona Moral")
    tipo_parte = SelectField(
        "Tipo de Promovente", coerce=int, choices=ExhExhortoPromovente.TIPOS_PARTES.items(), validators=[Optional()]
    )
    tipo_parte_nombre = StringField("Tipo Promovente Nombre")
    correo_electronico = StringField("Correo Electrónico", validators=[Optional(), Length(max=256)])
    telefono = StringField("Teléfono (10 dígitos)", validators=[Optional(), Length(min=10, max=10), Regexp(TELEFONO_REGEXP)])
    guardar = SubmitField("Guardar")
