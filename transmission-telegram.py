import argparse
import logging
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from credentials import Credentials
from transmission_broker import TransmissionBroker, NoConnectionException
from transmissionrpc.error import TransmissionError

LOGGING_FORMAT = '%(filename)s:%(lineno)d# %(levelname)s %(asctime)s: %(message)s'
VERSION = '1'
HELP_TEXT = 'Transmission Telegram bot version %s\n\n' \
            'Usage:\n' \
            '/help - display this help\n' \
            '/set_credentials address=<ADDRESS> port=<PORT> user=<user> password=<password>' \
            ' - set credentials and connect to Transmission\n' \
            '/list - retrieve list of current torrents and their statuses\n' \
            '/add <URI> - add torrent and start download\n' \
            '/remove <TORRENT_ID> <TORRENT_ID> ... - remove torrents by IDs. ID can be determined using /list command\n' \
            % VERSION
global_args = None
broker = TransmissionBroker()


def parse_credentials(definition):
    address = None
    port = None
    user = None
    password = None

    pairs = definition.split()

    for pair in pairs:
        parameter, value = tuple([v.strip() for v in pair.split('=')])
        if parameter == 'address':
            address = value
        elif parameter == 'port':
            port = value
        elif parameter == 'user':
            user = value
        elif parameter == 'password':
            password = value

    return Credentials(address, port, user, password)


def check_connection(bot, update):
    try:
        broker.check_connection(update.message.chat_id)
    except NoConnectionException as e:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Please, setup connection using /set_credentials")
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
        broker.remove_torrent(update.message.chat_id, torrent_ids)

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
        broker.add_torrent(update.message.chat_id, update.message.text.split(' ',1)[1])

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

    torrents = broker.retrieve_list(update.message.chat_id)

    bot.sendMessage(chat_id=update.message.chat_id,
                    text="Here are current torrents list:\n%s" % str(torrents))


def set_credentials_command(bot, update):
    credentials = parse_credentials(update.message.text.split(' ', 1)[1])

    bot.sendMessage(chat_id=update.message.chat_id,
                    text="You entered:\n\n%s\nOk, testing connection to Transmission..."
                    % str(credentials))

    try:
        broker.open_connection(update.message.chat_id, credentials)
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Successfully connected to Transmission at %s"
                             % credentials.address)
    except TransmissionError as e:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Cannot connect to Transmission at %s\nError: %s"
                             % (credentials.address, str(e)))


def error_command(bot, update, error):
    logging.warning('Update "%s" caused error "%s"' % (update, error))


def run():
    global global_args
    updater = Updater(token=global_args.token)
    dispatcher = updater.dispatcher
    dispatcher.add_error_handler(error_command)

    set_credentials_handler = CommandHandler('set_credentials', set_credentials_command)
    dispatcher.add_handler(set_credentials_handler)

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

    unknown_handler = MessageHandler([Filters.command], help_command)
    dispatcher.add_handler(unknown_handler)

    updater.start_polling()
    updater.idle()


def main():
    parser = argparse.ArgumentParser(
        description='Bot for controlling Transmission over Telegram. Version %s.' % VERSION
    )
    parser.add_argument('token',
                        help='Telegram bot token')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Debug log level')
    parser.add_argument('-p', '--pid_file', action='store',
                        help='File to store daemon''s PID')
    args = parser.parse_args()

    global global_args
    global_args = args

    if args.verbose:
        logging.basicConfig(format=LOGGING_FORMAT, level=logging.DEBUG)
        logging.info('Debug log level activated')
    else:
        logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO)

    run()


if __name__ == '__main__':
    main()
