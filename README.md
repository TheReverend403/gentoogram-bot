# gentoogram-bot

![GitHub](https://img.shields.io/github/license/TheReverend403/gentoogram-bot?style=flat-square)
![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/TheReverend403/gentoogram-bot/build-docker-image.yml?branch=main&style=flat-square)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=flat-square)](https://github.com/astral-sh/ruff)

Just a bot for the [@Gentoogram](https://t.me/Gentoogram) Telegram group. It filters chat with regex and stuff.

## Using

```sh
uv sync
mkdir config/
cp gentoogram/resources/config/settings.yml config/
$EDITOR config/settings.yml
uv run -m gentoogram
```
