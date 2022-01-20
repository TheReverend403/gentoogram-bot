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
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"


## Python builder
FROM python-base as python-builder-base

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
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

COPY --from=sudobmitch/base:scratch / /
COPY docker/entrypoint.d/ /etc/entrypoint.d/

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        util-linux

RUN rm -rf /var/lib/apt/lists/*

COPY --from=python-builder-base $PYSETUP_PATH $PYSETUP_PATH

ARG APP_USER=app

RUN addgroup --gid 1000 --system ${APP_USER} && \
    adduser --uid 1000 --system --gid 1000 --no-create-home ${APP_USER}

WORKDIR /app

COPY --chown=${APP_USER}:${APP_USER} ./gentoogram ./gentoogram

ENV APP_USER=${APP_USER} \
    SETTINGS_FILE_FOR_DYNACONF="/config/settings.yml" \
    PYTHONPATH="."

VOLUME ["/config"]

ENTRYPOINT ["/usr/bin/entrypointd.sh"]
CMD ["python", "-m", "gentoogram"]
