"""
Listas de Acuerdos, formularios
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import DateField, FileField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from hercules.blueprints.materias.models import Materia


class ListaDeAcuerdoNewForm(FlaskForm):
    """Formulario ListaDeAcuerdo para un Juzgado con una Materia"""

    distrito = StringField("Distrito")  # Read only
    autoridad = StringField("Autoridad")  # Read only
    fecha = DateField("Fecha (si ya existe otra con la misma fecha, será reemplazada)", validators=[DataRequired()])
    archivo = FileField("Archivo PDF con la Lista de Acuerdos", validators=[FileRequired()])
    guardar = SubmitField("Guardar")


class ListaDeAcuerdoMateriaNewForm(FlaskForm):
    """Formulario ListaDeAcuerdo para un Juzgado que puede seleccionar la Materia"""

    distrito = StringField("Distrito")  # Read only
    autoridad = StringField("Autoridad")  # Read only
    materia = SelectField("Materia", coerce=int, validators=[DataRequired()])
    fecha = DateField("Fecha (si ya existe otra con la misma fecha, será reemplazada)", validators=[DataRequired()])
    archivo = FileField("Archivo PDF con la Lista de Acuerdos", validators=[FileRequired()])
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones de materia"""
        super().__init__(*args, **kwargs)
        self.materia.choices = [(m.id, m.nombre) for m in Materia.query.filter_by(estatus="A").order_by(Materia.nombre).all()]
