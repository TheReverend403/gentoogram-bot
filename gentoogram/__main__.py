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

import re
import secrets
import sys
from functools import wraps

import httpx
import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.loguru import LoguruIntegration
from telegram import Update, User
from telegram.constants import ChatAction, ParseMode
from telegram.error import NetworkError, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from gentoogram import meta
from gentoogram.config import config

re_flags = re.UNICODE | re.IGNORECASE | re.DOTALL


def sentry_before_send(event, hint):
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]
        if isinstance(exc_value, TelegramError | NetworkError):
            return None

    return event


def admin(func):
    @wraps(func)
    async def wrapped(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user = update.effective_user
        if user.id != config.get("telegram.admin_id"):
            logger.info(
                f"{user.full_name} ({user.id}) was denied access to {func.__name__}"
            )
            await update.effective_chat.send_message(
                reply_to_message_id=update.effective_message.id,
                text="That command can only be used by bot admins. Which you are not.",
            )
            return None
        return await func(update, context, *args, **kwargs)

    return wrapped


def send_action(action: ChatAction):
    def decorator(func):
        @wraps(func)
        async def command_func(
            update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
        ):
            await update.effective_chat.send_chat_action(action=action)
            return await func(update, context, *args, **kwargs)

        return command_func

    return decorator


def main():
    logger.remove()
    logger.add(
        sys.stderr,
        colorize=config.get("logger.colorize", True),
        format=config.get(
            "logger.format",
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level}</level> | "
            "{message}",
        ),
        level=config.get("logger.level", "INFO"),
    )

    sentry_dsn = config.get("sentry.dsn")
    if sentry_dsn:
        sentry_sdk.init(
            sentry_dsn,
            release=meta.VERSION,
            before_send=sentry_before_send,
            integrations=[
                LoguruIntegration(),
            ],
        )

    token = config.get("telegram.token")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CommandHandler("version", cmd_version))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, chat_filter))
    app.add_handler(MessageHandler(filters.TEXT, chat_filter))
    app.add_handler(MessageHandler(filters.FORWARDED, chat_filter))

    if not config.get("webhook.enabled", False):
        logger.info("Running in polling mode")
        app.run_polling()
    else:
        listen_addr = config.get("webhook.listen", "0.0.0.0")  # noqa: S104
        port = config.get("webhook.port", 3020)
        url_base = config.get("webhook.url_base")
        url_path = config.get("webhook.url_path", "/")
        url = f"{url_base}{url_path}"
        secret_token = secrets.token_hex()

        logger.info(f"Running in webhook mode ({url_base}{url_path})")
        app.run_webhook(
            listen=listen_addr,
            port=port,
            webhook_url=url,
            url_path=url_path,
            secret_token=secret_token,
        )


@admin
@send_action(ChatAction.TYPING)
async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    config.reload()
    user = update.effective_user
    logger.info(f"Config reloaded by {user.full_name} ({user.id})")
    await update.effective_chat.send_message(
        reply_to_message_id=update.effective_message.id,
        text="Success!",
    )


@send_action(ChatAction.TYPING)
async def cmd_version(update: Update, context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    await update.effective_chat.send_message(
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_to_message_id=update.effective_message.id,
        text=f"<a href='https://github.com/TheReverend403/gentoogram-bot'>gentoogram-bot {meta.VERSION}</a>",
    )


async def is_spammer(user: User) -> bool:
    if not config.get("cas.enabled", False):
        return False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.cas.chat/check?user_id={user.id}", timeout=5
            )
            check_result = response.json()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning(exc)
        return False

    if check_result.get("ok"):
        offenses = check_result.get("result").get("offenses")
        if offenses >= config.get("cas.threshold", 1):
            logger.info(
                f"[CAS] {user.full_name} ({user.id}) failed check with {offenses} offense(s)"
            )
            return True

    return False


async def chat_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):  # noqa: C901, ARG001
    logger.debug(f"{update}")

    message = update.effective_message
    if not message:
        return

    chat = update.effective_chat
    if chat.id != int(config.get("telegram.chat_id")):
        return

    user = update.effective_user

    log_data = {
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
        },
        "chat": {"id": chat.id, "type": chat.type, "username": chat.username},
    }

    _filters = config.get("filters")
    for pattern in _filters.get("usernames"):
        if re.search(pattern, user.full_name, re_flags) or re.search(
            pattern, user.username, re_flags
        ):
            log_data.update({"regex": pattern})
            logger.info(f"Username filter match: {log_data}")

            if await chat.ban_member(user.id):
                logger.info(f"Banned {user.id}")
            else:
                logger.info(f"Failed to ban {user.id}")

            if not await message.delete():
                logger.warning(f"Failed to delete message {message.id}")

            break

    # This is a new chat member event.
    if not message.text:
        if await is_spammer(user):
            if await chat.ban_member(user.id):
                logger.info(f"[CAS] Banned {user.id}")
            else:
                logger.warning(f"[CAS] Failed to ban {user.id}")

            if not await message.delete():
                logger.warning(f"[CAS] Failed to delete message {message.id}")

            return
        return

    for pattern in _filters.get("messages"):
        if re.search(pattern, message.text, re_flags):
            log_data.update(
                {
                    "message": {"id": message.id, "text": message.text},
                    "regex": pattern,
                }
            )
            logger.info(f"Message filter match: {log_data}")
            if await message.delete():
                logger.info(f"Deleted message {message.id}")
            else:
                logger.warning(f"Failed to delete message {message.id}")
            break


if __name__ == "__main__":
    main()
