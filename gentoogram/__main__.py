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
from logging.config import dictConfig

import requests
import sentry_sdk
from telegram.error import NetworkError, TelegramError
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from gentoogram.config import Config

config = Config()
dictConfig(config.get('logging'))
logger = logging.getLogger('gentoogram')
version = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('UTF-8')
re_flags = re.UNICODE | re.IGNORECASE | re.DOTALL


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
            logger.debug(f'User {user_id} was denied access to {func.__name__}')
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text='That command can only be used by bot admins. Which you are not.')
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
    dispatcher.add_handler(MessageHandler(Filters.forwarded, chat_filter))
    updater.start_polling()
    logger.info('Ready!')


@admin
def reload_config(update, context):
    config.load()
    logger.debug('Config reloaded.')
    context.bot.send_message(chat_id=update.effective_chat.id, text='Config reloaded!')


def is_spammer(user_id: int) -> bool:
    try:
        with requests.get(f'https://api.cas.chat/check?user_id={user_id}', timeout=5) as response:
            check_result = response.json()
    except (requests.RequestException, TimeoutError) as exc:
        logger.warning(exc)
        return False

    return not check_result.get('ok')


def chat_filter(update, context):
    logger.debug(f'{update}')

    message = update.effective_message
    if not message:
        return

    chat = update.effective_chat
    if chat.id not in [int(chat) for chat in config.get('telegram', {}).get('chats', [])]:
        return

    user = update.effective_user
    if is_spammer(user.id):
        if chat.kick_member(user.id) and message.delete():
            logger.info(f'Kicked user {user.id} (CAS).')
        else:
            logger.info(f'Could not kick user {user.id}.')
        return

    username = user.username if user.username else ''

    full_name = f'{user.first_name}'
    if user.last_name:
        full_name += f' {user.last_name}'

    log_data = {
        'user': {
            'id': user.id,
            'username': username,
            'first_name': user.first_name,
            'last_name': user.last_name
        },
        'chat': {
            'id': chat.id,
            'type': chat.type,
            'username': chat.username
        }
    }

    filters = config.get('filters')
    for pattern in filters.get('usernames'):
        if re.search(pattern, full_name, re_flags) or re.search(pattern, username, re_flags):
            log_data.update({'regex': pattern})
            logger.info(f'Username filter match: {log_data}')

            if chat.kick_member(user.id) and message.delete():
                logger.info(f'Kicked user {user.id}.')
            else:
                logger.info(f'Could not kick user {user.id}.')

            break

    if not message.text:
        return

    for pattern in filters.get('messages'):
        if re.search(pattern, message.text, re_flags):
            log_data.update({
                'message': {
                    'id': message.message_id,
                    'text': message.text
                },
                'regex': pattern
            })
            logger.info(f'Message filter match: {log_data}')
            if message.delete():
                logger.info(f'Deleted message {message.message_id}')
            else:
                logger.info(f'Could not delete message {message.message_id}')
            break


if __name__ == '__main__':
    main(sys.argv)
