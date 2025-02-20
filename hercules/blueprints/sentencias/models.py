"""
Sentencias, modelos
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class Sentencia(database.Model, UniversalMixin):
    """Sentencia"""

    # Nombre de la tabla
    __tablename__ = "sentencias"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="sentencias")
    materia_tipo_juicio_id: Mapped[int] = mapped_column(ForeignKey("materias_tipos_juicios.id"))
    materia_tipo_juicio: Mapped["MateriaTipoJuicio"] = relationship(back_populates="sentencias")

    # Columnas
    sentencia: Mapped[str] = mapped_column(String(16))
    sentencia_fecha: Mapped[Optional[date]] = mapped_column(Date(), index=True)
    expediente: Mapped[str] = mapped_column(String(16))
    expediente_anio: Mapped[int]
    expediente_num: Mapped[int]
    fecha: Mapped[date] = mapped_column(Date(), index=True)
    descripcion: Mapped[str] = mapped_column(String(1024))
    es_perspectiva_genero: Mapped[bool] = mapped_column(default=False)
    archivo: Mapped[str] = mapped_column(String(256), default="", server_default="")
    url: Mapped[str] = mapped_column(String(512), default="", server_default="")

    # Columnas para Retrieval-Augmented Generation (RAG)
    rag_fue_analizado_tiempo: Mapped[Optional[datetime]]
    rag_analisis: Mapped[Optional[dict]] = mapped_column(JSON)
    rag_fue_sintetizado_tiempo: Mapped[Optional[datetime]]
    rag_sintesis: Mapped[Optional[dict]] = mapped_column(JSON)
    rag_fue_categorizado_tiempo: Mapped[Optional[datetime]]
    rag_categorias: Mapped[Optional[dict]] = mapped_column(JSON)

    @property
    def descargar_url(self):
        """URL para descargar el archivo desde el sitio web"""
        if self.id:
            return f"https://www.pjecz.gob.mx/consultas/sentencias/descargar/?id={self.id}"
        return ""

    def __repr__(self):
        """Representación"""
        return f"<Sentencia {self.id}>"
