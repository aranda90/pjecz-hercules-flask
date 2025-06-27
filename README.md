# pjecz-hercules-flask

PJECZ Hércules es un sistema web hecho con Flask.

## Requerimientos

Los requerimientos son

- Python 3.11
- PostgreSQL 15
- Redis

## Instalación

Crear el entorno virtual

```bash
python3.11 -m venv .venv
```

Ingresar al entorno virtual

```bash
source venv/bin/activate
```

Actualizar el gestor de paquetes **pip**

```bash
pip install --upgrade pip
```

Instalar el paquete **wheel** para compilar las dependencias

```bash
pip install wheel
```

Instalar **poetry** en el entorno virtual si no lo tiene desde el sistema operativo

```bash
pip install poetry
```

Configurar **poetry** para que use el entorno virtual dentro del proyecto

```bash
poetry config virtualenvs.in-project true
```

Instalar las dependencias por medio de **poetry**

```bash
poetry install
```

## Configuración

Crear un archivo `.env` en la raíz del proyecto con las variables, establecer sus propios SECRET_KEY, DB_PASS, CLOUD_STORAGE_DEPOSITO y SALT.

```bash
# Flask, para SECRET_KEY use openssl rand -hex 24
FLASK_APP=hercules.app
FLASK_DEBUG=1
SECRET_KEY=XXXXXXXX

# Base de datos
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=pjecz_plataforma_web
DB_USER=adminpjeczplataformaweb
DB_PASS=XXXXXXXX
SQLALCHEMY_DATABASE_URI="postgresql+psycopg2://adminpjeczplataformaweb:XXXXXXXX@127.0.0.1:5432/pjecz_plataforma_web"

# Google Cloud Storage
CLOUD_STORAGE_DEPOSITO=

# Claves INEGI del estado y municipio de Saltillo, Coahuila de Zaragoza
ESTADO_CLAVE=05
MUNICIPIO_CLAVE=030

# Host
HOST=http://127.0.0.1:5000

# Redis
REDIS_URL=redis://127.0.0.1:6379
TASK_QUEUE=pjecz_hercules

# Salt sirve para cifrar el ID con HashID, debe ser igual en la API
SALT=XXXXXXXX

# Si esta en PRODUCTION se evita reiniciar la base de datos
DEPLOYMENT_ENVIRONMENT=develop

# Google AI Studio
AI_STUDIO_API_KEY=
```

Crear un archivo `.bashrc` que se ejecute al iniciar la terminal

```bash
if [ -f ~/.bashrc ]
then
    . ~/.bashrc
fi

if command -v figlet &> /dev/null
then
    figlet Hercules Flask
else
    echo "== Hercules Flask"
fi
echo

if [ -f .env ]
then
    echo "-- Variables de entorno"
    # export $(grep -v '^#' .env | xargs)
    source .env && export $(sed '/^#/d' .env | cut -d= -f1)
    echo "   CLOUD_STORAGE_DEPOSITO: ${CLOUD_STORAGE_DEPOSITO}"
    echo "   DB_HOST: ${DB_HOST}"
    echo "   DB_PORT: ${DB_PORT}"
    echo "   DB_NAME: ${DB_NAME}"
    echo "   DB_USER: ${DB_USER}"
    echo "   DB_PASS: ${DB_PASS}"
    echo "   DEPLOYMENT_ENVIRONMENT: ${DEPLOYMENT_ENVIRONMENT}"
    echo "   ESTADO_CLAVE: ${ESTADO_CLAVE}"
    echo "   FLASK_APP: ${FLASK_APP}"
    echo "   HOST: ${HOST}"
    echo "   MUNICIPIO_CLAVE: ${MUNICIPIO_CLAVE}"
    echo "   REDIS_URL: ${REDIS_URL}"
    echo "   SALT: ${SALT}"
    echo "   SECRET_KEY: ${SECRET_KEY}"
    echo "   SQLALCHEMY_DATABASE_URI: ${SQLALCHEMY_DATABASE_URI}"
    echo "   TASK_QUEUE: ${TASK_QUEUE}"
    echo
    export PGHOST=$DB_HOST
    export PGPORT=$DB_PORT
    export PGDATABASE=$DB_NAME
    export PGUSER=$DB_USER
    export PGPASSWORD=$DB_PASS
fi

if [ -d .venv ]
then
    echo "-- Python Virtual Environment"
    source .venv/bin/activate
    echo "   $(python3 --version)"
    export PYTHONPATH=$(pwd)
    echo "   PYTHONPATH: ${PYTHONPATH}"
    echo
    echo "-- Poetry"
    export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
    echo "   $(poetry --version)"
    echo
    if [ -f cli/app.py ]
    then
        echo "-- Ejecutar el CLI"
        alias cli="python3 ${PWD}/cli/app.py"
        echo "   cli --help"
        echo
    fi
    echo "-- Flask 127.0.0.1:5000"
    alias arrancar="flask run --port=5000"
    echo "   arrancar = flask run --port=5000"
    echo
    echo "-- RQ Worker ${TASK_QUEUE}"
    alias fondear="rq worker ${TASK_QUEUE}"
    echo "   fondear"
    echo
fi

if [ -f .github/workflows/gcloud-app-deploy.yml ]
then
    echo "-- Si cambia pyproject.toml reconstruya requirements.txt para el deploy en GCP via GitHub Actions"
    echo "   poetry export -f requirements.txt --output requirements.txt --without-hashes"
    echo
fi
```

## Arrancar

Antes de usar el CLI o de arrancar el servidor de **Flask** debe cargar las variables de entorno y el entorno virtual.

```bash
source .bashrc
```

Tendrá el alias al **Command Line Interface**

```bash
cli --help
```

Para hacer tareas en el fondo, abrir una terminal, cargar `source .bashrc` y ejecutar

```bash
fondear
```

Para lanzar el front-end Flask, abrir una terminal, cargar `source .bashrc` y ejecutar

```bash
arrancar
```
