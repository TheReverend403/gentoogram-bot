ARG PYTHON_VERSION=3.9
ARG POETRY_VERSION=1.1.12

## Base
FROM python:${PYTHON_VERSION}-slim as python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=$POETRY_VERSION \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv" \
    S6_DOWNLOAD_PATH="/opt/s6"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"


FROM python-base as s6-base

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    xz-utils

ARG S6_OVERLAY_VERSION="3.0.0.0-1"

ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch-${S6_OVERLAY_VERSION}.tar.xz /tmp
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64-${S6_OVERLAY_VERSION}.tar.xz /tmp
RUN mkdir -p "$S6_DOWNLOAD_PATH" && \
    tar -C "$S6_DOWNLOAD_PATH/" -Jxpf /tmp/s6-overlay-x86_64-${S6_OVERLAY_VERSION}.tar.xz && \
    tar -C "$S6_DOWNLOAD_PATH/" -Jxpf /tmp/s6-overlay-noarch-${S6_OVERLAY_VERSION}.tar.xz


## Python builder
FROM python-base as python-builder-base

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    curl

# install poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://install.python-poetry.org | python -

# copy project requirement files here to ensure they will be cached.
WORKDIR $PYSETUP_PATH
COPY poetry.lock pyproject.toml ./

# install runtime deps - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
RUN poetry install --no-dev


## Production image
FROM python-base as production

RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    curl

RUN apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=python-builder-base $PYSETUP_PATH $PYSETUP_PATH

COPY --from=s6-base $S6_DOWNLOAD_PATH /
COPY docker/rootfs /

ARG APP_USER=app

RUN addgroup --gid 1000 --system ${APP_USER} && \
    adduser --uid 1000 --system --gid 1000 --no-create-home ${APP_USER}

WORKDIR /app

COPY --chown=${APP_USER}:${APP_USER} ./gentoogram ./gentoogram

ENV APP_USER=${APP_USER} \
    SETTINGS_FILE_FOR_DYNACONF="/config/settings.yml" \
    PYTHONPATH="." \
    S6_BEHAVIOUR_IF_STAGE2_FAILS=2

VOLUME ["/config"]

HEALTHCHECK --interval=10s --timeout=5s CMD ["/bin/healthcheck"]
ENTRYPOINT ["/init"]