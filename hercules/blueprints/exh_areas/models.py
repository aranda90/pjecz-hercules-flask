"""
Exh Areas, modelos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ExhArea(database.Model, UniversalMixin):
    """ExhArea"""

    # Nombre de la tabla
    __tablename__ = "exh_areas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    nombre: Mapped[str] = mapped_column(String(256))

    # Hijos
    exh_exhortos: Mapped[List["ExhExhorto"]] = relationship("ExhExhorto", back_populates="exh_area")

    def __repr__(self):
        """Representación"""
        return f"<ExhArea {self.clave}>"
