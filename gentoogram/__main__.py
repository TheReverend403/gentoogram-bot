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
import subprocess
import sys
from functools import wraps

import sentry_sdk
from telegram.error import NetworkError, TelegramError
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from gentoogram.config import Config

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
version = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('UTF-8')
config = Config()


def sentry_before_send(event, hint):
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        if isinstance(exc_value, (TelegramError, NetworkError)):
            return None

    return event


def admin(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in config.get('admins', []):
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="That command can only be used by bot admins. Which you are not.")
            return
        return func(update, context, *args, **kwargs)

    return wrapped


def main(args):
    sentry_dsn = config.get('sentry', {}).get('dsn')
    if sentry_dsn:
        sentry_sdk.init(sentry_dsn, release=version, before_send=sentry_before_send)

    token = config.get('telegram').get('token')
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('reload', reload_config))
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, chat_filter))
    dispatcher.add_handler(MessageHandler(Filters.text, chat_filter))
    updater.start_polling()
    logging.info('Ready!')


@admin
def reload_config(update, context):
    config.reload()
    context.bot.send_message(chat_id=update.effective_chat.id, text="Config reloaded!")


def chat_filter(update, context):
    message = update.message
    chat = message.chat
    user = message.from_user
    name = user.first_name

    if chat.id != config.get('telegram', {}).get('chat_id', 0):
        return

    filters = config.get('filters')
    for pattern in filters.get('usernames'):
        if re.fullmatch(pattern, name):
            logging.info(f'{name} looks like a spam bot, kicking. Regex: {pattern}')
            chat.kick_member(user.id)
            message.delete()
            break

    for pattern in filters.get('messages'):
        if re.fullmatch(pattern, message.text):
            logging.info(f'Deleted message {message}. Regex: {pattern}')
            message.delete()
            break


if __name__ == '__main__':
    main(sys.argv)
