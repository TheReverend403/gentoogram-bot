# syntax=docker/dockerfile:1

ARG DEBIAN_VERSION=bookworm
ARG PYTHON_VERSION=3.12

## Base
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} as python-base

ARG META_VERSION
ARG META_VERSION_HASH
ARG META_SOURCE

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    # Latest
    POETRY_VERSION="" \
    VIRTUAL_ENV="/venv" \
    META_VERSION="${META_VERSION}" \
    META_VERSION_HASH="${META_VERSION_HASH}" \
    META_SOURCE="${META_SOURCE}"

ENV PATH="${POETRY_HOME}/bin:${VIRTUAL_ENV}/bin:${PATH}" \
    PYTHONPATH="/app:${PYTHONPATH}"

RUN python -m venv "${VIRTUAL_ENV}"

WORKDIR /app


## Python builder
FROM python-base as python-builder-base

RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    apt-get update && \
    apt-get install --no-install-recommends -y \
    curl \
    && apt-get autoclean && rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN --mount=type=cache,target=/root/.cache \
    curl -sSL https://install.python-poetry.org | python3 -

COPY poetry.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache \
    poetry install --no-root --only main


## Production image
FROM python-base as app-base

RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    apt-get update && \
    apt-get install --no-install-recommends -y \
    curl && \
    apt-get autoclean && rm -rf /var/lib/apt/lists/*

COPY --from=python-builder-base ${VIRTUAL_ENV} ${VIRTUAL_ENV}
COPY docker/rootfs /
COPY gentoogram ./gentoogram

ENV ROOT_PATH_FOR_DYNACONF="/config" \
    INSTANCE_FOR_DYNACONF="gentoogram.__main__.config"

VOLUME ["/config"]

ENTRYPOINT ["/docker-entrypoint.sh"]


## Dev image
FROM app-base as development

COPY --from=python-builder-base ${POETRY_HOME} ${POETRY_HOME}
COPY poetry.lock pyproject.toml ./

RUN --mount=type=cache,target=/root/.cache \
    poetry install --no-root

ENV ENV_FOR_DYNACONF=development \
    CFG_LOGGER__LEVEL="DEBUG"


## Production image
FROM app-base as production

ENV ENV_FOR_DYNACONF=production \
    CFG_LOGGER__LEVEL="INFO"

HEALTHCHECK --start-interval=1s --start-period=10s --interval=10s --timeout=5s CMD ["/docker-healthcheck.sh"]
