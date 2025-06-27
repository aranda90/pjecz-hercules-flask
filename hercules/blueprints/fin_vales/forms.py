"""
Financieros Vales, formularios
"""

from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.fin_vales.models import FinVale

MONTOS = [
    ("100.0", "$100.00"),
    ("200.0", "$200.00"),
    ("300.0", "$300.00"),
    ("500.0", "$500.00"),
]


class FinValeEditForm(FlaskForm):
    """Formulario para editar un vale"""

    usuario_email = SelectField("Quien lo usará", coerce=str, validators=[Optional()], validate_choice=False)  # Select2
    solicito_email = SelectField("Quien lo solicitará", coerce=str, validators=[Optional()], validate_choice=False)  # Select2
    autorizo_email = SelectField("Quien lo autorizará", coerce=str, validators=[Optional()], validate_choice=False)  # Select2
    justificacion = TextAreaField("Justificación", validators=[DataRequired(), Length(max=1024)], render_kw={"rows": 4})
    monto = SelectField("Monto", choices=MONTOS, validators=[DataRequired()])
    actualizar = SubmitField("Actualizar")


class FinValeStep1CreateForm(FlaskForm):
    """Formulario paso 1 crear FinVale"""

    usuario_email = StringField("Quien lo usará")  # Read only
    solicito_email = StringField("Quien lo solicitará")  # Read only
    autorizo_email = StringField("Quien lo autorizará")  # Read only
    justificacion = TextAreaField("Justificación", validators=[DataRequired(), Length(max=1024)], render_kw={"rows": 4})
    monto = SelectField("Monto", choices=MONTOS, validators=[DataRequired()])
    guardar = SubmitField("Guardar")


class FinValeStep2RequestForm(FlaskForm):
    """Formulario paso 2 solicitar FinVale"""

    contrasena = PasswordField("Contraseña de su firma electrónica", validators=[DataRequired(), Length(6, 64)])
    solicitar = SubmitField("Solicitar")


class FinValeCancel2RequestForm(FlaskForm):
    """Formulario cancelar solicitado FinVale"""

    motivo = StringField("Motivo", validators=[DataRequired(), Length(max=256)])
    contrasena = PasswordField("Contraseña de su firma electrónica", validators=[DataRequired(), Length(6, 64)])
    cancelar = SubmitField("Cancelar")


class FinValeStep3AuthorizeForm(FlaskForm):
    """Formulario paso 3 autorizar FinVale"""

    contrasena = PasswordField("Contraseña de su firma electrónica", validators=[DataRequired(), Length(6, 64)])
    autorizar = SubmitField("Autorizar")


class FinValeCancel3AuthorizeForm(FlaskForm):
    """Formulario cancelar autorizado FinVale"""

    motivo = StringField("Motivo", validators=[DataRequired(), Length(max=256)])
    contrasena = PasswordField("Contraseña de su firma electrónica", validators=[DataRequired(), Length(6, 64)])
    cancelar = SubmitField("Cancelar")


class FinValeStep4DeliverForm(FlaskForm):
    """Formulario paso 4 entregar FinVale"""

    folio = IntegerField("Folio", validators=[DataRequired()])
    entregar = SubmitField("Entregar")


class FinValeStep5AttachmentsForm(FlaskForm):
    """Formulario paso 5 adjuntar FinVale"""

    vehiculo_descripcion = StringField("Descripción del vehículo", validators=[DataRequired(), Length(max=256)])
    tanque_inicial = StringField("Tanque inicial", validators=[Optional(), Length(max=48)])
    tanque_final = StringField("Tanque final", validators=[Optional(), Length(max=48)])
    kilometraje_inicial = IntegerField("Kilometraje inicial", validators=[Optional()])
    kilometraje_final = IntegerField("Kilometraje final", validators=[Optional()])
    concluir = SubmitField("Concluir entrega de adjuntos")


class FinValeStep6ArchiveForm(FlaskForm):
    """Formulario paso 6 archivar FinVale"""

    notas = TextAreaField("Notas", validators=[DataRequired(), Length(max=1020)])
    archivar = SubmitField("Archivar")
