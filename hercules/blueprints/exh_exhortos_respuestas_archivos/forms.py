"""
Exh Exhortos Respuestas Archivos, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length

from hercules.blueprints.exh_exhortos_respuestas_archivos.models import ExhExhortoRespuestaArchivo


class ExhExhortoRespuestaArchivoNewForm(FlaskForm):
    """Formulario ExhExhortoArchivoNew"""

    tipo_documento = SelectField(
        "Tipo", coerce=int, choices=ExhExhortoRespuestaArchivo.TIPOS_DOCUMENTOS.items(), validators=[DataRequired()]
    )
    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    subir = SubmitField("Subir")


class ExhExhortoRespuestaArchivoEditForm(FlaskForm):
    """Formulario para Editar"""

    nombre_archivo = StringField("Nombre del Archivo", validators=[DataRequired(), Length(max=256)])
    hash_sha1 = StringField("Hash SHA-1")  # Read only
    hash_sha256 = StringField("Hash SHA-256")  # Read only
    tipo_documento = SelectField(
        "Tipo", coerce=int, choices=ExhExhortoRespuestaArchivo.TIPOS_DOCUMENTOS.items(), validators=[DataRequired()]
    )
    url = StringField("URL")
    tamano = StringField("Tamaño")
    fecha_hora_recepcion = StringField("Fecha y hora de recepción")
    guardar = SubmitField("Guardar")
