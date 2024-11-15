"""
Exh Exhortos, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import DateTimeField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.exh_areas.models import ExhArea


class ExhExhortoNewForm(FlaskForm):
    """Formulario New Exhorto"""

    # Campos solo lectura
    exhorto_origen_id = StringField("Exhorto Origen ID", validators=[Optional()])
    estado_origen = StringField("Estado Origen", validators=[Optional()])
    fecha_origen = StringField("Fecha Origen", validators=[Optional()])
    folio_seguimiento = StringField("Folio de Seguimiento", validators=[Optional()])
    estado = StringField("Estado", validators=[Optional()])

    # Campos select con opciones que se cargan con javascript
    municipio_origen = SelectField("Municipio Origen", choices=None, validate_choice=False, validators=[DataRequired()])
    estado_destino = SelectField("Estado Destino", choices=None, validate_choice=False, validators=[DataRequired()])
    municipio_destino = SelectField("Municipio Destino", choices=None, validate_choice=False, validators=[DataRequired()])
    materia = SelectField("Materia", choices=None, validate_choice=False, validators=[DataRequired()])

    # Campos Select2
    juzgado_origen = SelectField("Juzgado Origen", coerce=int, validate_choice=False, validators=[DataRequired()])

    # Campos
    numero_expediente_origen = StringField("Número de Expediente Origen", validators=[DataRequired(), Length(max=256)])
    numero_oficio_origen = StringField("Número de Oficio Origen", validators=[Optional(), Length(max=256)])
    tipo_juicio_asunto_delitos = StringField("Tipo de Juicio Asunto Delitos", validators=[DataRequired(), Length(max=256)])
    juez_exhortante = StringField("Juez Exhortante", validators=[Optional(), Length(max=256)])
    fojas = IntegerField("Fojas", validators=[DataRequired()])
    dias_responder = IntegerField("Días Responder", validators=[DataRequired()])
    tipo_diligenciacion_nombre = StringField("Tipo Diligenciación Nombre", validators=[Optional(), Length(max=256)])
    observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=1024)])
    crear = SubmitField("Crear")


class ExhExhortoEditForm(FlaskForm):
    """Formulario Edit Exhorto"""

    # Campos solo lectura
    exhorto_origen_id = StringField("Exhorto Origen ID", validators=[Optional()])
    fecha_origen = StringField("Fecha Origen", validators=[Optional()])
    folio_seguimiento = StringField("Folio de Seguimiento", validators=[Optional()])
    exh_area = StringField("Área", validators=[Optional()])
    remitente = StringField("Remitente", validators=[Optional()])
    distrito = StringField("Distrito", validators=[Optional()])
    autoridad = StringField("Autoridad", validators=[Optional()])
    numero_exhorto = StringField("Número de Exhorto", validators=[Optional()])
    estado = StringField("Estado", validators=[Optional()])

    # Campos select con opciones que se cargan con javascript
    estado_origen = SelectField("Estado Origen", choices=None, validate_choice=False, validators=[DataRequired()])
    municipio_origen = SelectField("Municipio Origen", choices=None, validate_choice=False, validators=[DataRequired()])
    estado_destino = SelectField("Estado Destino", choices=None, validate_choice=False, validators=[DataRequired()])
    municipio_destino = SelectField("Municipio Destino", choices=None, validate_choice=False, validators=[DataRequired()])
    materia = SelectField("Materia", choices=None, validate_choice=False, validators=[DataRequired()])

    # Campos Select2
    juzgado_origen = SelectField("Juzgado Origen", coerce=int, validate_choice=False, validators=[DataRequired()])

    # Campos
    numero_expediente_origen = StringField("Número de Expediente Origen", validators=[DataRequired(), Length(max=256)])
    numero_oficio_origen = StringField("Número de Oficio Origen", validators=[Optional(), Length(max=256)])
    tipo_juicio_asunto_delitos = StringField("Tipo de Juicio Asunto Delitos", validators=[DataRequired(), Length(max=256)])
    juez_exhortante = StringField("Juez Exhortante", validators=[Optional(), Length(max=256)])
    fojas = IntegerField("Fojas", validators=[DataRequired()])
    dias_responder = IntegerField("Días Responder", validators=[DataRequired()])
    tipo_diligenciacion_nombre = StringField("Tipo Diligenciación Nombre", validators=[Optional(), Length(max=256)])
    observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=1024)])
    guardar = SubmitField("Guardar")


class ExhExhortoSendManuallyForm(FlaskForm):
    """Formulario Enviar Manualmente Exhorto"""

    folio_seguimiento = StringField("Folio de Seguimiento", validators=[DataRequired()])
    acuse_fecha_hora_recepcion = DateTimeField("Fecha Hora de Recepción", validators=[DataRequired()])
    # acuse_municipio_area_recibe_id
    acuse_area_recibe_id = StringField("Área ID", validators=[DataRequired(), Length(max=256)])
    acuse_area_recibe_nombre = StringField("Área Nombre", validators=[DataRequired(), Length(max=256)])
    acuse_url_info = StringField("URL info", validators=[Optional(), Length(max=256)])
    recibir = SubmitField("Recibir")


class ExhExhortoRecibeResponseManuallyForm(FlaskForm):
    """Formulario Recibir respuesta Manualmente Exhorto"""

    respuesta_respuesta_origen_id = StringField("Respuesta Origen ID", validators=[DataRequired()])
    respuesta_observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=1024)])
    respuesta_fecha_hora_recepcion = DateTimeField("Fecha Hora de Recepción", validators=[DataRequired()])
    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    recibir = SubmitField("Recibir")


class ExhExhortoTransferForm(FlaskForm):
    """Formulario Transferir Exhorto"""

    exh_area = SelectField("Área", coerce=int, validators=[DataRequired()])
    distrito = SelectField("Distrito", choices=None, validate_choice=False, validators=[DataRequired()])
    autoridad = SelectField("Autoridad", choices=None, validate_choice=False, validators=[DataRequired()])
    transferir = SubmitField("Transferir")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para materia y exh_area"""
        super().__init__(*args, **kwargs)
        self.exh_area.choices = [
            (m.id, m.clave + " - " + m.nombre) for m in ExhArea.query.filter_by(estatus="A").order_by(ExhArea.clave).all()
        ]


class ExhExhortoProcessForm(FlaskForm):
    """Formulario Procesar Exhorto"""

    numero_exhorto = StringField("Número de Exhorto", validators=[Optional(), Length(max=256)])
    procesar = SubmitField("Procesar")


class ExhExhortoRefuseForm(FlaskForm):
    """Formulario Rechazar Exhorto"""

    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    rechazar = SubmitField("Rechazar")


class ExhExhortoDiligenceForm(FlaskForm):
    """Formulario Diligenciar Exhorto"""

    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    diligenciar = SubmitField("Diligenciar")


class ExhExhortoResponseForm(FlaskForm):
    """Formulario Contestar Exhorto"""

    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    contestar = SubmitField("Contestar")
