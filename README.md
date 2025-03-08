# gentoogram-bot

![GitHub](https://img.shields.io/github/license/TheReverend403/gentoogram-bot?style=flat-square)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/TheReverend403/gentoogram-bot/build-docker-image.yml?branch=main&style=flat-square)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=flat-square)](https://github.com/astral-sh/ruff)

Just a bot for the [@Gentoogram](https://t.me/Gentoogram) Telegram group. It filters chat with regex and stuff.

## Setting up the dev environment

First, install [uv](https://docs.astral.sh/uv/getting-started/installation/).

```sh
git clone https://github.com/TheReverend403/gentoogram-bot
cd gentoogram-bot

uv sync --group dev
uv run pre-commit install
```

## Running in dev mode

### Docker

```sh
cp docker/.env.example docker/.env # Open and set any empty variables
docker compose -f docker/docker-compose.dev.yml up --build --pull always
```

### Manual

```sh
mkdir config
cp gentoogram/resources/config/settings.toml config/ # Edit settings.toml

uv run -m gentoogram
```
