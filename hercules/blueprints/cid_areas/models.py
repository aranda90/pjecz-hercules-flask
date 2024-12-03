"""
Cid Areas, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class CIDArea(database.Model, UniversalMixin):
    """CIDArea"""

    # Nombre de la tabla
    __tablename__ = "cid_areas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    nombre: Mapped[str] = mapped_column(String(256))
    descripcion: Mapped[str] = mapped_column(String(256))

    cid_areas_autoridades: Mapped[List["CIDAreaAutoridad"]] = relationship(back_populates="cid_area")
    cid_procedimientos: Mapped[List["CIDProcedimiento"]] = relationship(back_populates="cid_area")
    cid_formatos: Mapped[List["CIDFormato"]] = relationship(back_populates="cid_area")

    def __repr__(self):
        """Representación"""
        return f"<CIDArea {self.id}>"
