"""
Exhortos - Promociones, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ExhExhortoPromocion(database.Model, UniversalMixin):
    """ExhExhortoPromocion"""

    REMITENTES = {
        "INTERNO": "Interno",
        "EXTERNO": "Externo",
    }

    ESTADOS = {
        "PENDIENTE": "Pendiente",
        "ENVIADO": "Enviado",
    }

    # Nombre de la tabla
    __tablename__ = "exh_exhortos_promociones"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    exh_exhorto_id: Mapped[int] = mapped_column(ForeignKey("exh_exhortos.id"))
    exh_exhorto: Mapped["ExhExhorto"] = relationship(back_populates="exh_exhortos_promociones")

    # Columnas
    # Identificador del origen de la promoción; éste puede ser el folio del oficio u otro documento desde donde partió la promoción
    folio_origen_promocion: Mapped[str] = mapped_column(String(16))

    # Hijo: Contiene la definición de los promoventes, en este caso el juzgado quien realiza la promoción
    exh_exhortos_promociones_promoventes: Mapped[List["ExhExhortoPromocionPromovente"]] = relationship(
        back_populates="exh_exhorto_promocion"
    )

    # Número de fojas que contiene la promoción.
    # El valor 0 significa "No Especificado".
    fojas: Mapped[int]

    # Fecha y hora en que el Poder Judicial promovente registró que se envió la promoción en su hora local.
    # En caso de no enviar este dato, el Poder Judicial promovido puede tomar su fecha hora local.
    fecha_origen: Mapped[Optional[datetime]] = mapped_column(DateTime, default=now())

    # Texto simple que contenga información extra o relevante sobre el exhorto.
    observaciones: Mapped[Optional[str]] = mapped_column(String(1024))

    # Hijo: Colección de los datos referentes a los archivos que se van a recibir el Poder Judicial exhortado en el envío del Exhorto.
    exh_exhortos_promociones_archivos: Mapped[List["ExhExhortoPromocionArchivo"]] = relationship(
        back_populates="exh_exhorto_promocion"
    )

    # Si el remitente es INTERNO entonces fue creada por nosotros, si es EXTERNO fue creada por otro PJ
    remitente: Mapped[str] = mapped_column(
        Enum(*REMITENTES, name="exh_exhortos_promociones_remitentes", native_enum=False), index=True
    )

    # Estado de la promoción, puede ser PENDIENTE o ENVIADO
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="exh_exhortos_promociones_estados", native_enum=False), index=True)

    def __repr__(self):
        """Representación"""
        return f"<ExhExhortoPromocion {self.id}>"
