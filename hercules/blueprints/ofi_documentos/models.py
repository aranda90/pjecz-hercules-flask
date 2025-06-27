"""
Ofi Documentos, modelos
"""

import hashlib
from datetime import datetime, date
from typing import List, Optional
import uuid

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class OfiDocumento(database.Model, UniversalMixin):
    """OfiDocumento"""

    ESTADOS = {
        "BORRADOR": "Borrador",
        "FIRMADO": "Firmado",
        "ENVIADO": "Enviado",
    }

    # Nombre de la tabla
    __tablename__ = "ofi_documentos"

    # Clave primaria
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="ofi_documentos")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="ofi_documentos_estados", native_enum=False), index=True)
    cadena_oficio_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    esta_archivado: Mapped[bool] = mapped_column(default=False)
    esta_cancelado: Mapped[bool] = mapped_column(default=False)
    vencimiento_fecha: Mapped[Optional[date]]
    enviado_tiempo: Mapped[Optional[datetime]]

    # El folio es None cuando el estado es BORRADOR
    # Cuando se firma el documento, se genera un folio y se separa su año y número
    folio: Mapped[Optional[str]] = mapped_column(String(64))
    folio_anio: Mapped[Optional[int]]
    folio_num: Mapped[Optional[int]]

    # Columnas contenido
    contenido_html: Mapped[Optional[str]] = mapped_column(Text)
    contenido_md: Mapped[Optional[str]] = mapped_column(Text)
    contenido_sfdt: Mapped[Optional[JSONB]] = mapped_column(JSONB)  # Syncfusion Document Editor

    # Columnas firma electronica simple
    firma_simple: Mapped[str] = mapped_column(String(256), default="")
    firma_simple_tiempo: Mapped[Optional[datetime]]
    firma_simple_usuario_id: Mapped[Optional[int]]

    # Columnas firma electronica avanzada
    firma_avanzada_nombre: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_puesto: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_email: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_efirma_tiempo: Mapped[Optional[datetime]]
    firma_avanzada_efirma_folio: Mapped[Optional[int]]
    firma_avanzada_efirma_sello_digital: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_efirma_url: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_efirma_qr_url: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_efirma_mensaje: Mapped[Optional[str]] = mapped_column(String(512))
    firma_avanzada_efirma_error: Mapped[Optional[str]] = mapped_column(String(512))
    firma_avanzada_cancelo_tiempo: Mapped[Optional[datetime]]
    firma_avanzada_cancelo_motivo: Mapped[Optional[str]] = mapped_column(String(256))
    firma_avanzada_cancelo_error: Mapped[Optional[str]] = mapped_column(String(512))

    # Hijos
    ofi_documentos_adjuntos: Mapped[List["OfiDocumentoAdjunto"]] = relationship(back_populates="ofi_documento")
    ofi_documentos_destinatarios: Mapped[List["OfiDocumentoDestinatario"]] = relationship(back_populates="ofi_documento")

    def elaborar_firma(self):
        """Generate a hash representing the current sample state"""
        elementos = []
        elementos.append(str(self.id))
        elementos.append(self.descripcion)
        elementos.append(str(self.folio))
        elementos.append(str(self.contenido_sfdt))
        return hashlib.md5("|".join(elementos).encode("utf-8")).hexdigest()

    def __repr__(self):
        """Representación"""
        return f"<OfiDocumento {self.id}>"
