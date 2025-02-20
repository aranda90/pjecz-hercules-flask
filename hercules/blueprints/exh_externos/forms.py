"""
Exh Externos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from hercules.blueprints.estados.models import Estado


class ExhExternoForm(FlaskForm):
    """Formulario ExhExterno"""

    clave = StringField("Clave", validators=[DataRequired(), Length(max=16)])
    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    estado = SelectField("Estado", coerce=int, validators=[DataRequired()])
    api_key = StringField("API Key", validators=[Optional(), Length(max=128)])
    endpoint_consultar_materias = StringField("Materias", validators=[Optional()])
    endpoint_recibir_exhorto = StringField("Recibir Exhorto", validators=[Optional()])
    endpoint_recibir_exhorto_archivo = StringField("Recibir Exhorto Archivo", validators=[Optional()])
    endpoint_consultar_exhorto = StringField("Consultar Exhorto", validators=[Optional()])
    endpoint_recibir_respuesta_exhorto = StringField("Recibir Respuesta Exhorto", validators=[Optional()])
    endpoint_recibir_respuesta_exhorto_archivo = StringField("Recibir Respuesta Exhorto Archivo", validators=[Optional()])
    endpoint_actualizar_exhorto = StringField("Actualizar Exhorto", validators=[Optional()])
    endpoint_recibir_promocion = StringField("Recibir Promoción", validators=[Optional()])
    endpoint_recibir_promocion_archivo = StringField("Recibir Promoción Archivo", validators=[Optional()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones de estados"""
        super().__init__(*args, **kwargs)
        self.estado.choices = [(d.id, d.nombre) for d in Estado.query.filter_by(estatus="A").order_by(Estado.nombre).all()]
