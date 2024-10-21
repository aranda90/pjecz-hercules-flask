"""
Funcionario Oficinas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from hercules.blueprints.oficinas.models import Oficina


class FuncionarioOficinaForm(FlaskForm):
    """Formulario FuncionarioOficina"""

    funcionario = StringField("Funcionario")  # Read only
    oficina = SelectField("Oficina", coerce=int)  # Select2
    guardar = SubmitField("Guardar")
