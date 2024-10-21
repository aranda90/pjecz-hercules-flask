"""
Usuarios, formularios
"""

from flask_wtf import FlaskForm
from wtforms import HiddenField, IntegerField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp

from hercules.blueprints.usuarios.models import Usuario
from lib.safe_string import CONTRASENA_REGEXP

CONTRASENA_MENSAJE = "De 8 a 48 caracteres con al menos una mayúscula, una minúscula y un número. No acentos, ni eñe."


class AccesoForm(FlaskForm):
    """Formulario de acceso al sistema"""

    siguiente = HiddenField()
    identidad = StringField("Correo electrónico o usuario", validators=[Optional(), Length(8, 256)])
    contrasena = PasswordField(
        "Contraseña",
        validators=[Optional(), Length(8, 48), Regexp(CONTRASENA_REGEXP, 0, CONTRASENA_MENSAJE)],
    )
    email = StringField("Correo electrónico", validators=[Optional(), Email()])
    token = StringField("Token", validators=[Optional()])
    guardar = SubmitField("Guardar")


class UsuarioForm(FlaskForm):
    """Formulario Usuario"""

    distrito = SelectField("Distrito", choices=None, validate_choice=False)  # Las opciones se agregan con JS
    autoridad = SelectField("Autoridad", choices=None, validate_choice=False)  # Las opciones se agregan con JS
    oficina = SelectField("Oficina", coerce=int)  # Select2
    email = StringField("e-mail", validators=[DataRequired(), Email()])
    nombres = StringField("Nombres", validators=[DataRequired(), Length(max=256)])
    apellido_paterno = StringField("Apellido primero", validators=[DataRequired(), Length(max=256)])
    apellido_materno = StringField("Apellido segundo", validators=[Optional(), Length(max=256)])
    curp = StringField("CURP habilita recibos de nómina", validators=[Optional(), Length(max=256)])
    puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    workspace = SelectField("Workspace", choices=Usuario.WORKSPACES.items(), validators=[DataRequired()])
    efirma_registro_id = IntegerField("ID eFirma habilita firma electrónica", validators=[Optional()])
    guardar = SubmitField("Guardar")
