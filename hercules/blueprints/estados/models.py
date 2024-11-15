"""
Estados, modelos
"""

from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class Estado(database.Model, UniversalMixin):
    """Estado"""

    # Nombre de la tabla
    __tablename__ = "estados"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    nombre: Mapped[str] = mapped_column(String(256))

    # Hijos
    exh_externos: Mapped[List["ExhExterno"]] = relationship("ExhExterno", back_populates="estado")
    municipios: Mapped[List["Municipio"]] = relationship("Municipio", back_populates="estado")

    def __repr__(self):
        """Representación"""
        return f"<Estado {self.clave}>"
