"""
Ofi Documentos Destinatarios, modelos
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class OfiDocumentoDestinatario(database.Model, UniversalMixin):
    """OfiDocumentoDestinatario"""

    # Nombre de la tabla
    __tablename__ = "ofi_documentos_destinatarios"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clave foránea
    ofi_documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ofi_documentos.id"))
    ofi_documento: Mapped["OfiDocumento"] = relationship(back_populates="ofi_documentos_destinatarios")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="ofi_documentos_destinatarios")

    # Columnas
    con_copia: Mapped[bool] = mapped_column(default=False)
    fue_leido: Mapped[bool] = mapped_column(default=False)
    fue_leido_tiempo: Mapped[Optional[datetime]]

    def __repr__(self):
        """Representación"""
        return f"<OfiDocumentoDestinatario {self.id}>"
