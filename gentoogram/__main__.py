import logging
import re
import subprocess
import sys

import sentry_sdk
from dynaconf import settings
from telegram.error import Conflict, NetworkError
from telegram.ext import MessageHandler, Filters, Updater

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger('bot')


def sentry_before_send(event, hint):
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        if isinstance(exc_value, (Conflict, NetworkError)):
            return None

    return event


version = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('UTF-8')
sentry_sdk.init(settings['sentry_dsn'], release=version, before_send=sentry_before_send)


def main(args):
    token = settings['token']
    updater = Updater(token=token, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, anti_china_spam))
    updater.start_polling()
    log.info('Ready!')


def anti_china_spam(update, context):
    message = update.message
    chat = message.chat
    user = message.from_user
    name = user.first_name

    if chat.id != settings['chat_id']:
        return

    if re.fullmatch(r'^[\u4e00-\u9fff]+$', name):
        log.info(f'{name} looks like a Chinese spam bot, kicking.')
        chat.kick_member(user.id)
        message.delete()


if __name__ == '__main__':
    main(sys.argv)
