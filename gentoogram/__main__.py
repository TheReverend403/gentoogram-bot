import logging
import os
import re
import subprocess
import sys

import sentry_sdk
import yaml
from telegram.error import TelegramError, NetworkError
from telegram.ext import MessageHandler, Filters, Updater

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger('bot')
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(base_dir)


def sentry_before_send(event, hint):
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        if isinstance(exc_value, (TelegramError, NetworkError)):
            return None

    return event


version = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('UTF-8')
with open(f'{base_dir}/settings.yml') as fd:
    config = yaml.safe_load(fd)


def main(args):
    sentry_dsn = config.get('sentry', {}).get('dsn')
    if sentry_dsn:
        sentry_sdk.init(sentry_dsn, release=version, before_send=sentry_before_send)

    token = config.get('telegram').get('token')
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, blacklist))
    dispatcher.add_handler(MessageHandler(Filters.text, blacklist))
    updater.start_polling()
    log.info('Ready!')


def blacklist(update, context):
    message = update.message
    chat = message.chat
    user = message.from_user
    name = user.first_name

    if chat.id != config.get('telegram', {}).get('chat_id', 0):
        return

    blacklists = config.get('blacklist')
    for pattern in blacklists.get('usernames'):
        if re.fullmatch(pattern, name):
            log.info(f'{name} looks like a spam bot, kicking. Regex: {pattern}')
            chat.kick_member(user.id)
            message.delete()
            break

    for pattern in blacklists.get('messages'):
        if re.fullmatch(pattern, message.text):
            log.info(f'Deleted message {message}. Regex: {pattern}')
            message.delete()
            break


if __name__ == '__main__':
    main(sys.argv)
