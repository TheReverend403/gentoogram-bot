# syntax=docker/dockerfile:1

ARG DEBIAN_VERSION=bookworm

## Base
FROM debian:${DEBIAN_VERSION}-slim AS python-base

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_FROZEN=1 \
    UV_PROJECT_ENVIRONMENT="/opt/uv/venv" \
    UV_PYTHON_INSTALL_DIR="/opt/uv/python" \
    UV_CACHE_DIR="/opt/uv/cache"

ENV PATH="${UV_PROJECT_ENVIRONMENT}/bin:${PATH}" \
    PYTHONPATH="/app:${PYTHONPATH}"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/
COPY .python-version .

RUN --mount=type=cache,target=${UV_CACHE_DIR} \
    uv python install


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

ADD . .
RUN ln -s /app/docker/rootfs/* /

RUN --mount=type=cache,target=${UV_CACHE_DIR} \
    uv sync --no-install-project --no-dev

VOLUME ["/config"]

ENTRYPOINT ["/docker-entrypoint.sh"]


## Dev image
FROM app-base AS development

ENV ENV_FOR_DYNACONF=development \
    CFG_LOGGER__LEVEL="DEBUG"

RUN --mount=type=cache,target=${UV_CACHE_DIR} \
    uv sync --no-install-project --group dev


## Production image
FROM app-base AS production

ENV ENV_FOR_DYNACONF=production \
    CFG_LOGGER__LEVEL="INFO"
