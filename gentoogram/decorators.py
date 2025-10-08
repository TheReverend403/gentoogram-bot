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
from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram import Update
    from telegram.constants import ChatAction
    from telegram.ext import ContextTypes

from gentoogram.config import config

logger = logging.getLogger(__name__)


def admin(func):
    @wraps(func)
    async def wrapped(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user = update.effective_user
        if user.id not in config.get("telegram.admins"):
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
