"""
Bitácoras de APIs
"""

from typing import Optional

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class BitacoraAPI(database.Model, UniversalMixin):
    """BitacoraAPI"""

    PETICIONES = {
        "GET": "GET",
        "POST": "POST",
        "PUT": "PUT",
        "DELETE": "DELETE",
    }

    # Nombre de la tabla
    __tablename__ = "bitacoras_apis"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="bitacoras_apis")

    # Columnas
    api_nombre: Mapped[str] = mapped_column(String(256))
    api_ruta: Mapped[str] = mapped_column(String(512))
    peticion: Mapped[str] = mapped_column(Enum(*PETICIONES, name="peticiones_tipos", native_enum=False), index=True)
    respuesta_exitosa: Mapped[Optional[bool]] = mapped_column(Boolean)
    respuesta_mensaje: Mapped[Optional[str]] = mapped_column(String(256))
    respuesta_errores: Mapped[list[str]] = mapped_column(JSON)
    respuesta_datos: Mapped[list[dict]] = mapped_column(JSON)

    def __repr__(self):
        """Representación"""
        return f"<Bitacora API {self.id}>"
