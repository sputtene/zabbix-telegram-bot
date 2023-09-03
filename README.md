# zabbix-telegram-bot
This project is a work in progress.

## Quick start

### Clone this git repository

```
git clone https://github.com/sputtene/zabbix-telegram-bot.git
```


### Create a virtual environment (venv) and install dependencies

Create a virtual environment:
```
cd zabbix-telegram-bot
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```
pip install -r requirements.txt
```


### Configure your Telegram bot API token

**@BotFather** on Telegram will have given the API token for your bot when you
created it.

If you don't find it, you can ask BotFather to tell you again.

Put the token in the configuration file:
```
cp settings.ini-example settings.ini
$EDITOR settings.ini
```

Edit the `settings.ini` file so it looks like this:
```
[TelegramSettings]
API-Token: 1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZa_bcdefgh
```


### Execute the bot script

You are now ready to execute the bot:
```
./telegram_bot.py
```


## Systemd
It is also possible to run the zabbix telegram bot as a systemd service.
An example service file can be found in the `systemd` directory
