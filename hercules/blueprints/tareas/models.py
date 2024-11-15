"""
Tareas, modelos
"""

from flask import current_app
from redis.exceptions import RedisError
from rq.exceptions import NoSuchJobError
from rq.job import Job
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class Tarea(database.Model, UniversalMixin):
    """Tarea"""

    # Nombre de la tabla
    __tablename__ = "tareas"

    # Clave primaria NOTA: El id es string y es el mismo que usa el RQ worker
    id: Mapped[str] = mapped_column(primary_key=True)

    # Clave foránea
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    usuario: Mapped["Usuario"] = relationship(back_populates="tareas")

    # Columnas
    archivo: Mapped[str] = mapped_column(String(256), default="")
    comando: Mapped[str] = mapped_column(String(256), index=True)
    ha_terminado: Mapped[bool] = mapped_column(default=False)
    mensaje: Mapped[str] = mapped_column(String(1024), default="")
    url: Mapped[str] = mapped_column(String(512), default="")

    def get_rq_job(self):
        """Helper method that loads the RQ Job instance"""
        try:
            rq_job = Job.fetch(self.id, connection=current_app.redis)
        except (RedisError, NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        """Returns the progress percentage for the task"""
        job = self.get_rq_job()
        return job.meta.get("progress", 0) if job is not None else 100

    def __repr__(self):
        """Representación"""
        return f"<Tarea {self.id}>"
