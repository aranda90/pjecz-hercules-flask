"""
Ofi Plantillas, modelos
"""

from typing import Optional
import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class OfiPlantilla(database.Model, UniversalMixin):
    """OfiPlantilla"""

    # Nombre de la tabla
    __tablename__ = "ofi_plantillas"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="ofi_plantillas")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    esta_archivado: Mapped[bool] = mapped_column(default=False)

    # Columnas contenido
    contenido_html: Mapped[Optional[str]] = mapped_column(Text)
    contenido_md: Mapped[Optional[str]] = mapped_column(Text)
    contenido_sfdt: Mapped[Optional[JSONB]] = mapped_column(JSONB)  # Syncfusion Document Editor

    def __repr__(self):
        """Representación"""
        return f"<OfiPlantilla {self.id}>"
