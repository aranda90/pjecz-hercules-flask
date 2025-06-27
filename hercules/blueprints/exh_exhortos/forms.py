"""
Exh Exhortos, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

from hercules.blueprints.exh_areas.models import ExhArea
from lib.safe_string import EXPEDIENTE_REGEXP


class ExhExhortoNewForm(FlaskForm):
    """Formulario para crear un nuevo exhorto"""

    # Campos solo lectura
    exhorto_origen_id = StringField("Exhorto Origen ID", validators=[Optional()])
    estado_origen = StringField("Estado Origen", validators=[Optional()])
    fecha_origen = StringField("Fecha Origen", validators=[Optional()])
    folio_seguimiento = StringField("Folio de Seguimiento", validators=[Optional()])

    # Campos select con opciones que se cargan con javascript
    municipio_origen = SelectField("Municipio Origen", choices=None, validate_choice=False, validators=[DataRequired()])
    estado_destino = SelectField("Estado Destino", choices=None, validate_choice=False, validators=[DataRequired()])
    municipio_destino = SelectField("Municipio Destino", choices=None, validate_choice=False, validators=[DataRequired()])
    materia = SelectField("Materia", choices=None, validate_choice=False, validators=[DataRequired()])
    tipo_diligencia = SelectField(
        "Tipo Diligencia (si es OTROS escriba el nombre)", choices=None, validate_choice=False, validators=[DataRequired()]
    )

    # Campos Select2
    juzgado_origen = SelectField("Juzgado Origen", coerce=int, validate_choice=False, validators=[DataRequired()])

    # Campos
    numero_expediente_origen = StringField(
        "Número de Expediente Origen", validators=[DataRequired(), Regexp(EXPEDIENTE_REGEXP)]
    )
    numero_oficio_origen = StringField("Número de Oficio Origen", validators=[Optional(), Regexp(EXPEDIENTE_REGEXP)])
    tipo_juicio_asunto_delitos = StringField("Tipo de Juicio Asunto Delitos", validators=[DataRequired(), Length(max=256)])
    juez_exhortante = StringField("Juez Exhortante", validators=[Optional(), Length(max=256)])
    fojas = IntegerField("Fojas", validators=[DataRequired()])
    dias_responder = IntegerField("Días Responder", validators=[DataRequired()])
    tipo_diligenciacion_nombre = StringField("Tipo Diligenciación Nombre", validators=[Optional(), Length(max=256)])
    observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=1024)], render_kw={"rows": 6})
    guardar = SubmitField("Guardar")


class ExhExhortoEditForm(FlaskForm):
    """Formulario para editar un exhorto"""

    # Campos solo lectura
    exhorto_origen_id = StringField("Exhorto Origen ID", validators=[Optional()])
    estado_origen = StringField("Estado Origen", validators=[Optional()])
    fecha_origen = StringField("Fecha Origen", validators=[Optional()])
    folio_seguimiento = StringField("Folio de Seguimiento", validators=[Optional()])

    # Campos select con opciones que se cargan con javascript
    municipio_origen = SelectField("Municipio Origen", choices=None, validate_choice=False, validators=[DataRequired()])
    estado_destino = SelectField("Estado Destino", choices=None, validate_choice=False, validators=[DataRequired()])
    municipio_destino = SelectField("Municipio Destino", choices=None, validate_choice=False, validators=[DataRequired()])
    materia = SelectField("Materia", choices=None, validate_choice=False, validators=[DataRequired()])
    tipo_diligencia = SelectField("Tipo Diligencia", choices=None, validate_choice=False, validators=[DataRequired()])

    # Campos Select2
    juzgado_origen = SelectField("Juzgado Origen", coerce=int, validate_choice=False, validators=[DataRequired()])

    # Campos
    numero_expediente_origen = StringField("Número de Expediente Origen", validators=[DataRequired(), Length(max=256)])
    numero_oficio_origen = StringField("Número de Oficio Origen", validators=[Optional(), Length(max=256)])
    tipo_juicio_asunto_delitos = StringField("Tipo de Juicio Asunto Delitos", validators=[DataRequired(), Length(max=256)])
    juez_exhortante = StringField("Juez Exhortante", validators=[Optional(), Length(max=256)])
    fojas = IntegerField("Fojas", validators=[DataRequired()])
    dias_responder = IntegerField("Días Responder", validators=[DataRequired()])
    tipo_diligenciacion_nombre = StringField(
        "Tipo Diligenciación Nombre (cuando Tipo Diligencia es OTROS)", validators=[Optional(), Length(max=256)]
    )
    observaciones = TextAreaField("Observaciones", validators=[Optional(), Length(max=1024)], render_kw={"rows": 6})
    guardar = SubmitField("Guardar")


class ExhExhortoTransferForm(FlaskForm):
    """Formulario para transferir un exhorto"""

    exh_area = SelectField("Área", coerce=int, validators=[DataRequired()])
    distrito = SelectField("Distrito", choices=None, validate_choice=False, validators=[DataRequired()])
    autoridad = SelectField("Autoridad", choices=None, validate_choice=False, validators=[DataRequired()])
    transferir = SubmitField("Transferir")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones para materia y exh_area"""
        super().__init__(*args, **kwargs)
        self.exh_area.choices = [
            (a.id, a.clave + " - " + a.nombre) for a in ExhArea.query.filter_by(estatus="A").order_by(ExhArea.clave).all()
        ]


class ExhExhortoProcessForm(FlaskForm):
    """Formulario para procesar un exhorto"""

    numero_exhorto = StringField("Número de Exhorto", validators=[DataRequired(), Length(max=64)])
    procesar = SubmitField("Procesar")


class ExhExhortoRefuseForm(FlaskForm):
    """Formulario rechazar un exhorto"""

    archivo = FileField("Archivo PDF", validators=[FileRequired()])
    rechazar = SubmitField("Rechazar")
