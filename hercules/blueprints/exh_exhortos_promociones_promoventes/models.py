"""
Exh Exhortos Promociones Promoventes, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ExhExhortoPromocionPromovente(database.Model, UniversalMixin):
    """ExhExhortoPromocionPromovente"""

    GENEROS = {
        "M": "MASCULINO",
        "F": "FEMENINO",
        "-": "SIN SEXO",
    }

    TIPOS_PARTES = {
        0: "No definido o se especifica en tipoParteNombre",
        1: "Actor, Promovente, Ofendido",
        2: "Demandado, Inculpado, Imputado",
    }

    # Nombre de la tabla
    __tablename__ = "exh_exhortos_promociones_promoventes"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    exh_exhorto_promocion_id: Mapped[int] = mapped_column(ForeignKey("exh_exhortos_promociones.id"))
    exh_exhorto_promocion: Mapped["ExhExhortoPromocion"] = relationship(back_populates="exh_exhortos_promociones_promoventes")

    # Nombre de la parte, en el caso de persona moral, solo en nombre de la empresa o razón social.
    nombre: Mapped[str] = mapped_column(String(256))

    # Apellido paterno de la parte. Solo cuando no sea persona moral. Opcional.
    apellido_paterno: Mapped[Optional[str]] = mapped_column(String(256))

    # Apellido materno de la parte, si es que aplica para la persona. Solo cuando no sea persona moral. Opcional.
    apellido_materno: Mapped[Optional[str]] = mapped_column(String(256))

    # 'M' = Masculino,
    # 'F' = Femenino.
    # Solo cuando aplique y se quiera especificar (que se tenga el dato). NO aplica para persona moral.
    genero: Mapped[str] = mapped_column(Enum(*GENEROS, name="exh_exhortos_promociones_promoventes_generos", native_enum=False))

    # Valor que indica si la parte es una persona moral.
    es_persona_moral: Mapped[bool]

    # Indica el tipo de parte:
    # 1 = Actor, Promovente, Ofendido;
    # 2 = Demandado, Inculpado, Imputado;
    # 0 = No definido o se especifica en tipoParteNombre
    tipo_parte: Mapped[int]

    # Aquí se puede especificar el nombre del tipo de parte. Opcional.
    tipo_parte_nombre: Mapped[Optional[str]] = mapped_column(String(256))

    @property
    def nombre_completo(self):
        """Junta nombres, apellido_paterno y apellido materno"""
        return self.nombre + " " + self.apellido_paterno + " " + self.apellido_materno

    @property
    def genero_descripcion(self):
        """Descripción del género"""
        return self.GENEROS[self.genero]

    @property
    def tipo_parte_descripcion(self):
        """Descripción del tipo de parte"""
        if self.tipo_parte == 0:
            return self.tipo_parte_nombre
        return self.TIPOS_PARTES[self.tipo_parte]

    def __repr__(self):
        """Representación"""
        return f"<ExhExhortoPromocionPromovente {self.id}>"
