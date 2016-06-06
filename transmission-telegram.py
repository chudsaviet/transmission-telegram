import argparse
import logging
from bot_config import BotConfig
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from transmission_broker import TransmissionBroker, NotAuthorizedChatException
from transmissionrpc.error import TransmissionError

LOGGING_FORMAT = '%(filename)s:%(lineno)d# %(levelname)s %(asctime)s: %(message)s'
VERSION = '2'
HELP_TEXT = 'Transmission Telegram bot version %s\n\n' \
            'Usage:\n' \
            '/help - display this help\n' \
            '/secret <SECRET> - authorize using secret\n' \
            '/list - retrieve list of current torrents and their statuses\n' \
            '/add <URI> - add torrent and start download\n' \
            '/remove <TORRENT_ID> <TORRENT_ID> ... - remove torrents by IDs\n' \
            % VERSION

# Sorry, using global variable here is inevitable because of Telegram library's API
global_broker = None


def check_connection(bot, update):
    try:
        global_broker.check_chat_authorization(update.message.chat_id)
    except NotAuthorizedChatException as e:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Please, authorize using /secret command")
        return False

    return True


def help_command(bot, update):
    bot.sendMessage(chat_id=update.message.chat_id,
                    text=HELP_TEXT)


def remove_command(bot, update):
    if not check_connection(bot, update):
        return

    torrent_ids = list()
    try:
        for string_id in update.message.text.split(' ')[1:]:
            torrent_ids.append(int(string_id))
    except ValueError as e:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Wrong torrent IDs: %s\nException:\n%s" % (update.message.text.split(' ', 1)[1], str(e)))
        return

    bot.sendMessage(chat_id=update.message.chat_id,
                    text="Removing torrents: %s ..." % torrent_ids)

    try:
        global_broker.remove_torrent(update.message.chat_id, torrent_ids)

        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Torrents successfully removed")
    except TransmissionError as e:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Exception happened while trying to remove torrents:\n%s\nNothing removed." % str(e))


def add_command(bot, update):
    if not check_connection(bot, update):
        return

    bot.sendMessage(chat_id=update.message.chat_id,
                    text="Adding torrent to Transmission")

    try:
        global_broker.add_torrent(update.message.chat_id, update.message.text.split(' ', 1)[1])

        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Torrent successfully added")
    except TransmissionError as e:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Exception happened while trying to add torrent:\n%s" % str(e))


def list_command(bot, update):
    if not check_connection(bot, update):
        return

    bot.sendMessage(chat_id=update.message.chat_id,
                    text="Got it, retrieving list of current torrents...")

    torrents = global_broker.retrieve_list(update.message.chat_id)

    bot.sendMessage(chat_id=update.message.chat_id,
                    text="Here are current torrents list:\n%s" % str(torrents))


def error_command(bot, update, error):
    logging.warning('Update "%s" caused error "%s"' % (update, error))


def secret_command(bot, update):

    secret = update.message.text.split(' ', 1)[1]

    if global_broker.authorize_chat(update.message.chat_id, secret):
        bot.sendMessage(chat_id=update.message.chat_id,
                        text='Authorization successful')
    else:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text='Secret is wrong')


def run(config):
    updater = Updater(token=config.token)
    dispatcher = updater.dispatcher
    dispatcher.add_error_handler(error_command)

    list_handler = CommandHandler('list', list_command)
    dispatcher.add_handler(list_handler)

    add_handler = CommandHandler('add', add_command)
    dispatcher.add_handler(add_handler)

    remove_handler = CommandHandler('remove', remove_command)
    dispatcher.add_handler(remove_handler)

    help_handler = CommandHandler('help', help_command)
    dispatcher.add_handler(help_handler)

    start_handler = CommandHandler('start', help_command)
    dispatcher.add_handler(start_handler)

    secret_handler = CommandHandler('secret', secret_command)
    dispatcher.add_handler(secret_handler)

    unknown_handler = MessageHandler([Filters.command], help_command)
    dispatcher.add_handler(unknown_handler)

    updater.start_polling()
    updater.idle()


def main():
    parser = argparse.ArgumentParser(
        description='Bot for controlling Transmission over Telegram. Version %s.' % VERSION
    )
    parser.add_argument('--config', required=True,
                        help='Path to config ini-formatted file')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Debug log level')
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format=LOGGING_FORMAT, level=logging.DEBUG)
        logging.info('Debug log level activated')
    else:
        logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)

    config = BotConfig(args.config)
    logging.info('Will use next config parameters:\n%s' % config)

    global global_broker
    global_broker = TransmissionBroker(config)

    run(config)


if __name__ == '__main__':
    main()
