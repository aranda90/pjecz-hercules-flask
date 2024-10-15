"""
Ubicaciones de Expedientes, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class UbicacionExpediente(database.Model, UniversalMixin):
    """UbicacionExpediente"""

    UBICACIONES = {
        "ARCHIVO": "Archivo",
        "JUZGADO": "Juzgado",
    }

    # Nombre de la tabla
    __tablename__ = "ubicaciones_expedientes"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="ubicaciones_expedientes")

    # Columnas
    expediente: Mapped[str] = mapped_column(String(16), index=True)
    ubicacion: Mapped[str] = mapped_column(
        Enum(*UBICACIONES, name="ubicaciones_expedientes_ubicaciones", native_enum=False), index=True
    )

    def __repr__(self):
        """Representación"""
        return f"<UbicacionExpediente {self.id}>"
