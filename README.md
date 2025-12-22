# gentoogram-bot

![GitHub](https://img.shields.io/github/license/lwatsondev/gentoogram-bot?style=flat-square)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/lwatsondev/gentoogram-bot/build-docker-image.yml?branch=main&style=flat-square)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=flat-square)](https://github.com/astral-sh/ruff)

Just a bot for the [@Gentoogram](https://t.me/Gentoogram) Telegram group. It filters chat with regex and stuff.

## Setting up the dev environment

First, install [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
git clone https://github.com/lwatsondev/gentoogram-bot
cd gentoogram-bot

uv sync --group dev
uv run pre-commit install
```

## Running in dev mode

```sh
## Env var usage for configuration is documented here: https://www.dynaconf.com/envvars/
## Env var prefix is set to 'CFG_', not 'DYNACONF_'.
## Add env vars to 'docker/.env'.
## You can also copy gentoogram/resources/config/default.toml to docker/config/app/
cp docker/.env.example docker/.env
docker compose -f docker/compose.yaml up --build --pull always
```
