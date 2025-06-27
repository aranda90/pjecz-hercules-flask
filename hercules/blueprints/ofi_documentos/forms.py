"""
Ofi Documentos, formularios
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, DateField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, Regexp

FOLIO_REGEXP = r"^(\w.[-\/])*\d+\/\d{4}$"


class OfiDocumentoNewForm(FlaskForm):
    """Formulario para crear OfiDocumento"""

    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    folio = StringField("Folio (DD-NN/AAAA)", validators=[Optional(), Regexp(FOLIO_REGEXP)])
    vencimiento_fecha = DateField("Fecha de vencimiento", validators=[Optional()])
    contenido_md = TextAreaField("Contenido MD", validators=[Optional()], render_kw={"rows": 10})
    contenido_html = TextAreaField("Contenido HTML", validators=[Optional()], render_kw={"rows": 10})
    contenido_sfdt = TextAreaField("Contenido SFDT", validators=[Optional()], render_kw={"rows": 10})
    cadena_oficio_id = HiddenField("Cadena de Oficio", validators=[Optional()])
    guardar = SubmitField("Guardar")


class OfiDocumentoEditForm(FlaskForm):
    """Formulario para editar OfiDocumento"""

    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    folio = StringField("Folio (DD-NN/AAAA)", validators=[Optional(), Regexp(FOLIO_REGEXP)])
    vencimiento_fecha = DateField("Fecha de vencimiento", validators=[Optional()])
    contenido_md = TextAreaField("Contenido MD", validators=[Optional()], render_kw={"rows": 10})
    contenido_html = TextAreaField("Contenido HTML", validators=[Optional()], render_kw={"rows": 10})
    contenido_sfdt = TextAreaField("Contenido SFDT", validators=[Optional()], render_kw={"rows": 10})
    guardar = SubmitField("Guardar")


class OfiDocumentoSignForm(FlaskForm):
    """Formulario para firmar un OfiDocumento"""

    descripcion = StringField("Descripción", validators=[DataRequired(), Length(max=256)])
    folio = StringField("Folio (DD-NN/AAAA)", validators=[DataRequired(), Regexp(FOLIO_REGEXP)])
    contenido_md = TextAreaField("Contenido MD", validators=[Optional()], render_kw={"rows": 10})
    contenido_html = TextAreaField("Contenido HTML", validators=[Optional()], render_kw={"rows": 10})
    contenido_sfdt = TextAreaField("Contenido SFDT", validators=[Optional()], render_kw={"rows": 10})  # Read Only
    firmar = SubmitField("Firmar")
