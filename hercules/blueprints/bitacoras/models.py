"""
Bitácoras
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class Bitacora(database.Model, UniversalMixin):
    """Bitacora"""

    # Nombre de la tabla
    __tablename__ = "bitacoras"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    modulo_id: Mapped[int] = mapped_column(ForeignKey("modulos.id"))
    modulo: Mapped["Modulo"] = relationship(back_populates="bitacoras")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="bitacoras")

    # Columnas
    descripcion: Mapped[str] = mapped_column(String(256))
    url: Mapped[str] = mapped_column(String(512))

    def __repr__(self):
        """Representación"""
        return f"<Bitacora {self.creado} {self.descripcion}>"
