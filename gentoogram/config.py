#  This file is part of gentoogram-bot.
#
#  gentoogram-bot is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  gentoogram-bot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with gentoogram-bot.  If not, see <https://www.gnu.org/licenses/>.

import logging.config
import os

from dynaconf import Dynaconf, ValidationError, Validator

from gentoogram.paths import BASE_DIR

CONFIG_DIR = os.getenv("ROOT_PATH_FOR_DYNACONF", BASE_DIR / "config")

config = Dynaconf(
    envvar_prefix="CFG",
    root_path=CONFIG_DIR,
    settings_files=[
        "*.toml",
        "*.yml",
        "*.yaml",
    ],
)


def _get_logging_config(_config: Dynaconf) -> dict:
    return {
        "version": 1,
        "formatters": {
            "standard": {"format": _config.get("logger.format")},
        },
        "handlers": {
            "default": {
                "level": _config.get("logger.level"),
                "formatter": "standard",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {
                "handlers": ["default"],
                "level": _config.get("logger.level"),
                "propagate": False,
            },
        },
    }


logging.config.dictConfig(_get_logging_config(config))
logger = logging.getLogger(__name__)

config.validators.register(
    Validator(
        "telegram.token",
        must_exist=True,
        len_min=1,
        is_type_of=str,
    ),
    Validator("telegram.chat_id", must_exist=True, is_type_of=int),
    Validator("telegram.admins", must_exist=True, is_type_of=list),
    Validator(
        "webhook.enabled",
        is_type_of=bool,
        default=False,
        apply_default_on_none=True,
    )
    & Validator(
        "webhook.port", is_type_of=int, default=3020, apply_default_on_none=True
    )
    & Validator(
        "webhook.listen",
        len_min=1,
        is_type_of=str,
        default="0.0.0.0",  # noqa: S104
        apply_default_on_none=True,
    )
    & Validator(
        "webhook.listen",
        "webhook.port",
        must_exist=True,
        when=Validator("webhook.enabled", eq=True),
    ),
    Validator("webhook.url_base", startswith="https://")
    & Validator("webhook.url_path", default="/", apply_default_on_none=True)
    & Validator(
        "webhook.url_base",
        "webhook.url_path",
        must_exist=True,
        len_min=1,
        is_type_of=str,
        when=Validator("webhook.enabled", eq=True),
    ),
    Validator(
        "filters.usernames",
        "filters.messages",
        default=[],
        apply_default_on_none=True,
        is_type_of=list,
    ),
    Validator(
        "sentry.dsn",
        is_type_of=str,
        condition=lambda v: v == "" or v.startswith("https://"),
    ),
    Validator(
        "cas.enabled",
        is_type_of=bool,
        default=False,
        apply_default_on_none=True,
    )
    & Validator(
        "cas.threshold",
        is_type_of=int,
        gt=0,
        default=1,
        apply_default_on_none=True,
        must_exist=True,
        when=Validator("cas.enabled", eq=True),
    ),
    Validator(
        "logger.level",
        is_type_of=str,
        default="INFO",
        apply_default_on_none=True,
    )
    & Validator(
        "logger.format",
        is_type_of=str,
        default="%(asctime)s | %(levelname)s | %(name)s: %(message)s",
        apply_default_on_none=True,
    ),
)

try:
    config.validators.validate_all()
    logging.config.dictConfig(_get_logging_config(config))
except ValidationError as exc:
    logger.exception(exc.message)
    raise SystemExit(1) from exc
