"""
Cid Procedimientos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

from hercules.blueprints.cid_areas.models import CIDArea
from lib.wtforms import JSONField


class CIDProcedimientoForm(FlaskForm):
    """Formulario CID Procedimiento"""

    titulo_procedimiento = StringField("Título", validators=[DataRequired(), Length(max=256)])
    codigo = StringField("Código", validators=[DataRequired(), Length(max=16)])
    revision = IntegerField("Revisión (Número entero apartir de 1)", validators=[DataRequired()])
    fecha = DateField("Fecha de elaboración", validators=[DataRequired()])
    cid_area = StringField("Área")  # Read Only
    # Step Objetivo
    objetivo = JSONField("Objetivo", validators=[Optional()])
    # Step Alcance
    alcance = JSONField("Alcance", validators=[Optional()])
    # Step Documentos
    documentos = JSONField("Documentos", validators=[Optional()])
    # Step Definiciones
    definiciones = JSONField("Definiciones", validators=[Optional()])
    # Step Responsabilidades
    responsabilidades = JSONField("Responsabilidades", validators=[Optional()])
    # Step Desarrollo
    desarrollo = JSONField("Desarrollo", validators=[Optional()])
    # Step Registros
    registros = JSONField("Registros", validators=[Optional()])
    # Step Control de Cambios
    control_cambios = JSONField("Control de Cambios", validators=[Optional()])
    # Step Autorizaciones
    elaboro_nombre = StringField("Nombre", validators=[Optional(), Length(max=256)])
    elaboro_puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    elaboro_email = SelectField(label="Correo electrónico", coerce=str, validators=[Optional()], validate_choice=False)
    reviso_nombre = StringField("Nombre", validators=[Optional(), Length(max=256)])
    reviso_puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    reviso_email = SelectField(label="Correo electrónico", coerce=str, validators=[Optional()], validate_choice=False)
    aprobo_nombre = StringField("Nombre", validators=[Optional(), Length(max=256)])
    aprobo_puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    aprobo_email = SelectField(label="Correo electrónico", coerce=str, validators=[Optional()], validate_choice=False)
    autorizaciones = JSONField("Autorizaciones", validators=[Optional()])
    # Guardar
    guardar = SubmitField("Guardar")


class CIDProcedimientoEditForm(FlaskForm):
    """Formulario CID Procedimiento"""

    # Step Encabezado
    titulo_procedimiento = StringField("Título", validators=[DataRequired(), Length(max=256)])
    codigo = StringField("Código", validators=[Optional(), Length(max=16)])
    revision = IntegerField("Revisión (Número entero apartir de 1)", validators=[Optional()])
    fecha = DateField("Fecha de elaboración", validators=[DataRequired()])
    cid_area = StringField("Área")  # Read Only
    # Step Objetivo
    objetivo = JSONField("Objetivo", validators=[Optional()])
    # Step Alcance
    alcance = JSONField("Alcance", validators=[Optional()])
    # Step Documentos
    documentos = JSONField("Documentos", validators=[Optional()])
    # Step Definiciones
    definiciones = JSONField("Definiciones", validators=[Optional()])
    # Step Responsabilidades
    responsabilidades = JSONField("Responsabilidades", validators=[Optional()])
    # Step Desarrollo
    desarrollo = JSONField("Desarrollo", validators=[Optional()])
    # Step Registros
    registros = JSONField("Registros", validators=[Optional()])
    # Step Control de Cambios
    control_cambios = JSONField("Control de Cambios", validators=[Optional()])
    # Step Autorizaciones
    elaboro_nombre = StringField("Nombre", validators=[Optional(), Length(max=256)])
    elaboro_puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    elaboro_email = SelectField(label="Correo electrónico", coerce=str, validators=[Optional()], validate_choice=False)
    reviso_nombre = StringField("Nombre", validators=[Optional(), Length(max=256)])
    reviso_puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    reviso_email = SelectField(label="Correo electrónico", coerce=str, validators=[Optional()], validate_choice=False)
    aprobo_nombre = StringField("Nombre", validators=[Optional(), Length(max=256)])
    aprobo_puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    aprobo_email = SelectField(label="Correo electrónico", coerce=str, validators=[Optional()], validate_choice=False)
    autorizaciones = JSONField("Autorizaciones", validators=[Optional()])
    # Guardar
    guardar = SubmitField("Guardar")


class CIDProcedimientoAcceptRejectForm(FlaskForm):
    """Formaulario para Aceptar o Rechazar"""

    titulo_procedimiento = StringField("Título", validators=[DataRequired(), Length(max=256)])
    codigo = StringField("Código", validators=[DataRequired(), Length(max=16)])
    cid_area = StringField("Área")  # Read Only
    revision = IntegerField("Revisión", validators=[DataRequired()])
    seguimiento = StringField("Seguimiento", validators=[DataRequired()])
    seguimiento_posterior = StringField("Seguimiento posterior", validators=[DataRequired()])
    elaboro_nombre = StringField("Remitente Elaboró", validators=[Optional()])
    reviso_nombre = StringField("Remitente Revisó", validators=[Optional()])
    url = StringField("Archivo PDF", validators=[Optional()])
    aceptar = SubmitField("Aceptar")
    rechazar = SubmitField("Rechazar")


class CIDProcedimientoCambiarAreaForm(FlaskForm):
    """Formulario CIDProcedimientoCambiarArea"""

    titulo_procedimiento = StringField("Título")  # Read only
    codigo = StringField("Código")  # Read only
    cid_area_original = StringField("Área Original")
    cid_area = SelectField("Área", coerce=int, validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en inv_categoria"""
        super().__init__(*args, **kwargs)
        self.cid_area.choices = [
            (ca.id, ca.nombre) for ca in CIDArea.query.filter_by(estatus="A").order_by(CIDArea.nombre).all()
        ]


class CIDProcedimientosNewReview(FlaskForm):
    """Formulario nueva revision"""

    titulo_procedimiento = StringField("Título Procedimiento", validators=[Optional()])
    codigo = StringField("Código")  # Solo lectura
    revision = IntegerField("Nueva Revisión")  # Solo lectura
    cid_area = StringField("Área")  # Read Only
    fecha = DateField("Fecha de elaboración", validators=[DataRequired()])
    reviso_nombre = StringField("Nombre", validators=[Optional(), Length(max=256)])
    reviso_puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    reviso_email = SelectField(label="Correo electrónico", coerce=str, validators=[Optional()], validate_choice=False)
    aprobo_nombre = StringField("Nombre", validators=[Optional(), Length(max=256)])
    aprobo_puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    aprobo_email = SelectField(label="Correo electrónico", coerce=str, validators=[Optional()], validate_choice=False)
    guardar = SubmitField("Iniciar nueva revisión")
