#!/usr/bin/env python3
"""
Usage: %(script_name)s { -h | --help }
       %(script_name)s [ { -c | --config-file } FILE ]
            [ { -i | --telegram-id } UUID }

Start the Telegram/Zabbix bot.

Arguments:
    -h, --help      This message
    -c FILE, --config-file FILE     The location of the config file.
    -i UUID, --telegram-id UUID     The UUID of your Telegram bot as returned
                    by @BotFather. It is discouraged to specify this on the
                    command line (although it is useful for testing); use
                    the config file instead.

Command line arguments override their equivalent settings in the config file
when specified.
"""

import sys, configparser, telebot
import getopt
import logging
import os.path


def usage():
    print (__doc__ % {'script_name': os.path.basename(sys.argv[0])}, file=sys.stderr)


def parse_commandline(argv = sys.argv[1:]):
    try:
        optlist, args = getopt.getopt(
                argv,
                'c:hi:',
                [ 'config-file=', 'help', 'telegram-id=' ]
        )
    except getopt.GetoptError as err:
        log = logging.getLogger(__name__)
        log.error('Error parsing command line options: %s', err)
        usage()
        sys.exit(1)

    for opt, arg in optlist:
        # TODO Parse command line options
        pass



def main():
    logging.basicConfig(format='%(message)s')

    parse_commandline()

    config = configparser.ConfigParser()

    # Open settings.ini file to retrieve API token
    try:
            with open('settings.ini') as f:
                    config.read_file(f)
    except:
            e = sys.exc_info()[1]
            print(e)
            sys.exit(1)

    token = config.get('TelegramSettings','API-Token')

    # initialise Bot
    try:
            bot = telebot.TeleBot(token)
            bot_info = bot.get_me()
    except:
            e = sys.exc_info()[1]
            print(e)
            sys.exit(1)

    # Bot handlers below
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
            bot.reply_to(message, "Howdy, how are you doing?")

    @bot.message_handler(func=lambda message: True)
    def echo_all(message):
            bot.reply_to(message, message.text)

    # Start the bot
    bot.infinity_polling()


if __name__ == '__main__':
    main()

