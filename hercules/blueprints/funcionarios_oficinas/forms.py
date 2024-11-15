"""
Funcionario Oficinas, formularios
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField

from hercules.blueprints.oficinas.models import Oficina


class FuncionarioOficinaForm(FlaskForm):
    """Formulario FuncionarioOficina"""

    funcionario = StringField("Funcionario")  # Read only
    oficina = SelectField("Oficina", coerce=int)  # Select2
    guardar = SubmitField("Guardar")

    def __init__(self, *args, **kwargs):
        """Inicializar y cargar opciones en distrito"""
        super().__init__(*args, **kwargs)
        self.oficina.choices = [
            (o.id, o.clave + " - " + o.descripcion_corta)
            for o in Oficina.query.filter_by(estatus="A").order_by(Oficina.clave).all()
        ]
