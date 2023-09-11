#!/usr/bin/env python3
"""
Usage: %(script_name)s { -h | --help }
       %(script_name)s [ { -c | --config-file } FILE ]
            [ { -t | --telegram-id } UUID ] [ { -v | --verbose } ]
            [ { -d | --debug } ]

Start the Telegram/Zabbix bot.

Arguments:
    -h, --help      This message
    -c FILE, --config-file FILE     The location of the config file.
    -t UUID, --telegram-id UUID     The UUID of your Telegram bot as returned
                    by @BotFather. It is discouraged to specify this on the
                    command line (although it is useful for testing); use
                    the config file instead.
    -v, --verbose                   Extra verbose output.
    -d, --debug                     Enable debugging output. This implicitly
                    enables --verbose as well.

Command line arguments override their equivalent settings in the config file
when specified.
"""

__version__ = '0.1a1'


import sys, configparser, telebot
import getopt
import logging
import os.path

from pyzabbix import ZabbixAPI

import telegram.commands
import zabbix_frontend


def usage():
    print (__doc__ % {'script_name': os.path.basename(sys.argv[0])}, file=sys.stderr)


def parse_commandline(argv = sys.argv[1:]):
    cmdline_config = {
            'config-file': 'settings.ini',
            'telegram-id': None,
            'verbose': False,
            'debug': False,
    }

    try:
        optlist, args = getopt.getopt(
                argv,
                'c:ht:vd',
                [ 'config-file=', 'help', 'telegram-id=', 'verbose', 'debug' ]
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
        elif opt in ('-v', '--verbose'):
            cmdline_config['verbose'] = True
        elif opt in ('-d', '--debug'):
            cmdline_config['debug'] = True
        else:
            assert False, 'Unhandled command line option [%(opt)s]' % {'opt': opt};

    if cmdline_config['debug']:
        logging.getLogger().setLevel(level = logging.DEBUG)
    elif cmdline_config['verbose']:
        logging.getLogger().setLevel(level = logging.INFO)

    return cmdline_config


def main():
    logging.basicConfig(format='%(message)s')

    cmdline_config = parse_commandline()
    logging.debug("Config: %s", cmdline_config)

    configfile_parser = configparser.ConfigParser()
    # Open settings.ini file to retrieve API token
    try:
            with open(cmdline_config['config-file']) as f:
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
        ( 'telegram-id', ('Telegram Settings', 'API-Token'), 'telegram-API-token' ),
        ( None, ('Zabbix Settings', 'Server'), 'zabbix-server' ),
        ( None, ('Zabbix Settings', 'Token'), 'zabbix-token' ),
        ( None, ('Zabbix Settings', 'Username'), 'zabbix-username' ),
        ( None, ('Zabbix Settings', 'Password'), 'zabbix-password' ),
        ( None, ('Zabbix Settings', 'TelegramMediaType'), 'zabbix-telegram-mediatype'),
    ]:
        logging.debug("Parsing config option %(name)s" % {'name': name})
        config[name] = cmdline_config[cmdline_option] if cmdline_config.get(cmdline_option) else configfile_parser.get(configfile_option[0], configfile_option[1], fallback=None)

    telegram_token = config['telegram-API-token']

    if telegram_token == '':
        log = logging.getLogger(__name__)
        log.error('No Telegram API token specified. Configure it in the config file or specify it on the command line')
        sys.exit(1)

    # Initialize Zabbix API connector
    zapi = ZabbixAPI(config['zabbix-server'])

    if config.get('zabbix-token'):
        logging.debug('Using API token to log in to the Zabbix API')
        zapi.login(api_token = config.get('zabbix-token'))
    else:
        logging.debug('Using username/password to log in to the Zabbix API')
        zapi.login(config['zabbix-username'], config['zabbix-password'])

    logging.info('Connected to Zabbix API version %s, host: %s', zapi.api_version(), config['zabbix-server'])

    zabbix_frontend.init(config['zabbix-server'], config['zabbix-username'], config['zabbix-password'])


    # Get Zabbix users who have Telegram media configured, with their "sendto"
    # values.
    # The "sendto" values are assumed to be Telegram user ID's, which are used
    # to figure out which (Zabbix) user sends Telegram messages to the bot.
    #
    # Zabbix query:
    #   {
    #       "jsonrpc": "2.0",
    #       "method": "user.get",
    #       "params": {
    #           "output": ["userid", "username", "name", "surname"],
    #           "mediatypeids": 16,
    #           "selectMedias": ["mediatypeid","sendto"]
    #       },
    #       "id": 1
    #   }
    logging.info('Fetching Zabbix users with Telegram configured')
    zabbix_users_with_telegram = zapi.user.get(
            output = ['userid', 'username', 'name', 'surname'],
            mediatypeids = config['zabbix-telegram-mediatype'],
            selectMedias = ['mediatypeid', 'sendto'],
            selectRole = ['type'],
    )
    logging.debug('Got this list of users: %s', zabbix_users_with_telegram)

    telegram_users = {}
    for zabbix_user in zabbix_users_with_telegram:
        user = {
            'zabbix_userid': zabbix_user['userid'],
            'zabbix_username': zabbix_user['username'],
            'first_name': zabbix_user['name'],
            'surname': zabbix_user['surname'],
            'is_superadmin': zabbix_user['role']['type'] == '3'
        }

        # Filter all medias for user, so we only keep the entry with the Telegram
        # mediatype.
        telegram_media = list(filter(lambda media: media['mediatypeid'] == config['zabbix-telegram-mediatype'], zabbix_user['medias']))[0]

        telegram_users[telegram_media['sendto']] = user

    logging.debug('Telegram users I know about now: %s', telegram_users)


    bot_handler = telegram.commands.CommandHandler(telegram_token, zapi, telegram_users)


    # Start the bot
    #bot.infinity_polling()
    bot_handler.start_polling()



if __name__ == '__main__':
    main()

