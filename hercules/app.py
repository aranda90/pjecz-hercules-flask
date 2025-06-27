"""
Flask App
"""

import rq
from flask import Flask
from redis import Redis

from config.settings import Settings
from hercules.blueprints.abogados.views import abogados
from hercules.blueprints.arc_archivos.views import arc_archivos
from hercules.blueprints.arc_documentos.views import arc_documentos
from hercules.blueprints.arc_documentos_bitacoras.views import arc_documentos_bitacoras
from hercules.blueprints.arc_documentos_tipos.views import arc_documentos_tipos
from hercules.blueprints.arc_juzgados_extintos.views import arc_juzgados_extintos
from hercules.blueprints.arc_remesas.views import arc_remesas
from hercules.blueprints.arc_remesas_bitacoras.views import arc_remesas_bitacoras
from hercules.blueprints.arc_remesas_documentos.views import arc_remesas_documentos
from hercules.blueprints.arc_solicitudes.views import arc_solicitudes
from hercules.blueprints.arc_solicitudes_bitacoras.views import arc_solicitudes_bitacoras
from hercules.blueprints.audiencias.views import audiencias
from hercules.blueprints.autoridades.views import autoridades
from hercules.blueprints.autoridades_funcionarios.views import autoridades_funcionarios
from hercules.blueprints.bitacoras.views import bitacoras
from hercules.blueprints.bitacoras_apis.views import bitacoras_apis
from hercules.blueprints.centros_trabajos.views import centros_trabajos
from hercules.blueprints.cid_areas.views import cid_areas
from hercules.blueprints.cid_areas_autoridades.views import cid_areas_autoridades
from hercules.blueprints.cid_formatos.views import cid_formatos
from hercules.blueprints.cid_procedimientos.views import cid_procedimientos
from hercules.blueprints.distritos.views import distritos
from hercules.blueprints.domicilios.views import domicilios
from hercules.blueprints.edictos.views import edictos
from hercules.blueprints.edictos_acuses.views import edictos_acuses
from hercules.blueprints.entradas_salidas.views import entradas_salidas
from hercules.blueprints.estados.views import estados
from hercules.blueprints.exh_areas.views import exh_areas
from hercules.blueprints.exh_exhortos.views import exh_exhortos
from hercules.blueprints.exh_exhortos_actualizaciones.views import exh_exhortos_actualizaciones
from hercules.blueprints.exh_exhortos_archivos.views import exh_exhortos_archivos
from hercules.blueprints.exh_exhortos_partes.views import exh_exhortos_partes
from hercules.blueprints.exh_exhortos_promociones.views import exh_exhortos_promociones
from hercules.blueprints.exh_exhortos_promociones_archivos.views import exh_exhortos_promociones_archivos
from hercules.blueprints.exh_exhortos_promociones_promoventes.views import exh_exhortos_promociones_promoventes
from hercules.blueprints.exh_exhortos_promoventes.views import exh_exhortos_promoventes
from hercules.blueprints.exh_exhortos_respuestas.views import exh_exhortos_respuestas
from hercules.blueprints.exh_exhortos_respuestas_archivos.views import exh_exhortos_respuestas_archivos
from hercules.blueprints.exh_exhortos_respuestas_videos.views import exh_exhortos_respuestas_videos
from hercules.blueprints.exh_externos.views import exh_externos
from hercules.blueprints.exh_tipos_diligencias.views import exh_tipos_diligencias
from hercules.blueprints.fin_vales.views import fin_vales
from hercules.blueprints.funcionarios.views import funcionarios
from hercules.blueprints.funcionarios_oficinas.views import funcionarios_oficinas
from hercules.blueprints.glosas.views import glosas
from hercules.blueprints.identidades_generos.views import identidades_generos
from hercules.blueprints.inv_categorias.views import inv_categorias
from hercules.blueprints.inv_componentes.views import inv_componentes
from hercules.blueprints.inv_custodias.views import inv_custodias
from hercules.blueprints.inv_equipos.views import inv_equipos
from hercules.blueprints.inv_equipos_fotos.views import inv_equipos_fotos
from hercules.blueprints.inv_marcas.views import inv_marcas
from hercules.blueprints.inv_modelos.views import inv_modelos
from hercules.blueprints.inv_redes.views import inv_redes
from hercules.blueprints.listas_de_acuerdos.views import listas_de_acuerdos
from hercules.blueprints.materias.views import materias
from hercules.blueprints.materias_tipos_juicios.views import materias_tipos_juicios
from hercules.blueprints.modulos.views import modulos
from hercules.blueprints.municipios.views import municipios
from hercules.blueprints.nom_personas.views import nom_personas
from hercules.blueprints.ofi_documentos.views import ofi_documentos
from hercules.blueprints.ofi_documentos_adjuntos.views import ofi_documentos_adjuntos
from hercules.blueprints.ofi_documentos_destinatarios.views import ofi_documentos_destinatarios
from hercules.blueprints.ofi_plantillas.views import ofi_plantillas
from hercules.blueprints.oficinas.views import oficinas
from hercules.blueprints.peritos.views import peritos
from hercules.blueprints.peritos_tipos.views import peritos_tipos
from hercules.blueprints.permisos.views import permisos
from hercules.blueprints.redams.views import redams
from hercules.blueprints.repsvm_agresores.views import repsvm_agresores
from hercules.blueprints.repsvm_agresores_delitos.views import repsvm_agresores_delitos
from hercules.blueprints.repsvm_delitos.views import repsvm_delitos
from hercules.blueprints.roles.views import roles
from hercules.blueprints.sentencias.views import sentencias
from hercules.blueprints.sistemas.views import sistemas
from hercules.blueprints.soportes_adjuntos.views import soportes_adjuntos
from hercules.blueprints.soportes_categorias.views import soportes_categorias
from hercules.blueprints.soportes_tickets.views import soportes_tickets
from hercules.blueprints.tareas.views import tareas
from hercules.blueprints.ubicaciones_expedientes.views import ubicaciones_expedientes
from hercules.blueprints.usuarios.models import Usuario
from hercules.blueprints.usuarios.views import usuarios
from hercules.blueprints.usuarios_nominas.views import usuarios_nominas
from hercules.blueprints.usuarios_roles.views import usuarios_roles
from hercules.blueprints.web_archivos.views import web_archivos
from hercules.blueprints.web_paginas.views import web_paginas
from hercules.blueprints.web_ramas.views import web_ramas
from hercules.extensions import csrf, database, login_manager, moment


def create_app():
    """Crear app"""
    # Definir app
    app = Flask(__name__, instance_relative_config=True)

    # Cargar la configuración
    app.config.from_object(Settings())

    # Redis
    app.redis = Redis.from_url(app.config["REDIS_URL"])
    app.task_queue = rq.Queue(app.config["TASK_QUEUE"], connection=app.redis, default_timeout=3000)

    # Registrar blueprints
    app.register_blueprint(abogados)
    app.register_blueprint(arc_archivos)
    app.register_blueprint(arc_documentos)
    app.register_blueprint(arc_documentos_bitacoras)
    app.register_blueprint(arc_documentos_tipos)
    app.register_blueprint(arc_juzgados_extintos)
    app.register_blueprint(arc_remesas)
    app.register_blueprint(arc_remesas_bitacoras)
    app.register_blueprint(arc_remesas_documentos)
    app.register_blueprint(arc_solicitudes)
    app.register_blueprint(arc_solicitudes_bitacoras)
    app.register_blueprint(audiencias)
    app.register_blueprint(autoridades)
    app.register_blueprint(autoridades_funcionarios)
    app.register_blueprint(bitacoras)
    app.register_blueprint(bitacoras_apis)
    app.register_blueprint(distritos)
    app.register_blueprint(centros_trabajos)
    app.register_blueprint(cid_areas)
    app.register_blueprint(cid_areas_autoridades)
    app.register_blueprint(cid_formatos)
    app.register_blueprint(cid_procedimientos)
    app.register_blueprint(domicilios)
    app.register_blueprint(exh_areas)
    app.register_blueprint(exh_exhortos)
    app.register_blueprint(exh_exhortos_actualizaciones)
    app.register_blueprint(exh_exhortos_archivos)
    app.register_blueprint(exh_exhortos_partes)
    app.register_blueprint(exh_exhortos_promociones)
    app.register_blueprint(exh_exhortos_promociones_archivos)
    app.register_blueprint(exh_exhortos_promociones_promoventes)
    app.register_blueprint(exh_exhortos_promoventes)
    app.register_blueprint(exh_exhortos_respuestas)
    app.register_blueprint(exh_exhortos_respuestas_archivos)
    app.register_blueprint(exh_exhortos_respuestas_videos)
    app.register_blueprint(exh_externos)
    app.register_blueprint(exh_tipos_diligencias)
    app.register_blueprint(edictos)
    app.register_blueprint(edictos_acuses)
    app.register_blueprint(entradas_salidas)
    app.register_blueprint(estados)
    app.register_blueprint(fin_vales)
    app.register_blueprint(funcionarios)
    app.register_blueprint(funcionarios_oficinas)
    app.register_blueprint(glosas)
    app.register_blueprint(identidades_generos)
    app.register_blueprint(inv_categorias)
    app.register_blueprint(inv_componentes)
    app.register_blueprint(inv_custodias)
    app.register_blueprint(inv_equipos)
    app.register_blueprint(inv_equipos_fotos)
    app.register_blueprint(inv_marcas)
    app.register_blueprint(inv_modelos)
    app.register_blueprint(inv_redes)
    app.register_blueprint(listas_de_acuerdos)
    app.register_blueprint(materias)
    app.register_blueprint(materias_tipos_juicios)
    app.register_blueprint(modulos)
    app.register_blueprint(municipios)
    app.register_blueprint(nom_personas)
    app.register_blueprint(ofi_documentos)
    app.register_blueprint(ofi_documentos_adjuntos)
    app.register_blueprint(ofi_documentos_destinatarios)
    app.register_blueprint(ofi_plantillas)
    app.register_blueprint(oficinas)
    app.register_blueprint(peritos)
    app.register_blueprint(peritos_tipos)
    app.register_blueprint(permisos)
    app.register_blueprint(redams)
    app.register_blueprint(repsvm_agresores)
    app.register_blueprint(repsvm_agresores_delitos)
    app.register_blueprint(repsvm_delitos)
    app.register_blueprint(roles)
    app.register_blueprint(sentencias)
    app.register_blueprint(sistemas)
    app.register_blueprint(soportes_adjuntos)
    app.register_blueprint(soportes_categorias)
    app.register_blueprint(soportes_tickets)
    app.register_blueprint(tareas)
    app.register_blueprint(ubicaciones_expedientes)
    app.register_blueprint(usuarios)
    app.register_blueprint(usuarios_nominas)
    app.register_blueprint(usuarios_roles)
    app.register_blueprint(web_archivos)
    app.register_blueprint(web_paginas)
    app.register_blueprint(web_ramas)

    # Inicializar extensiones
    extensions(app)

    # Inicializar autenticación
    authentication(Usuario)

    # Entregar app
    return app


def extensions(app):
    """Inicializar extensiones"""
    csrf.init_app(app)
    database.init_app(app)
    login_manager.init_app(app)
    moment.init_app(app)
    # socketio.init_app(app)


def authentication(user_model):
    """Inicializar Flask-Login"""
    login_manager.login_view = "usuarios.login"

    @login_manager.user_loader
    def load_user(uid):
        return user_model.query.get(uid)
