import logging
import sys
import requests
import re
import time

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

def get_graph(graph_id, from_ts, to_ts, width, height):
    if this.session_token is None:
        do_login()

    url = this.zabbix_server + '/chart2.php'
    params = {
            'graphid': graph_id,
            'from': from_ts,
            'to': to_ts,
            'width': width,
            'height': height,
            'profileIdx': 'web.charts.filter',
    }
    cookies = { 'zbx_session': this.session_token }

    r = requests.get(url, params=params, cookies=cookies)

    logging.debug('Retrieved graph, headers are: %s', r.headers)

    return r.content


def interval_between(from_ts, to_ts):
    """
    Calculate the interval between from_ts and to_ts (i.e. calculate
    to_ts - from_ts) in seconds.

    Both from_ts and to_ts are in "Zabbix time notation": see
    https://www.zabbix.com/documentation/current/en/manual/config/visualization/graphs/simple#time-period-selector

    This means they can be relative time syntax like "now-5h" or absolute time
    syntax in format Y-m-d H:i:s.
    """
    interval = 0
    if from_ts.startswith('now') and to_ts.startswith('now'):
        from_offset = _zabbix_time_offset_to_seconds(from_ts[3:])
        to_offset   = _zabbix_time_offset_to_seconds(to_ts[3:])
        interval = to_offset - from_offset
    elif from_ts.startswith('now'):
        now = now_to_epoch()
        from_epoch = now + _zabbix_time_offset_to_seconds(from_ts[3:])
        to_epoch = absolute_time_to_epoch(to_ts)
        interval = to_epoch - from_epoch
    elif to_ts.startswith('now'):
        now = now_to_epoch()
        from_epoch = absolute_time_to_epoch(from_ts)
        to_epoch = now + _zabbix_time_offset_to_seconds(to_ts[3:])
        interval = to_epoch - from_epoch
    else:
        from_epoch = absolute_time_to_epoch(from_ts)
        to_epoch = absolute_time_to_epoch(to_ts)
        interval = to_epoch - from_epoch

    return interval


def add_interval_to_ts(ts, interval):
    # Interval can be in seconds or a Zabbix interval specification (e.g. '+3m').
    #
    # Two cases: ts can be in absolute time and relative time specification.
    # The return value of this function will be of the same form.
    interval_seconds = _zabbix_time_offset_to_seconds(interval)

    if ts.startswith('now'):
        # Relative time specification
        ts_offset = _zabbix_time_offset_to_seconds(ts[3:])
        new_offset = ts_offset + interval_seconds
        return 'now' + _seconds_to_zabbix_time_offset(new_offset)
    else:
        # Absolute time
        ts_epoch = absolute_time_to_epoch(ts)
        new_ts = ts_epoch + interval_seconds
        return epoch_to_absolute_time(new_ts)


def absolute_time_to_epoch(abs_time):
    return int(time.mktime(time.strptime(abs_time, '%Y-%m-%d %H:%M:%S')))

def zabbix_time_to_epoch(zabbix_time):
    if not zabbix_time.startswith('now'):
        raise ValueError('%s is now a Zabbix time specification' % zabbix_time)

    return now_to_epoch() + _zabbix_time_offset_to_seconds(zabbix_time[3:])


def now_to_epoch():
    return int(time.time())


def now_to_absolute_time():
    return epoch_to_absolute_time(now_to_epoch())

def epoch_to_absolute_time(epoch):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(epoch)))


def _zabbix_time_offset_to_seconds(time_offset):
    """
    Convert Zabbix time offsets like 2h or 5d to seconds.
    """
    # This can happen when the original time specification was just "now".
    # Easier to return 0 early than to adapt the regex and logic below to
    # handle an empty string.
    if time_offset == '': return 0


    m = re.match(r'^([-+]?\d+)([smhdwMy]?)$', str(time_offset))

    if m is None:
        raise ValueError('Time offset [%s] has invalid syntax' % time_offset)

    amount = m.group(1)
    unit = m.group(2)

    multiplier = 1      # No unit means seconds
    if   unit == 's': multiplier = 1
    elif unit == 'm': multiplier = 60
    elif unit == 'h': multiplier = 60 * 60
    elif unit == 'd': multiplier = 60 * 60 * 24
    elif unit == 'w': multiplier = 60 * 60 * 24 * 7
    elif unit == 'M': multiplier = 60 * 60 * 24 * 30
    elif unit == 'y': multiplier = 60 * 60 * 24 * 365

    return int(amount) * multiplier


def _seconds_to_zabbix_time_offset(seconds):
    if seconds == 0: return ''

    amount, unit = seconds, 's'

    if amount % 60 == 0: amount, unit = int(amount / 60), 'm'
    if amount % 60 == 0: amount, unit = int(amount / 60), 'h'
    if amount % 24 == 0: amount, unit = int(amount / 24), 'd'

    # Try from largest to smallest unit now, otherwise 210 days would be
    # simplified as 30 weeks instead of 7 months.
    # Also only simplify if the unit is still days (so no prior simplification
    # has already happened), otherwise 2555 days would simplify to 7 years,
    # which would in its turn be changed to 1 week.
    if amount % 365 == 0                : amount, unit = int(amount / 365), 'y'
    if amount %  30 == 0 and unit == 'd': amount, unit = int(amount /  30), 'M'
    if amount %   7 == 0 and unit == 'd': amount, unit = int(amount /   7), 'w'

    if amount > 0: amount = '+' + str(amount)   # Make sure + or - prefix is there

    return str(amount) + unit
