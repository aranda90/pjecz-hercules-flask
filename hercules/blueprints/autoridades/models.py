"""
Autoridad
"""

from typing import List

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class Autoridad(database.Model, UniversalMixin):
    """Autoridad"""

    AUDIENCIAS_CATEGORIAS = {
        "NO DEFINIDO": "No Definido",
        "CIVIL FAMILIAR MERCANTIL LETRADO TCYA": "Civil Familiar Mercantil Letrado TCyA",
        "MATERIA ACUSATORIO PENAL ORAL": "Materia Acusatorio Penal Oral",
        "DISTRITALES": "Distritales",
        "SALAS": "Salas",
    }

    ORGANOS_JURISDICCIONALES = {
        "NO DEFINIDO": "No Definido",
        "JUZGADO DE PRIMERA INSTANCIA": "Juzgado de Primera Instancia",
        "JUZGADO DE PRIMERA INSTANCIA ORAL": "Juzgado de Primera Instancia Oral",
        "PLENO O SALA DEL TSJ": "Pleno o Sala del TSJ",
        "TRIBUNAL DISTRITAL": "Tribunal Distrital",
        "TRIBUNAL DE CONCILIACION Y ARBITRAJE": "Tribunal de Conciliación y Arbitraje",
    }

    SEDES = {
        "ND": "ND",
        "DACN": "DACN",
        "DMNC": "DMNC",
        "DPRR": "DPRR",
        "DRGR": "DRGR",
        "DSBN": "DSBN",
        "DSLT": "DSLT",
        "DSPD": "DSPD",
        "DTRC": "DTRC",
    }

    # Nombre de la tabla
    __tablename__ = "autoridades"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Claves foráneas
    distrito_id: Mapped[int] = mapped_column(ForeignKey("distritos.id"))
    distrito: Mapped["Distrito"] = relationship(back_populates="autoridades")
    materia_id: Mapped[int] = mapped_column(ForeignKey("materias.id"))
    materia: Mapped["Materia"] = relationship(back_populates="autoridades")
    municipio_id: Mapped[int] = mapped_column(ForeignKey("municipios.id"))
    municipio: Mapped["Municipio"] = relationship(back_populates="autoridades")

    # Columnas
    clave: Mapped[str] = mapped_column(String(16), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))
    descripcion_corta: Mapped[str] = mapped_column(String(64))
    es_archivo_solicitante: Mapped[bool] = mapped_column(default=False)
    es_cemasc: Mapped[bool] = mapped_column(default=False)
    es_defensoria: Mapped[bool] = mapped_column(default=False)
    es_extinto: Mapped[bool] = mapped_column(default=False)
    es_jurisdiccional: Mapped[bool] = mapped_column(default=False)
    es_notaria: Mapped[bool] = mapped_column(default=False)
    es_organo_especializado: Mapped[bool] = mapped_column(default=False)
    es_revisor_escrituras: Mapped[bool] = mapped_column(default=False)
    organo_jurisdiccional: Mapped[str] = mapped_column(
        Enum(*ORGANOS_JURISDICCIONALES, name="autoridades_organos_jurisdiccionales", native_enum=False),
        index=True,
    )
    directorio_edictos: Mapped[str] = mapped_column(String(256))
    directorio_glosas: Mapped[str] = mapped_column(String(256))
    directorio_listas_de_acuerdos: Mapped[str] = mapped_column(String(256))
    directorio_sentencias: Mapped[str] = mapped_column(String(256))
    audiencia_categoria: Mapped[str] = mapped_column(
        Enum(*AUDIENCIAS_CATEGORIAS, name="autoridades_audiencias_categorias", native_enum=False), index=True
    )
    limite_dias_listas_de_acuerdos: Mapped[int] = mapped_column(default=0)
    sede: Mapped[str] = mapped_column(
        Enum(*SEDES, name="autoridades_sedes", native_enum=False), index=True
    )  # Clave del distrito judicial geografico

    # Hijos
    arc_documentos: Mapped[List["ArcDocumento"]] = relationship(back_populates="autoridad")
    arc_remesas: Mapped[List["ArcRemesa"]] = relationship(back_populates="autoridad")
    arc_solicitudes: Mapped[List["ArcSolicitud"]] = relationship(back_populates="autoridad")
    audiencias: Mapped[List["Audiencia"]] = relationship(back_populates="autoridad")
    autoridades_funcionarios: Mapped[List["AutoridadFuncionario"]] = relationship(back_populates="autoridad")
    cid_areas_autoridades: Mapped[List["CIDAreaAutoridad"]] = relationship(back_populates="autoridad")
    cid_procedimientos: Mapped[List["CIDProcedimiento"]] = relationship(back_populates="autoridad")
    edictos: Mapped[List["Edicto"]] = relationship(back_populates="autoridad")
    glosas: Mapped[List["Glosa"]] = relationship(back_populates="autoridad")
    listas_de_acuerdos: Mapped[List["ListaDeAcuerdo"]] = relationship(back_populates="autoridad")
    redam: Mapped[List["Redam"]] = relationship("Redam", back_populates="autoridad")
    sentencias: Mapped[List["Sentencia"]] = relationship(back_populates="autoridad")
    ubicaciones_expedientes: Mapped[List["UbicacionExpediente"]] = relationship(back_populates="autoridad")
    usuarios: Mapped[List["Usuario"]] = relationship("Usuario", back_populates="autoridad")

    def __repr__(self):
        """Representación"""
        return f"<Autoridad {self.clave}>"
