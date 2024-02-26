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

import logging
import re
import secrets
from functools import wraps

import httpx
import sentry_sdk
from telegram import Chat, Update
from telegram.constants import ParseMode
from telegram.error import NetworkError, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from gentoogram import version
from gentoogram.config import config

logger = logging.getLogger(__name__)

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
        user_id = update.effective_user.id
        if user_id != config.get("telegram.admin_id"):
            logger.debug(f"User {user_id} was denied access to {func.__name__}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="That command can only be used by bot admins. Which you are not.",
            )
            return None
        return await func(update, context, *args, **kwargs)

    return wrapped


def main():
    sentry_dsn = config.get("sentry.dsn")
    if sentry_dsn:
        sentry_sdk.init(
            sentry_dsn, release=version.VERSION, before_send=sentry_before_send
        )

    token = config.get("telegram.token")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("reload", cmd_reload))
    app.add_handler(CommandHandler("version", cmd_version))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, chat_filter))
    app.add_handler(MessageHandler(filters.TEXT, chat_filter))
    app.add_handler(MessageHandler(filters.FORWARDED, chat_filter))

    if not config.get("webhook.enabled", False):
        app.run_polling()
    else:
        listen_addr = config.get("webhook.listen", "0.0.0.0")  # noqa: S104
        port = config.get("webhook.port", 3020)
        url_base = config.get("webhook.url_base")
        url_path = config.get("webhook.url_path", "/")
        url = f"{url_base}{url_path}"
        secret_token = secrets.token_hex()

        app.run_webhook(
            listen=listen_addr,
            port=port,
            webhook_url=url,
            url_path=url_path,
            secret_token=secret_token,
        )

    logger.info("Ready!")


@admin
async def cmd_reload(update: Update, context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    config.reload()
    logger.debug("Config reloaded.")
    reply_to = (
        update.effective_message.id
        if update.effective_chat.type != Chat.PRIVATE
        else None
    )
    await update.effective_chat.send_message(
        reply_to_message_id=reply_to,
        text="Config reloaded!",
    )


async def cmd_version(update: Update, context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    reply_to = (
        update.effective_message.id
        if update.effective_chat.type != Chat.PRIVATE
        else None
    )
    await update.effective_chat.send_message(
        reply_to_message_id=reply_to,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        text=f"<a href='https://github.com/TheReverend403/gentoogram-bot'>gentoogram-bot {version.VERSION}</a>",
    )


async def is_spammer(user_id: int) -> bool:
    if not config.get("cas.enabled", True):
        return True

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.cas.chat/check?user_id={user_id}", timeout=5
            )
            check_result = response.json()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning(exc)
        return False

    if check_result.get("ok"):
        offenses = check_result.get("result").get("offenses")
        if offenses >= config.get("cas.threshold", 1):
            logger.info(
                f"User {user_id} failed CAS spam check with {offenses} offense(s)."
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
    username = user.username if user.username else ""

    full_name = f"{user.first_name}"
    if user.last_name:
        full_name += f" {user.last_name}"

    log_data = {
        "user": {
            "id": user.id,
            "username": username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
        "chat": {"id": chat.id, "type": chat.type, "username": chat.username},
    }

    _filters = config.get("filters")
    for pattern in _filters.get("usernames"):
        if re.search(pattern, full_name, re_flags) or re.search(
            pattern, username, re_flags
        ):
            log_data.update({"regex": pattern})
            logger.info(f"Username filter match: {log_data}")

            if await chat.ban_member(user.id) and await message.delete():
                logger.info(f"Banned user {user.id}.")
            else:
                logger.info(f"Could not kick user {user.id}.")

            break

    # This is a new chat member event.
    if not message.text:
        if await is_spammer(user.id):
            logger.info(f"CAS check match: {log_data}")
            if await chat.ban_member(user.id) and await message.delete():
                logger.info(f"Kicked user {user.id} (CAS).")
            else:
                logger.info(f"Could not kick user {user.id} (CAS).")
            return
        return

    for pattern in _filters.get("messages"):
        if re.search(pattern, message.text, re_flags):
            log_data.update(
                {
                    "message": {"id": message.message_id, "text": message.text},
                    "regex": pattern,
                }
            )
            logger.info(f"Message filter match: {log_data}")
            if await message.delete():
                logger.info(f"Deleted message {message.message_id}")
            else:
                logger.info(f"Could not delete message {message.message_id}")
            break


if __name__ == "__main__":
    main()
