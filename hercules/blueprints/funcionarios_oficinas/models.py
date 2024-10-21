"""
Funcionarios Oficinas, modelos
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class FuncionarioOficina(database.Model, UniversalMixin):
    """FuncionarioOficina"""

    # Nombre de la tabla
    __tablename__ = "funcionarios_oficinas"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    funcionario_id: Mapped[int] = mapped_column(ForeignKey("funcionarios.id"))
    funcionario: Mapped["Funcionario"] = relationship(back_populates="funcionarios_oficinas")
    oficina_id: Mapped[int] = mapped_column(ForeignKey("oficinas.id"))
    oficina: Mapped["Oficina"] = relationship(back_populates="funcionarios_oficinas")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))

    def __repr__(self):
        """Representación"""
        return f"<FuncionarioOficina {self.descripcion}>"
