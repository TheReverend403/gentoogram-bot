import logging
import re
import sys

from dynaconf import settings
from telegram.ext import MessageHandler, Filters, Updater

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger('bot')


def create_updater(token):
    updater = Updater(token=token, use_context=True)
    return updater


def main(args):
    token = settings['token']
    updater = create_updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(spam_handler)
    updater.start_polling()
    logger.info('Ready!')


def anti_china_spam(update, context):
    if not update.message.chat_id == settings['chat_id']:
        return
    name = update.message.from_user.first_name
    if re.fullmatch(r'[\u4e00-\u9fff]{3}', name):
        logger.info(f'{name} looks like a Chinese spam bot, kicking.')
        update.chat.kick_chat_member(update.message.from_user.id)
        update.message.delete()


spam_handler = MessageHandler(Filters.status_update.new_chat_members, anti_china_spam)

if __name__ == '__main__':
    main(sys.argv)
