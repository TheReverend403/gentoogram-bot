# syntax=docker/dockerfile:1

ARG DEBIAN_VERSION=bookworm
ARG PYTHON_VERSION=3.13
ARG NODE_VERSION=20

## Base
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-${DEBIAN_VERSION}-slim AS python-base

ARG META_VERSION
ARG META_VERSION_HASH
ARG META_SOURCE

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT="/venv" \
    META_VERSION="${META_VERSION}" \
    META_VERSION_HASH="${META_VERSION_HASH}" \
    META_SOURCE="${META_SOURCE}"

ENV PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}" \
    PYTHONPATH="/app:${PYTHONPATH}"

WORKDIR /app


## Python builder
FROM python-base AS python-builder-base

RUN --mount=type=cache,target=/var/cache/apt,sharing=private \
    apt-get update && \
    apt-get install --no-install-recommends -y \
    curl \
    && apt-get autoclean && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=LICENSE,target=LICENSE \
    uv sync --frozen --no-install-project --no-dev


## Production image
FROM python-base AS app-base

COPY --from=python-builder-base ${UV_PROJECT_ENVIRONMENT} ${UV_PROJECT_ENVIRONMENT}
COPY docker/rootfs /
COPY gentoogram ./gentoogram

ENV ROOT_PATH_FOR_DYNACONF="/config" \
    INSTANCE_FOR_DYNACONF="gentoogram.__main__.config"

VOLUME ["/config"]

ENTRYPOINT ["/docker-entrypoint.sh"]


## Dev image
FROM app-base AS development

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=LICENSE,target=LICENSE \
    uv sync --frozen --no-install-project --group dev

ENV ENV_FOR_DYNACONF=development \
    CFG_LOGGER__LEVEL="DEBUG"


## Production image
FROM app-base AS production

ENV ENV_FOR_DYNACONF=production \
    CFG_LOGGER__LEVEL="INFO"
