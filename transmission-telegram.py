#!/usr/bin/env python3

import argparse
import logging
import logging.handlers
import sys
import os
import time
import signal
from bot_config import BotConfig
from persistence import Persistence
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from transmission_broker import TransmissionBroker, NotAuthorizedChatException
from transmissionrpc.error import TransmissionError

import platform

LINUX = (platform.system() == 'Linux')
if LINUX:
    SYSLOG_DEVICE = '/dev/log'

LOGGING_FORMAT_STDOUT = '%(filename)s:%(lineno)d# %(levelname)s %(asctime)s: %(message)s'
LOGGING_FORMAT_SYSLOG = 'transmission-telegram: %(filename)s:%(lineno)d# %(levelname)s: %(message)s'
VERSION = '2'
HELP_TEXT = 'Transmission Telegram bot version %s\n\n' \
            'Usage:\n' \
            '/help - display this help\n' \
            '/secret <SECRET> - authorize using secret\n' \
            '/list - retrieve list of current torrents and their statuses\n' \
            '/add <URI> - add torrent and start download\n' \
            '/remove <TORRENT_ID> <TORRENT_ID> ... - remove torrents by IDs\n' \
            % VERSION


# Sorry, using global variables here is inevitable because of Telegram library's API
global_broker = None
global_updater = None
global_error_exit = False


def check_connection(bot, update):
    try:
        global_broker.check_chat_authorization(update.message.chat_id)
    except NotAuthorizedChatException as e:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Please, authorize using /secret command")
        return False

    return True


def transmission_error(bot, update, exception):
    # Will send error to chat and syslog, and exit. Systemd should restart bot.
    error_message = "Transmission exception happened:\n%s" % str(exception)
    bot.sendMessage(chat_id=update.message.chat_id,
                    text=error_message)
    logging.error(error_message)

    global global_error_exit
    global_error_exit = True
    # SIGTERM is to be handled by Updater
    #os.kill(os.getpid(), signal.SIGABRT)


def telegram_error(bot, update, error):
    # Will only send error to syslog and exit. Systemd should restart bot.
    error_message = 'Update "%s" caused error "%s"' % (update, error)
    logging.error(error_message)
    global global_error_exit
    global_error_exit = True
    # SIGTERM is to be handled by Updater
    # os.kill(os.getpid(), signal.SIGABRT)


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
        transmission_error(bot, update, e)


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
        transmission_error(bot, update, e)


def list_command(bot, update):
    if not check_connection(bot, update):
        return

    bot.sendMessage(chat_id=update.message.chat_id,
                    text="Got it, retrieving list of current torrents...")
    try:
        torrents = global_broker.retrieve_list(update.message.chat_id)
        bot.sendMessage(chat_id=update.message.chat_id,
                        text="Here are current torrents list:\n%s" % str(torrents))
    except TransmissionError as e:
        transmission_error(bot, update, e)


def secret_command(bot, update):

    secret = update.message.text.split(' ', 1)[1]

    if global_broker.authorize_chat(update.message.chat_id, secret):
        bot.sendMessage(chat_id=update.message.chat_id,
                        text='Authorization successful')
    else:
        bot.sendMessage(chat_id=update.message.chat_id,
                        text='Secret is wrong')


def setup_logging(linux_daemon, verbose):
    logger = logging.getLogger()

    if linux_daemon:
        # If we are Linux daemon, print logs to syslog
        handler = logging.handlers.SysLogHandler(address=SYSLOG_DEVICE)
        formatter = logging.Formatter(LOGGING_FORMAT_SYSLOG)
    else:
        # If we are not Linux daemon, just print logs to stdout
        handler = logging.StreamHandler()
        formatter = logging.Formatter(LOGGING_FORMAT_STDOUT)

    handler.setFormatter(formatter)
    # Clean handlers
    logger.handlers = []
    # Add appropriate handler
    logger.addHandler(handler)

    if verbose:
        logger.setLevel(logging.DEBUG)
        logging.info('Debug log level activated')
    else:
        logger.setLevel(logging.INFO)


def daemonize(pid_file):
    # Fork off the parent process
    pid = os.fork()

    # If we are in parent process - save child PID and return True
    # If we are in child process - proceed to next steps
    if pid > 0:
        file = open(pid_file, 'w')
        file.write(str(pid))
        file.close()
        return True

    # Change the file mode mask
    os.umask(0)

    # Create a new SID for the child process
    os.setsid()

    # Change the current working directory
    os.chdir('/')

    # Close IO
    sys.stdin.close()
    sys.stdout.close()
    sys.stderr.close()

    return False


def run(args):
    logging.info('Starting bot')

    config = BotConfig(args.config)
    logging.info('Will use next config parameters:\n%s' % config)

    global global_broker
    global_broker = TransmissionBroker(config, Persistence(config.persistence_file))

    global global_updater
    global_updater = Updater(token=config.token)
    dispatcher = global_updater.dispatcher
    dispatcher.add_error_handler(telegram_error)

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

    global_updater.start_polling()

    global global_error_exit
    global_updater.is_idle = True
    while global_updater.is_idle:
        if global_error_exit:
            global_updater.stop()
            sys.exit(1)

        time.sleep(0.1)


def main():
    parser = argparse.ArgumentParser(
        description='Bot for controlling Transmission over Telegram. Version %s.' % VERSION
    )
    parser.add_argument('--config', required=True,
                        help='Path to config ini-formatted file')
    if LINUX:
        parser.add_argument('--daemon_pid_file', required=False,
                            help='Run as daemon and save PID to specified file')
    parser.add_argument('--log', required=False,
                            help='File to store log')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Debug log level')
    args = parser.parse_args()

    if LINUX and args.daemon_pid_file:
        # Exit if we are in parent process
        if daemonize(args.daemon_pid_file):
            sys.exit()
        setup_logging(linux_daemon=True, verbose=args.verbose)
    else:
        setup_logging(linux_daemon=False, verbose=args.verbose)

    try:
        run(args)
    except Exception as e:
        logging.error(e)
        sys.exit(1)

if __name__ == '__main__':
    main()

