"""
Inventarios Modelos, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class InvModelo(database.Model, UniversalMixin):
    """InvModelo"""

    # Nombre de la tabla
    __tablename__ = "inv_modelos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    inv_marca_id: Mapped[int] = mapped_column(ForeignKey("inv_marcas.id"))
    inv_marca: Mapped["InvMarca"] = relationship(back_populates="inv_modelos")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))

    # Hijos
    inv_equipos: Mapped[List["InvEquipo"]] = relationship(back_populates="inv_modelo")

    def __repr__(self):
        """Representación"""
        return f"<InvModelo {self.id}>"
