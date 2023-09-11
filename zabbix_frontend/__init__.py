import logging
import sys
import requests

this = sys.modules[__name__]
this.zabbix_server = None
this.zabbix_username = None
this.zabbix_password = None
this.session_token = None


def init(server, username, password):
    this.zabbix_server = server
    this.zabbix_username = username
    this.zabbix_password = password

    logging.debug("Initializing Zabbix frontend module with server: %s, username: %s", this.zabbix_server, this.zabbix_username)


def do_login():
    logging.debug("Logging in to Zabbix frontend")

    url = this.zabbix_server + '/index.php'

    post_fields = {
            'name': this.zabbix_username,
            'password': this.zabbix_password,
            'form_refresh': 1,
            'autologin': 0,
            'enter': 'Sign in',
    }

    r = requests.post(url, data=post_fields)

    this.session_token = r.cookies['zbx_session']

    pass

def get_graph(graph_id, period, width, height):
    if this.session_token is None:
        do_login()

    url = this.zabbix_server + '/chart2.php'
    params = {
            'graphid': graph_id,
            'period': period,
            'width': width,
            'height': height,
    }
    cookies = { 'zbx_session': this.session_token }

    r = requests.get(url, params=params, cookies=cookies)

    logging.debug('Retrieved graph, headers are: %s', r.headers)

    return r.content
