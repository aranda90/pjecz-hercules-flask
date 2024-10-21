"""
Funcionarios, modelos
"""

from datetime import date
from typing import List

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class Funcionario(database.Model, UniversalMixin):
    """Funcionario"""

    # Nombre de la tabla
    __tablename__ = "funcionarios"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    centro_trabajo_id: Mapped[int] = mapped_column(ForeignKey("centros_trabajos.id"))
    centro_trabajo: Mapped["CentroTrabajo"] = relationship(back_populates="funcionarios")

    # Columnas
    nombres: Mapped[str] = mapped_column(String(256))
    apellido_paterno: Mapped[str] = mapped_column(String(256))
    apellido_materno: Mapped[str] = mapped_column(String(256), default="")
    curp: Mapped[str] = mapped_column(String(18), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    puesto: Mapped[str] = mapped_column(String(256), default="")
    en_funciones: Mapped[bool] = mapped_column(default=True)
    en_sentencias: Mapped[bool] = mapped_column(default=True)
    en_soportes: Mapped[bool] = mapped_column(default=False)
    en_tesis_jurisprudencias: Mapped[bool] = mapped_column(default=False)
    telefono: Mapped[str] = mapped_column(String(48), default="")
    extension: Mapped[str] = mapped_column(String(24), default="")
    domicilio_oficial: Mapped[str] = mapped_column(String(512), default="")
    ingreso_fecha: Mapped[date]
    puesto_clave: Mapped[str] = mapped_column(String(32), default="")
    fotografia_url: Mapped[str] = mapped_column(String(512), default="")

    # Hijos
    autoridades_funcionarios: Mapped[List["AutoridadFuncionario"]] = relationship(back_populates="funcionario")
    funcionarios_oficinas: Mapped[List["FuncionarioOficina"]] = relationship(back_populates="funcionario")
    soportes_tickets: Mapped[List["SoporteTicket"]] = relationship(back_populates="funcionario")
    # tesis_jurisprudencias: Mapped[List["TesisJurisprudenciaFuncionario"]] = relationship(back_populates="funcionario")

    @property
    def nombre(self):
        """Junta nombres, apellido_paterno y apellido materno"""
        return self.nombres + " " + self.apellido_paterno + " " + self.apellido_materno

    def __repr__(self):
        """Representación"""
        return f"<Funcionario {self.nombre}>"
