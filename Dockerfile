ARG ARG_PYTHON_VERSION=3.11
ARG ARG_POETRY_VERSION=1.5.1
ARG ARG_POETRY_HOME="/opt/poetry"
ARG ARG_PYSETUP_PATH="/opt/pysetup"
ARG ARG_VENV_PATH="${ARG_PYSETUP_PATH}/.venv"

## Base
FROM python:${ARG_PYTHON_VERSION}-slim as python-base

ARG ARG_POETRY_HOME
ARG ARG_VENV_PATH

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME=${ARG_POETRY_HOME} \
    PATH="${ARG_VENV_PATH}/bin:${ARG_POETRY_HOME}/bin:$PATH"


## Python builder
FROM python-base as python-builder-base

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


ARG ARG_POETRY_VERSION
ARG ARG_PYSETUP_PATH

ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=${ARG_POETRY_VERSION}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN curl -sSL https://install.python-poetry.org | python -

WORKDIR ${ARG_PYSETUP_PATH}

COPY poetry.lock pyproject.toml ./
RUN poetry install --only main


## Production image
FROM python-base as production

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
      curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ARG ARG_VENV_PATH

COPY --from=python-builder-base ${ARG_VENV_PATH} ${ARG_VENV_PATH}
COPY docker/rootfs /

WORKDIR /app

COPY ./gentoogram ./gentoogram

ENV PYTHONPATH="." \
    SETTINGS_FILE_FOR_DYNACONF="/config/settings.yml"

VOLUME ["/config"]

HEALTHCHECK --interval=30s --timeout=5s CMD ["/docker-healthcheck.sh"]

ENTRYPOINT ["/docker-init.sh"]
