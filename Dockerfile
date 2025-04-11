# syntax=docker/dockerfile:1

ARG DEBIAN_VERSION=bookworm

## Base
FROM debian:${DEBIAN_VERSION}-slim AS python-base

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT="/opt/uv/venv" \
    UV_PYTHON_INSTALL_DIR="/opt/uv/python" \
    UV_CACHE_DIR="/opt/uv/cache"

ENV PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}" \
    PYTHONPATH="/app:${PYTHONPATH}"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/


## Base image
FROM python-base AS app-base

ARG META_VERSION
ARG META_COMMIT
ARG META_SOURCE

ENV META_VERSION="${META_VERSION}" \
    META_COMMIT="${META_COMMIT}" \
    META_SOURCE="${META_SOURCE}" \
    ROOT_PATH_FOR_DYNACONF="/config" \
    SETTINGS_FILES_FOR_DYNACONF='["/app/gentoogram/resources/config/default.toml", "*.toml"]' \
    INSTANCE_FOR_DYNACONF="gentoogram.__main__.config"

WORKDIR /app

RUN --mount=type=cache,target=${UV_CACHE_DIR} \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=LICENSE,target=LICENSE \
    uv sync --frozen --no-install-project --no-dev

COPY docker/rootfs /
COPY gentoogram ./gentoogram

VOLUME ["/config"]

ENTRYPOINT ["/docker-entrypoint.sh"]


## Dev image
FROM app-base AS development

ENV ENV_FOR_DYNACONF=development \
    CFG_LOGGER__LEVEL="DEBUG"

RUN --mount=type=cache,target=${UV_CACHE_DIR} \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=README.md,target=README.md \
    --mount=type=bind,source=LICENSE,target=LICENSE \
    uv sync --frozen --no-install-project --group dev


## Production image
FROM app-base AS production

ENV ENV_FOR_DYNACONF=production \
    CFG_LOGGER__LEVEL="INFO"
