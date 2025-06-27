"""
Settings

Para producción, configure los siguientes secretos en Google Cloud Secret Manager:

- pjecz_hercules_flask_ai_studio_api_key
- pjecz_hercules_flask_cloud_storage_deposito
- pjecz_hercules_flask_cloud_storage_deposito_edictos
- pjecz_hercules_flask_cloud_storage_deposito_glosas
- pjecz_hercules_flask_cloud_storage_deposito_listas_de_acuerdos
- pjecz_hercules_flask_cloud_storage_deposito_perseo
- pjecz_hercules_flask_cloud_storage_deposito_sentencias
- pjecz_hercules_flask_cloud_storage_deposito_usuarios
- pjecz_hercules_flask_estado_clave
- pjecz_hercules_flask_expediente_virtual_api_key
- pjecz_hercules_flask_expediente_virtual_api_url
- pjecz_hercules_flask_host
- pjecz_hercules_flask_municipio_clave
- pjecz_hercules_flask_redis_url
- pjecz_hercules_flask_salt
- pjecz_hercules_flask_secret_key
- pjecz_hercules_flask_sqlalchemy_database_uri
- pjecz_hercules_flask_syncfusion_license_key
- pjecz_hercules_flask_task_queue

Para desarrollo, debe crear un archivo .env con las variables de entorno:

- AI_STUDIO_API_KEY
- ESTADO_CLAVE
- CLOUD_STORAGE_DEPOSITO
- CLOUD_STORAGE_DEPOSITO_EDICTOS
- CLOUD_STORAGE_DEPOSITO_GLOSAS
- CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS
- CLOUD_STORAGE_DEPOSITO_PERSEO
- CLOUD_STORAGE_DEPOSITO_SENTENCIAS
- CLOUD_STORAGE_DEPOSITO_USUARIOS
- ESTADO_CLAVE
- EXPEDIENTE_VIRTUAL_API_KEY
- EXPEDIENTE_VIRTUAL_API_URL
- HOST
- MUNICIPIO_CLAVE
- REDIS_URL
- SALT
- SECRET_KEY
- SQLALCHEMY_DATABASE_URI
- SYNCFUSION_LICENSE_KEY
- TASK_QUEUE
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from google.cloud import secretmanager
from pydantic_settings import BaseSettings

load_dotenv()

MEGABYTE = (2**10) ** 2
PROJECT_ID = os.getenv("PROJECT_ID", "")  # Por defecto está vacío, esto significa estamos en modo local
SERVICE_PREFIX = os.getenv("SERVICE_PREFIX", "pjecz_hercules_flask")


def get_secret(secret_id: str) -> str:
    """Get secret from google cloud secret manager"""

    # If not in google cloud, return environment variable
    if PROJECT_ID == "":
        return os.getenv(secret_id.upper().strip(), "")

    # Create the secret manager client
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version
    secret = f"{SERVICE_PREFIX}_{secret_id}"
    name = client.secret_version_path(PROJECT_ID, secret, "latest")

    # Access the secret version
    response = client.access_secret_version(name=name)

    # Return the decoded payload
    return response.payload.data.decode("UTF-8").strip()


class Settings(BaseSettings):
    """Settings"""

    AI_STUDIO_API_KEY: str = get_secret("ai_studio_api_key")
    CLOUD_STORAGE_DEPOSITO: str = get_secret("cloud_storage_deposito")
    CLOUD_STORAGE_DEPOSITO_EDICTOS: str = get_secret("cloud_storage_deposito_edictos")
    CLOUD_STORAGE_DEPOSITO_GLOSAS: str = get_secret("cloud_storage_deposito_glosas")
    CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS: str = get_secret("cloud_storage_deposito_listas_de_acuerdos")
    CLOUD_STORAGE_DEPOSITO_PERSEO: str = get_secret("cloud_storage_deposito_perseo")
    CLOUD_STORAGE_DEPOSITO_SENTENCIAS: str = get_secret("cloud_storage_deposito_sentencias")
    CLOUD_STORAGE_DEPOSITO_USUARIOS: str = get_secret("cloud_storage_deposito_usuarios")
    ESTADO_CLAVE: str = get_secret("estado_clave")
    EXPEDIENTE_VIRTUAL_API_KEY: str = get_secret("expediente_virtual_api_key")
    EXPEDIENTE_VIRTUAL_API_URL: str = get_secret("expediente_virtual_api_url")
    HOST: str = get_secret("host")
    MUNICIPIO_CLAVE: str = get_secret("municipio_clave")
    REDIS_URL: str = get_secret("redis_url")
    SALT: str = get_secret("salt")
    SECRET_KEY: str = get_secret("secret_key")
    SQLALCHEMY_DATABASE_URI: str = get_secret("sqlalchemy_database_uri")
    SYNCFUSION_LICENSE_KEY: str = get_secret("syncfusion_license_key")
    TASK_QUEUE: str = get_secret("task_queue")

    # Incrementar el tamaño de lo que se sube en los formularios para Syncfusion Document Editor
    MAX_CONTENT_LENGTH: int | None = None
    MAX_FORM_MEMORY_SIZE: int = 50 * MEGABYTE

    class Config:
        """Load configuration"""

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Customise sources, first environment variables, then .env file, then google cloud secret manager"""
            return env_settings, file_secret_settings, init_settings


@lru_cache()
def get_settings() -> Settings:
    """Get Settings"""
    return Settings()
