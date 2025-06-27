"""
Usuarios, modelos
"""

from datetime import datetime
from typing import List, Optional

from flask import current_app
from flask_login import UserMixin
from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.blueprints.permisos.models import Permiso
from hercules.blueprints.tareas.models import Tarea
from hercules.blueprints.usuarios_roles.models import UsuarioRol
from hercules.extensions import database, pwd_context
from lib.universal_mixin import UniversalMixin


class Usuario(database.Model, UserMixin, UniversalMixin):
    """Usuario"""

    WORKSPACES = {
        "BUSINESS STARTED": "Business Started",
        "BUSINESS STANDARD": "Business Standard",
        "COAHUILA": "Coahuila",
        "EXTERNO": "Externo",
    }

    # Nombre de la tabla
    __tablename__ = "usuarios"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="usuarios")
    oficina_id: Mapped[int] = mapped_column(ForeignKey("oficinas.id"))
    oficina: Mapped["Oficina"] = relationship(back_populates="usuarios")

    # Columnas
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    nombres: Mapped[str] = mapped_column(String(256))
    apellido_paterno: Mapped[str] = mapped_column(String(256))
    apellido_materno: Mapped[str] = mapped_column(String(256))
    curp: Mapped[str] = mapped_column(String(18), default="")
    puesto: Mapped[str] = mapped_column(String(256), default="")
    efirma_registro_id: Mapped[Optional[int]]
    workspace: Mapped[str] = mapped_column(Enum(*WORKSPACES, name="usuarios_workspaces", native_enum=False), index=True)

    # Columnas que NO aparecen en nuevo o editar porque vienen de otros lugares
    email_personal: Mapped[str] = mapped_column(String(256), default="")
    telefono: Mapped[str] = mapped_column(String(48), default="")
    telefono_celular: Mapped[str] = mapped_column(String(48), default="")
    extension: Mapped[str] = mapped_column(String(24), default="")
    fotografia_url: Mapped[str] = mapped_column(String(512), default="")

    # Columnas que NO deben ser expuestas
    api_key: Mapped[Optional[str]] = mapped_column(String(128))
    api_key_expiracion: Mapped[Optional[datetime]]
    contrasena: Mapped[Optional[str]] = mapped_column(String(256))

    # Hijos
    arc_documentos_bitacoras: Mapped[List["ArcDocumentoBitacora"]] = relationship(back_populates="usuario")
    arc_remesas: Mapped[List["ArcRemesa"]] = relationship(back_populates="usuario_asignado")
    arc_solicitudes_asignado: Mapped[List["ArcSolicitud"]] = relationship(back_populates="usuario_asignado")
    arc_solicitudes_bitacoras: Mapped[List["ArcSolicitudBitacora"]] = relationship(back_populates="usuario")
    arc_remesas_bitacoras: Mapped[List["ArcRemesaBitacora"]] = relationship(back_populates="usuario")
    bitacoras: Mapped[List["Bitacora"]] = relationship("Bitacora", back_populates="usuario")
    bitacoras_apis: Mapped[List["BitacoraAPI"]] = relationship("BitacoraAPI", back_populates="usuario")
    cid_procedimientos: Mapped[List["CIDProcedimiento"]] = relationship(back_populates="usuario")
    entradas_salidas: Mapped[List["EntradaSalida"]] = relationship("EntradaSalida", back_populates="usuario")
    fin_vales: Mapped[List["FinVale"]] = relationship("FinVale", back_populates="usuario")
    inv_custodias: Mapped[List["InvCustodia"]] = relationship("InvCustodia", back_populates="usuario")
    ofi_documentos: Mapped[List["OfiDocumento"]] = relationship("OfiDocumento", back_populates="usuario")
    ofi_documentos_destinatarios: Mapped[List["OfiDocumentoDestinatario"]] = relationship(
        "OfiDocumentoDestinatario", back_populates="usuario"
    )
    ofi_plantillas: Mapped[List["OfiPlantilla"]] = relationship("OfiPlantilla", back_populates="usuario")
    tareas: Mapped[List["Tarea"]] = relationship("Tarea", back_populates="usuario")
    usuarios_nominas: Mapped[List["UsuarioNomina"]] = relationship("UsuarioNomina", back_populates="usuario")
    usuarios_roles: Mapped[List["UsuarioRol"]] = relationship("UsuarioRol", back_populates="usuario")
    soportes_tickets: Mapped[List["SoporteTicket"]] = relationship(back_populates="usuario")

    # Propiedades
    modulos_menu_principal_consultados = []
    permisos_consultados = {}

    @property
    def nombre(self):
        """Junta nombres, apellido primero y apellido segundo"""
        return self.nombres + " " + self.apellido_paterno + " " + self.apellido_materno

    @property
    def modulos_menu_principal(self):
        """Elaborar listado con los modulos ordenados para el menu principal"""
        if len(self.modulos_menu_principal_consultados) > 0:
            return self.modulos_menu_principal_consultados
        modulos = []
        modulos_nombres = []
        for usuario_rol in self.usuarios_roles:
            if usuario_rol.estatus == "A":
                for permiso in usuario_rol.rol.permisos:
                    if (
                        permiso.modulo.nombre not in modulos_nombres
                        and permiso.estatus == "A"
                        and permiso.nivel > 0
                        and permiso.modulo.en_navegacion
                        and permiso.modulo.en_plataforma_hercules
                    ):
                        modulos.append(permiso.modulo)
                        modulos_nombres.append(permiso.modulo.nombre)
        self.modulos_menu_principal_consultados = sorted(modulos, key=lambda x: x.nombre_corto)
        return self.modulos_menu_principal_consultados

    @property
    def permisos(self):
        """Entrega un diccionario con todos los permisos"""
        if len(self.permisos_consultados) > 0:
            return self.permisos_consultados
        self.permisos_consultados = {}
        for usuario_rol in self.usuarios_roles:
            if usuario_rol.estatus == "A":
                for permiso in usuario_rol.rol.permisos:
                    if permiso.estatus == "A":
                        etiqueta = permiso.modulo.nombre
                        if etiqueta not in self.permisos_consultados or permiso.nivel > self.permisos_consultados[etiqueta]:
                            self.permisos_consultados[etiqueta] = permiso.nivel
        return self.permisos_consultados

    @classmethod
    def find_by_identity(cls, identity):
        """Encontrar a un usuario por su correo electrónico"""
        return Usuario.query.filter(Usuario.email == identity).first()

    @property
    def is_active(self):
        """¿Es activo?"""
        return self.estatus == "A"

    def authenticated(self, with_password=True, password=""):
        """Ensure a user is authenticated, and optionally check their password."""
        if self.id and with_password:
            return pwd_context.verify(password, self.contrasena)
        return True

    def can(self, modulo_nombre: str, permission: int):
        """¿Tiene permiso?"""
        if modulo_nombre in self.permisos:
            return self.permisos[modulo_nombre] >= permission
        return False

    def can_view(self, modulo_nombre: str):
        """¿Tiene permiso para ver?"""
        return self.can(modulo_nombre, Permiso.VER)

    def can_edit(self, modulo_nombre: str):
        """¿Tiene permiso para editar?"""
        return self.can(modulo_nombre, Permiso.MODIFICAR)

    def can_insert(self, modulo_nombre: str):
        """¿Tiene permiso para agregar?"""
        return self.can(modulo_nombre, Permiso.CREAR)

    def can_admin(self, modulo_nombre: str):
        """¿Tiene permiso para administrar?"""
        return self.can(modulo_nombre, Permiso.ADMINISTRAR)

    def get_roles(self):
        """Obtener roles"""
        usuarios_roles = UsuarioRol.query.filter_by(usuario_id=self.id).filter_by(estatus="A").all()
        return [usuario_rol.rol.nombre for usuario_rol in usuarios_roles]

    def launch_task(self, comando, mensaje, *args, **kwargs):
        """Lanzar tarea en el fondo"""
        rq_job = current_app.task_queue.enqueue(f"hercules.blueprints.{comando}", *args, **kwargs)
        tarea = Tarea(id=rq_job.get_id(), comando=comando, mensaje=mensaje, usuario=self)
        tarea.save()
        return tarea

    def get_tasks_in_progress(self):
        """Obtener tareas"""
        return Tarea.query.filter_by(usuario=self, ha_terminado=False).all()

    def get_task_in_progress(self, comando):
        """Obtener progreso de una tarea"""
        return Tarea.query.filter_by(comando=comando, usuario=self, ha_terminado=False).first()

    def __repr__(self):
        """Representación"""
        return f"<Usuario {self.email}>"
