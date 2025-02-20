"""
Exh Exhortos Partes, modelos
"""

from typing import Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ExhExhortoParte(database.Model, UniversalMixin):
    """ExhExhortoParte"""

    GENEROS = {
        "M": "MASCULINO",
        "F": "FEMENINO",
        "-": "SIN SEXO",
    }

    # Nombre de la tabla
    __tablename__ = "exh_exhortos_partes"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    exh_exhorto_id: Mapped[int] = mapped_column(ForeignKey("exh_exhortos.id"))
    exh_exhorto: Mapped["ExhExhorto"] = relationship(back_populates="exh_exhortos_partes")

    # Nombre de la parte, en el caso de persona moral, solo en nombre de la empresa o razón social.
    nombre: Mapped[str] = mapped_column(String(256))

    # Apellido paterno de la parte. Solo cuando no sea persona moral. Opcional.
    apellido_paterno: Mapped[Optional[str]] = mapped_column(String(256))

    # Apellido materno de la parte, si es que aplica para la persona. Solo cuando no sea persona moral. Opcional.
    apellido_materno: Mapped[Optional[str]] = mapped_column(String(256))

    # 'M' = Masculino,
    # 'F' = Femenino.
    # Solo cuando aplique y se quiera especificar (que se tenga el dato). NO aplica para persona moral.
    genero: Mapped[str] = mapped_column(Enum(*GENEROS, name="exh_exhortos_partes_generos", native_enum=False))

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
        if self.apellido_paterno is None:
            return self.nombre
        return self.nombre + " " + self.apellido_paterno + " " + self.apellido_materno

    @property
    def genero_descripcion(self):
        """Descripción del genero de la persona"""
        if self.genero == "M":
            return "M) Masculino"
        return "F) Femenino"

    @property
    def tipo_parte_descripcion(self):
        """Descripción del tipo de parte"""
        if self.tipo_parte == 0:
            return "0) NO DEFINIDO"
        elif self.tipo_parte == 1:
            return "1) Actor"
        elif self.tipo_parte == 2:
            return "2) Demandado"
        else:
            return "-"

    def __repr__(self):
        """Representación"""
        return f"<ExhExhortoParte {self.id}>"
