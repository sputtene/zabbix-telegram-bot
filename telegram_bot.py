#!/usr/bin/env python3

import sys, configparser, telebot

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
