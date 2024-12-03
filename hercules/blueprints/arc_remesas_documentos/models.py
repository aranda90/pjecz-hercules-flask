"""
Archivo - Remesas Documentos, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, JSON, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from lib.universal_mixin import UniversalMixin
from hercules.extensions import database


class ArcRemesaDocumento(database.Model, UniversalMixin):
    """ArcRemesaDocumento"""

    TIPOS = {
        "TRADICIONAL": "Tradicional",
        "ORAL": "Oral",
    }

    ANOMALIAS = {
        "EXPEDIENTE CON NUMERO INCORRECTO": "Expediente con número incorrecto",
        "EXPEDIENTE CON ANO INCORRECTO": "Expediente con año incorrecto",
        "EXPEDIENTE ENLISTADO Y NO ENVIADO": "Expediente enlistado y no enviado",
        "EXPEDIENTE CON PARTES INCORRECTAS": "Expediente con partes incorrectas",
        "EXPEDIENTE SIN FOLIAR": "Expediente sin foliar",
        "EXPEDIENTE FOLIADO INCORRECTAMENTE": "Expediente foliado incorrectamente",
        "EXPEDIENTE DESGLOSADO": "Expediente desglosado",
        "EXPEDIENTE CON CARATULA EN MAL ESTADO": "Expediente con caratula en mal estado",
        "EXPEDIENTE SIN CARATULA": "Expediente sin caratula",
        "EXPEDIENTE SIN ESPECIFICACION DE TOMOS ENVIADOS": "Expediente sin especificación de tomos enviados",
        "EXPEDIENTE CON CAPTURA ERRONEA DE FOJAS": "Expediente con captura errónea de fojas",
    }

    # Nombre de la tabla
    __tablename__ = "arc_remesas_documentos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    arc_documento_id: Mapped[int] = mapped_column(ForeignKey("arc_documentos.id"))
    arc_documento: Mapped["ArcDocumento"] = relationship(back_populates="arc_remesas_documentos")
    arc_remesa_id: Mapped[int] = mapped_column(ForeignKey("arc_remesas.id"))
    arc_remesa: Mapped["ArcRemesa"] = relationship(back_populates="arc_remesas_documentos")

    # Columnas
    anomalia: Mapped[str] = mapped_column(
        Enum(*ANOMALIAS, name="arc_remesas_documentos_anomalias", native_enum=False), index=True
    )
    fojas: Mapped[int]
    observaciones_solicitante: Mapped[str] = mapped_column(String(256))
    observaciones_archivista: Mapped[str] = mapped_column(String(256))
    tipo_juzgado: Mapped[str] = mapped_column(Enum(*TIPOS, name="arc_remesas_documentos_tipos", native_enum=False), index=True)

    def __repr__(self):
        """Representación"""
        return f"<ArcRemesaDocumento {self.id}>"
