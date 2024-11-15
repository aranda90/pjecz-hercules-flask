"""
Exh Externos, modelos
"""

from typing import Optional

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ExhExterno(database.Model, UniversalMixin):
    """ExhExterno"""

    # Nombre de la tabla
    __tablename__ = "exh_externos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    estado_id: Mapped[int] = mapped_column(ForeignKey("estados.id"))
    estado: Mapped["Estado"] = relationship(back_populates="exh_externos")

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))
    api_key: Mapped[Optional[str]] = mapped_column(String(128))

    # Columna materias es JSON con clave y nombre para cada una
    materias: Mapped[Optional[dict]] = mapped_column(JSON)

    # Columnas endpoints
    endpoint_consultar_materias: Mapped[Optional[str]] = mapped_column(String(256))
    endpoint_recibir_exhorto: Mapped[Optional[str]] = mapped_column(String(256))
    endpoint_recibir_exhorto_archivo: Mapped[Optional[str]] = mapped_column(String(256))
    endpoint_consultar_exhorto: Mapped[Optional[str]] = mapped_column(String(256))
    endpoint_recibir_respuesta_exhorto: Mapped[Optional[str]] = mapped_column(String(256))
    endpoint_recibir_respuesta_exhorto_archivo: Mapped[Optional[str]] = mapped_column(String(256))
    endpoint_actualizar_exhorto: Mapped[Optional[str]] = mapped_column(String(256))
    endpoint_recibir_promocion: Mapped[Optional[str]] = mapped_column(String(256))
    endpoint_recibir_promocion_archivo: Mapped[Optional[str]] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<ExhExterno {self.id}>"
