"""
CID Procedimientos, modelos
"""

import hashlib
from datetime import date
from typing import List, Optional

from sqlalchemy import JSON, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class CIDProcedimiento(database.Model, UniversalMixin):
    """CIDProcedimiento"""

    SEGUIMIENTOS = {
        "EN ELABORACION": "En Elaboración",
        "CANCELADO POR ELABORADOR": "Cancelado por elaborador",
        "ELABORADO": "Elaborado",
        "RECHAZADO POR REVISOR": "Rechazado por revisor",
        "EN REVISION": "En Revisión",
        "CANCELADO POR REVISOR": "Cancelado por revisor",
        "REVISADO": "Revisado",
        "RECHAZADO POR AUTORIZADOR": "Rechazado por autorizador",
        "EN AUTORIZACION": "En Autorización",
        "CANCELADO POR AUTORIZADOR": "Cancelado por autorizador",
        "AUTORIZADO": "Autorizado",
        "ARCHIVADO": "Archivado",
    }

    # Nombre de la tabla
    __tablename__ = "cid_procedimientos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="cid_procedimientos")
    cid_area_id: Mapped[int] = mapped_column(ForeignKey("cid_areas.id"))
    cid_area: Mapped["CIDArea"] = relationship(back_populates="cid_procedimientos")
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="cid_procedimientos")

    # Columnas
    titulo_procedimiento: Mapped[str] = mapped_column(String(256))
    codigo: Mapped[str] = mapped_column(String(16))
    revision: Mapped[int]
    fecha: Mapped[date]
    objetivo: Mapped[dict] = mapped_column(JSON, default={})
    alcance: Mapped[dict] = mapped_column(JSON, default={})
    documentos: Mapped[dict] = mapped_column(JSON, default={})
    definiciones: Mapped[dict] = mapped_column(JSON, default={})
    responsabilidades: Mapped[dict] = mapped_column(JSON, default={})
    desarrollo: Mapped[dict] = mapped_column(JSON, default={})
    registros: Mapped[dict] = mapped_column(JSON, default={})
    elaboro_nombre: Mapped[str] = mapped_column(String(256), default="")
    elaboro_puesto: Mapped[str] = mapped_column(String(256), default="")
    elaboro_email: Mapped[str] = mapped_column(String(256), default="")
    reviso_nombre: Mapped[str] = mapped_column(String(256), default="")
    reviso_puesto: Mapped[str] = mapped_column(String(256), default="")
    reviso_email: Mapped[str] = mapped_column(String(256), default="")
    aprobo_nombre: Mapped[str] = mapped_column(String(256), default="")
    aprobo_puesto: Mapped[str] = mapped_column(String(256), default="")
    aprobo_email: Mapped[str] = mapped_column(String(256), default="")
    control_cambios: Mapped[dict] = mapped_column(JSON, default={})

    # Número en la cadena, empieza en cero cuando quien elabora aun no lo firma
    cadena: Mapped[int]

    # Seguimiento
    seguimiento: Mapped[str] = mapped_column(
        Enum(*SEGUIMIENTOS, name="cid_procedimientos_seguimientos", native_enum=False), index=True
    )
    seguimiento_posterior: Mapped[str] = mapped_column(
        Enum(*SEGUIMIENTOS, name="cid_procedimientos_seguimientos", native_enum=False), index=True
    )

    # ID del registro anterior en la cadena
    anterior_id: Mapped[int]

    # Al firmarse cambia de texto vacio al hash MD5 y ya no debe modificarse
    firma: Mapped[str] = mapped_column(String(32), default="")

    # Al elaborar el archivo PDF y subirlo a Google Storage
    archivo: Mapped[str] = mapped_column(String(256), default="")
    url: Mapped[str] = mapped_column(String(512), default="")
    # ID del procedimineto anterior
    procedimiento_anterior_autorizado_id: Mapped[Optional[int]]

    cid_formatos: Mapped[List["CIDFormato"]] = relationship(back_populates="procedimiento")

    def elaborar_firma(self):
        """Generate a hash representing the current sample state"""
        if self.id is None or self.creado is None:
            raise ValueError("No se puede elaborar la firma porque no se ha guardado o consultado")
        elementos = []
        elementos.append(str(self.id))
        elementos.append(self.creado.strftime("%Y-%m-%d %H:%M:%S"))
        elementos.append(self.titulo_procedimiento)
        elementos.append(self.codigo)
        elementos.append(str(self.revision))
        elementos.append(str(self.objetivo))
        elementos.append(str(self.alcance))
        elementos.append(str(self.documentos))
        elementos.append(str(self.definiciones))
        elementos.append(str(self.responsabilidades))
        elementos.append(str(self.desarrollo))
        elementos.append(str(self.registros))
        elementos.append(self.elaboro_email)
        elementos.append(self.reviso_email)
        elementos.append(self.aprobo_email)
        elementos.append(str(self.control_cambios))
        return hashlib.md5("|".join(elementos).encode("utf-8")).hexdigest()

    def __repr__(self):
        """Representación"""
        return f"<CIDProcedimiento {self.id}>"
