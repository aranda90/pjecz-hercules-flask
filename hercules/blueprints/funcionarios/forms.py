"""
Funcionarios, formularios
"""

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, Regexp

from hercules.blueprints.centros_trabajos.models import CentroTrabajo
from hercules.blueprints.domicilios.models import Domicilio
from lib.safe_string import CURP_REGEXP


class FuncionarioAdminForm(FlaskForm):
    """Formulario Funcionario"""

    nombres = StringField("Nombres", validators=[DataRequired(), Length(max=256)])
    apellido_paterno = StringField("Apellido paterno", validators=[DataRequired(), Length(max=256)])
    apellido_materno = StringField("Apellido materno", validators=[Optional(), Length(max=256)])
    curp = StringField("CURP", validators=[DataRequired(), Length(min=18, max=18), Regexp(CURP_REGEXP, 0, "CURP inválida")])
    puesto = StringField("Puesto", validators=[Optional(), Length(max=256)])
    email = StringField("e-mail", validators=[DataRequired(), Email()])
    telefono = StringField("Teléfono", validators=[Optional(), Length(max=48)])
    extension = StringField("Extensión", validators=[Optional(), Length(max=16)])
    en_funciones = BooleanField("En funciones", validators=[Optional()])
    en_sentencias = BooleanField("En sentencias", validators=[Optional()])
    en_soportes = BooleanField("En soportes", validators=[Optional()])
    en_tesis_jurisprudencias = BooleanField("En tesis y jurisprudencias", validators=[Optional()])
    centro_trabajo = SelectField("Centro de trabajo", coerce=int, validators=[DataRequired()])
    ingreso_fecha = DateField("Fecha de ingreso", validators=[DataRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones de Centros de trabajos"""
        super().__init__(*args, **kwargs)
        self.centro_trabajo.choices = [
            (c.id, c.nombre) for c in CentroTrabajo.query.filter_by(estatus="A").order_by(CentroTrabajo.nombre).all()
        ]


class FuncionarioEditForm(FlaskForm):
    """Formulario para editar un funcionario"""

    nombre = StringField("Nombre")  # Read only
    puesto = StringField("Puesto")  # Read only
    email = StringField("e-mail")  # Read only
    telefono = StringField("Teléfono", validators=[Optional(), Length(max=48)])
    extension = StringField("Extensión", validators=[Optional(), Length(max=16)])
    guardar = SubmitField("Guardar")


class FuncionarioDomicilioForm(FlaskForm):
    """Formulario para relacionar oficinas al funcionario a partir de una direccion"""

    funcionario_nombre = StringField("Nombre")  # Read only
    funcionario_puesto = StringField("Puesto")  # Read only
    funcionario_email = StringField("e-mail")  # Read only
    domicilio = SelectField("Domicilio", coerce=int, validators=[DataRequired()])
    asignar = SubmitField("Asignar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones de Domicilios"""
        super().__init__(*args, **kwargs)
        self.domicilio.choices = [
            (d.id, d.completo) for d in Domicilio.query.filter_by(estatus="A").order_by(Domicilio.completo).all()
        ]
