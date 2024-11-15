"""
Exh Exhortos, modelos
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.functions import now

from hercules.extensions import database
from lib.universal_mixin import UniversalMixin


class ExhExhorto(database.Model, UniversalMixin):
    """ExhExhorto"""

    ESTADOS = {
        "RECIBIDO": "Recibido",
        "TRANSFIRIENDO": "Transfiriendo",
        "PROCESANDO": "Procesando",
        "RECHAZADO": "Rechazado",
        "DILIGENCIADO": "Diligenciado",
        "CONTESTADO": "Contestado",
        "PENDIENTE": "Pendiente",
        "CANCELADO": "Cancelado",
        "POR ENVIAR": "Por enviar",
        "INTENTOS AGOTADOS": "Intentos agotados",
        "RECIBIDO CON EXITO": "Recibido con éxito",
        "NO FUE RESPONDIDO": "No fue respondido",
        "RESPONDIDO": "Respondido",
    }

    REMITENTES = {
        "INTERNO": "Interno",
        "EXTERNO": "Externo",
    }

    # Nombre de la tabla
    __tablename__ = "exh_exhortos"

    # Clave primaria
    id: Mapped[int] = mapped_column(primary_key=True)

    # Clave foránea: Juzgado/Área al que se turna el Exhorto y hará el correspondiente proceso de este
    autoridad_id: Mapped[int] = mapped_column(ForeignKey("autoridades.id"))
    autoridad: Mapped["Autoridad"] = relationship(back_populates="exh_exhortos")

    # Clave foránea: Área de recepción
    exh_area_id: Mapped[int] = mapped_column(ForeignKey("exh_areas.id"))
    exh_area: Mapped["ExhArea"] = relationship(back_populates="exh_exhortos")

    # Materia (el que se obtuvo en la consulta de materias del PJ exhortado) al que el Exhorto hace referencia
    materia_clave: Mapped[str] = mapped_column(String(24))
    materia_nombre: Mapped[str] = mapped_column(String(256))

    # Clave foránea: Identificador INEGI del Municipio donde está localizado el Juzgado del PJ exhortante
    municipio_origen_id: Mapped[int] = mapped_column(ForeignKey("municipios.id"))
    municipio_origen: Mapped["Municipio"] = relationship(back_populates="exh_exhortos_origenes")

    # GUID/UUID... que sea único. Pero es opcional para nosotros cuando el estado es PENDIENTE
    folio_seguimiento: Mapped[Optional[str]] = mapped_column(String(48), unique=True)

    # UUID identificador con el que el PJ exhortante identifica el exhorto que envía
    exhorto_origen_id: Mapped[str] = mapped_column(String(48))

    # ID de la tabla Municipios: Para el payload es el Identificador INEGI del Municipio del Estado del PJ exhortado
    # al que se quiere enviar el Exhorto
    municipio_destino_id: Mapped[int]

    # Identificador propio del Juzgado/Área que envía el Exhorto, opcional
    juzgado_origen_id: Mapped[Optional[str]] = mapped_column(String(64))

    # Nombre del Juzgado/Área que envía el Exhorto, opcional
    juzgado_origen_nombre: Mapped[Optional[str]] = mapped_column(String(256))

    # El número de expediente (o carpeta procesal, carpeta...) que tiene el asunto en el Juzgado de Origen
    numero_expediente_origen: Mapped[str] = mapped_column(String(256))

    # El número del oficio con el que se envía el exhorto, el que corresponde al control interno del Juzgado de origen, opcional
    numero_oficio_origen: Mapped[Optional[str]] = mapped_column(String(256))

    # Nombre del tipo de Juicio, o asunto, listado de los delitos (para materia Penal)
    # que corresponde al Expediente del cual el Juzgado envía el Exhorto
    tipo_juicio_asunto_delitos: Mapped[str] = mapped_column(String(256))

    # Nombre completo del Juez del Juzgado o titular del Área que envía el Exhorto, opcional
    juez_exhortante: Mapped[Optional[str]] = mapped_column(String(256))

    # Número de fojas que contiene el exhorto. El valor 0 significa "No Especificado"
    fojas: Mapped[int] = mapped_column(default=0)

    # Cantidad de dias a partir del día que se recibió en el Poder Judicial exhortado que se tiene para responder el Exhorto.
    # El valor de 0 significa "No Especificado"
    dias_responder: Mapped[int] = mapped_column(default=0)

    # Nombre del tipo de diligenciación que le corresponde al exhorto enviado.
    # Este puede contener valores como "Oficio", "Petición de Parte", opcional
    tipo_diligenciacion_nombre: Mapped[Optional[str]] = mapped_column(String(256))

    # Fecha y hora en que el Poder Judicial exhortante registró que se envió el exhorto en su hora local.
    # En caso de no enviar este dato, el Poder Judicial exhortado puede tomar su fecha hora local.
    fecha_origen: Mapped[datetime] = mapped_column(default=now())

    # Texto simple que contenga información extra o relevante sobre el exhorto, opcional
    observaciones: Mapped[Optional[str]] = mapped_column(String(1024))

    # Estado de recepción del documento
    estado: Mapped[str] = mapped_column(Enum(*ESTADOS, name="exh_exhortos_estados", native_enum=False), index=True)

    # Campo para saber si es un proceso interno o extorno
    remitente: Mapped[str] = mapped_column(Enum(*REMITENTES, name="exh_exhortos_remitentes", native_enum=False), index=True)

    # Número de Exhorto con el que se radica en el Juzgado/Área que se turnó el exhorto.
    # Este número sirve para que el usuario pueda indentificar su exhorto dentro del Juzgado/Área donde se turnó,
    # opcional
    numero_exhorto: Mapped[Optional[str]] = mapped_column(String(256))

    # Hijos: PersonaParte[] NO Contiene la definición de las partes del Expediente
    exh_exhortos_partes: Mapped[List["ExhExhortoParte"]] = relationship("ExhExhortoParte", back_populates="exh_exhorto")

    # Hijos: ArchivoARecibir[] SI Colección de los datos referentes a los archivos
    # que se van a recibir el Poder Judicial exhortado en el envío del Exhorto.
    exh_exhortos_archivos: Mapped[List["ExhExhortoArchivo"]] = relationship("ExhExhortoArchivo", back_populates="exh_exhorto")

    # Hijos: Colección de objetos de tipo VideoAcceso que representan los accesos a
    # los videos de las audiencias que forman parte de la respuesta.
    exh_exhortos_videos: Mapped[List["ExhExhortoVideo"]] = relationship("ExhExhortoVideo", back_populates="exh_exhorto")

    # Cuando el exhorto esta en estado POR ENVIAR
    # Puede tener un tiempo con su anterior intento, si es nulo es que no ha sido enviado aun
    por_enviar_tiempo_anterior: Mapped[Optional[datetime]]

    # Y se lleva un contador de intentos
    por_enviar_intentos: Mapped[int] = mapped_column(default=0)

    # Acuse fecha hora local en el que el Poder Judicial exhortado marca que se recibió el Exhorto
    acuse_fecha_hora_recepcion: Mapped[Optional[datetime]]

    # Acuse Identificador del muncipio en donde se recibió o turnó el exhorto.
    # Puede dar el caso que el exhorto se turne directamente al Juzgado, por lo que este dato seria
    # el identificador del municipio donde está el Juzgado.
    # En caso que se tenga una "Oficialía Virtual", no es necesario especificar este dato.
    # NOTA: este dato corresponde al catálogo de municipios del INEGI.
    acuse_municipio_area_recibe_id: Mapped[Optional[int]]

    # Acuse Identificador del área o Juzgado turnado en donde se recibe el Exhorto.
    # En caso que todavía no esté turnado o se disponga de una "Oficialía Virtual",
    # este dato puede no ir en la respuesta.
    acuse_area_recibe_id: Mapped[Optional[str]] = mapped_column(String(256))

    # Acuse Nombre del área o Juzgado turnado en donde se encuentra el Exhorto.
    # En caso de tener una "Oficialía Virtual", este dato puede omitirse
    acuse_area_recibe_nombre: Mapped[Optional[str]] = mapped_column(String(256))

    # Acuse Contiene una URL para abrir una página con la información referente a la recepción del exhorto que se realizó.
    # Esta página el Juzgado que envió el exhorto la puede imprimir como acuse de recibido y evidencia de que el exhorto
    # fue enviado correctamente al Poder Judicial exhortado o también una página que muestre el estatus del exhorto.
    acuse_url_info: Mapped[Optional[str]] = mapped_column(String(256))

    # Identificador propio del Poder Judicial exhortado con el que identifica la respuesta del exhorto.
    # Este dato puede ser un número consecutivo (ej "1", "2", "3"...),
    # un GUID/UUID o cualquíer otro valor con que se identifique la respuesta
    respuesta_origen_id: Mapped[Optional[str]] = mapped_column(String(48))

    # Identificador del municipio que corresponde al Juzgado/Área al que se turnó el Exhorto y que realiza la respuesta de este
    respuesta_municipio_turnado_id: Mapped[Optional[int]]

    # Identificador propio del PJ exhortado que corresponde al Juzgado/Área al que se turna el Exhorto y está respondiendo
    respuesta_area_turnado_id: Mapped[Optional[str]] = mapped_column(String(256))

    # Nombre del Juzgado/Área al que el Exhorto se turnó y está respondiendo.
    respuesta_area_turnado_nombre: Mapped[Optional[str]] = mapped_column(String(256))

    # Número de Exhorto con el que se radicó en el Juzgado/Área que se turnó el exhorto.
    # Este número sirve para que el usuario pueda identificar su exhorto dentro del Juzgado/Área donde se turnó.
    respuesta_numero_exhorto: Mapped[Optional[str]] = mapped_column(String(256))

    # Valor que representa si se realizó la diligenciación del Exhorto:
    # 0 = No Diligenciado
    # 1 = Parcialmente Diligenciado
    # 2 = Diligenciado"
    respuesta_tipo_diligenciado: Mapped[Optional[int]]

    # Texto simple referente a alguna observación u observaciones correspondientes a la respuesta del Exhorto
    respuesta_observaciones: Mapped[Optional[str]] = mapped_column(String(1024))

    # Hijos: Colección de objetos de tipo Actualizaciones que representan
    # las diferentes actualizaciones pedidas para el exhorto
    exh_exhortos_actualizaciones: Mapped[List["ExhExhortoActualizacion"]] = relationship(
        "ExhExhortoActualizacion", back_populates="exh_exhorto"
    )

    # Hijo
    exh_exhortos_promociones: Mapped[List["ExhExhortoPromocion"]] = relationship(
        "ExhExhortoPromocion", back_populates="exh_exhorto"
    )

    def __repr__(self):
        """Representación"""
        return f"<ExhExhorto {self.id}>"
