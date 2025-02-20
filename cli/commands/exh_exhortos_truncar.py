"""
Exh Exhortos Truncar
"""

from sqlalchemy import text

from hercules.app import create_app
from hercules.extensions import database

app = create_app()
app.app_context().push()
database.app = app


def truncar() -> str:
    """Truncar la tabla de exhortos"""
    database.session.execute(text("TRUNCATE TABLE exh_exhortos RESTART IDENTITY CASCADE;"))
    database.session.commit()
    return "Ya no debe de haber registros en la tabla exh_extortos y en sus tablas relacionadas"
