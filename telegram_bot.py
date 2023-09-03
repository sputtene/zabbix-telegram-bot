#!/usr/bin/env python3
"""
Usage: %(script_name)s { -h | --help }
       %(script_name)s [ { -c | --config-file } FILE ]
            [ { -t | --telegram-id } UUID }

Start the Telegram/Zabbix bot.

Arguments:
    -h, --help      This message
    -c FILE, --config-file FILE     The location of the config file.
    -t UUID, --telegram-id UUID     The UUID of your Telegram bot as returned
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
    cmdline_config = {}

    try:
        optlist, args = getopt.getopt(
                argv,
                'c:ht:',
                [ 'config-file=', 'help', 'telegram-id=' ]
        )
    except getopt.GetoptError as err:
        log = logging.getLogger(__name__)
        log.error('Error parsing command line options: %s', err)
        usage()
        sys.exit(1)

    for opt, arg in optlist:
        if opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif opt in ('-c', '--config-file'):
            cmdline_config['config-file'] = arg
        elif opt in ('-t', '--telegram-id'):
            cmdline_config['telegram-id'] = arg
        else:
            assert False, 'Unhandled command line option [%(opt)s]' % {'opt': opt};

    return cmdline_config


def main():
    logging.basicConfig(format='%(message)s')

    cmdline_config = parse_commandline()

    configfile_parser = configparser.ConfigParser()
    # Open settings.ini file to retrieve API token
    try:
            with open(cmdline_config['config-file'] if 'config-file' in cmdline_config else 'settings.ini') as f:
                    configfile_parser.read_file(f)
    except:
            e = sys.exc_info()[1]
            print(e)
            sys.exit(1)

    # Put configuration in the actual config dictionary. Use the value specified
    # on the command line if it has a value, fall back to the config file if it
    # does not.
    config = {}
    for cmdline_option, configfile_option, name in [
        ( 'telegram-id', ('TelegramSettings', 'API-Token'), 'telegram-API-token' ),
    ]:
        print("Parsing config option %(name)s" % {'name': name})
        config[name] = cmdline_config[cmdline_option] if cmdline_option in cmdline_config else configfile_parser.get(configfile_option[0], configfile_option[1], fallback=None)

    token = config['telegram-API-token']

    if token == '':
        log = logging.getLogger(__name__)
        log.error('No Telegram API token specified. Configure it in the config file or specify it on the command line')
        sys.exit(1)

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

