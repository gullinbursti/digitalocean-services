#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import hashlib
import json
import logging
import os
import random
import re
import sqlite3
import sys
import time

from StringIO import StringIO

import MySQLdb as mdb
import pycurl
import requests

from flask import Flask, request
from urllib2 import quote

from constants import Const

reload(sys)
sys.setdefaultencoding('utf8')


app = Flask(__name__)

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler('/var/log/FacebookBot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


def send_tracker(category, action, label):
    logger.info("send_tracker(category=%s, action=%s, label=%s)" % (category, action, label))

    c = pycurl.Curl()
    c.setopt(c.URL, "http://beta.modd.live/api/bot_tracker.php?src=facebook&category={category}&action={category}&label={label}&value=&cid={cid}".format(category=category, action=category, label=action, cid=hashlib.md5(action.encode()).hexdigest()))
    c.setopt(c.WRITEDATA, StringIO())
    c.perform()
    c.close()

    c = pycurl.Curl()
    c.setopt(c.URL, "http://beta.modd.live/api/bot_tracker.php?src=facebook&category=user-message&action=user-message&label={label}&value=&cid={cid}".format(label=action, cid=hashlib.md5(action.encode()).hexdigest()))
    c.setopt(c.WRITEDATA, StringIO())
    c.perform()
    c.close()

    return True


def write_message_log(sender_id, message_id, message_txt):
    logger.info("write_message_log(sender_id=%s, message_id=%s, message_txt=%s)" % (sender_id, message_id, json.dumps(message_txt)))

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('INSERT INTO `fbbot_logs` (`id`, `message_id`, `chat_id`, `body`) VALUES (NULL, %s, %s, %s)', (message_id, sender_id, json.dumps(message_txt)))

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


def main_menu_quick_replies():
    logger.info("main_menu_quick_replies()")
    return [
        {
            'content_type' : "text",
            'title'        : "Main Menu",
            'payload'      : "MAIN_MENU"
        }, {
            'content_type' : "text",
            'title'        : "Invite Friends Now",
            'payload'      : "INVITE"
        }, {
            'content_type' : "text",
            'title'        : "Support",
            'payload'      : "SUPPORT"
        }
    ]


def coin_flip_quick_replies():
    logger.info("coin_flip_quick_replies()")
    return [
        {
            'content_type' : "text",
            'title'        : "Next Item",
            'payload'      : "NEXT_ITEM"
        }, {
            'content_type' : "text",
            'title'        : "No Thanks",
            'payload'      : "NO_THANKS"
        }
    ]


def opt_out_quick_replies():
    logger.info("opt_out_quick_replies()")
    return [
        {
            'content_type' : "text",
            'title'        : "Opt-In",
            'payload'      : "OPT_IN"
        }, {
            'content_type' : "text",
            'title'        : "Cancel",
            'payload'      : "CANCEL"
        }
    ]


def default_carousel(sender_id):
    logger.info("default_carousel(sender_id=%s)" % (sender_id))

    elements = [
        coin_flip_element(sender_id)
    ]

    params = {
        'fields'       : "is_payment_enabled",
        'access_token' : Const.ACCESS_TOKEN
    }
    response = requests.get("https://graph.facebook.com/v2.6/{sender_id}".format(sender_id=sender_id), params=params)
    if 'is_payment_enabled' in response.json() and response.json()['is_payment_enabled']:
        elements.append(daily_item_element(sender_id))

    if None in elements:
        send_text(sender_id, "No items are available right now, try again later")
        return

    send_carousel(
        recipient_id=sender_id,
        elements=elements,
        quick_replies=main_menu_quick_replies()
    )


def daily_item_element(sender_id, standalone=False):
    logger.info("daily_item_element(sender_id=%s, standalone=%s)" % (sender_id, standalone))

    element = None
    set_session_item(sender_id)

    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `game_name`, `image_url`, `max_buy`, `min_sell` FROM `flip_inventory` WHERE `type` = 2 ORDER BY RAND() LIMIT 1;')
            row = cur.fetchone()

            if row is not None:
                element = {
                    'title'     : "{item_name}".format(item_name=row['name'].encode('utf8')),
                    'subtitle'  : "",
                    'image_url' : row['image_url'],
                    'item_url'  : None,
                    'buttons'   : [{
                        'type'            : "payment",
                        'title'           : "Buy Now",
                        'payload'         : "%s-%d" % ("PURCHASE_ITEM", row['id']),
                        'payment_summary' : {
                            'currency'            : "USD",
                            'payment_type'        : "FIXED_AMOUNT",
                            'is_test_payment'     : False,
                            'merchant_name'       : "Gamebots",
                            'requested_user_info' : [
                                "contact_email"
                            ],
                            'price_list' : [{
                                'label'  : "Subtotal",
                                'amount' : row['min_sell']
                            }]
                        }
                    }]
                }

                if standalone is True:
                    element['buttons'].append({
                        'type'    : "postback",
                        'payload' : "NO_THANKS",
                        'title'   : "No Thanks"
                    })

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return element

def coin_flip_element(sender_id, standalone=False):
    logger.info("coin_flip_element(sender_id=%s, standalone=%s)" % (sender_id, standalone))

    set_session_item(sender_id)

    element = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `game_name`, `image_url` FROM `flip_inventory` WHERE `quantity` > 0 AND `type` = 1 AND `enabled` = 1 ORDER BY RAND() LIMIT 1;')
            row = cur.fetchone()

            if row is not None:
                set_session_item(sender_id, row['id'])

                element = {
                    'title'     : "{item_name}".format(item_name=row['name'].encode('utf8')),
                    'subtitle'  : "",
                    'image_url' : row['image_url'],
                    'item_url'  : None,
                    'buttons'   : [{
                        'type'    : "postback",
                        'payload' : "FLIP_COIN",
                        'title'   : "Flip Coin"
                    }]
                }

                if standalone is True:
                    element['buttons'].append({
                        'type'    : "postback",
                        'payload' : "NO_THANKS",
                        'title'   : "No Thanks"
                    })

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return element


def coin_flip_results(sender_id, item_id=None):
    logger.info("coin_flip_results(sender_id=%s, item_id=%s)" % (sender_id, item_id))

    send_image(sender_id, Const.FLIP_COIN_START_GIF_URL)

    if item_id is None:
        send_text(sender_id, "Can't find your item! Try flipping for it again")
        return "OK", 200

    total_wins = 1
    flip_item = None
    win_boost = 1

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `kik_name` FROM `item_winners` WHERE `fb_id` = %s LIMIT 1;', (sender_id,))
            if cur.fetchone() is not None:
                win_boost = 0.5

            cur.execute('SELECT COUNT(*) AS `tot` FROM `item_winners` WHERE `fb_id` = %s AND `added` > DATE_SUB(NOW(), INTERVAL 6 HOUR);', (sender_id,))
            row = cur.fetchone()
            if row is not None:
                total_wins = row['tot']

            cur.execute('SELECT `id`, `name`, `game_name`, `image_url`, `trade_url` FROM `flip_inventory` WHERE `id` = %s LIMIT 1;', (item_id,))
            row = cur.fetchone()

            if row is not None:
                flip_item = {
                    'item_id'   : row['id'],
                    'name'      : row['name'].encode('utf8'),
                    'game_name' : row['game_name'],
                    'image_url' : row['image_url'],
                    'claim_id'  : None,
                    'claim_url' : None,
                    'trade_url' : row['trade_url'],
                    'win_boost' : win_boost,
                    'pin_code'  : hashlib.md5(str(time.time()).encode()).hexdigest()[-4:].upper()
                }

            else:
                send_text(sender_id, "Looks like that item isn't available anymore, try another one")
                send_carousel(recipient_id=sender_id, elements=[coin_flip_element(sender_id, True)])
                return "OK", 0

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


    if sender_id == Const.ADMIN_FB_PSID or random.uniform(0, flip_item['win_boost']) <= ((1 / float(4)) * (abs(1 - (total_wins * 0.01)))) or sender_id == "1219553058088713":
        total_wins += 1
        payload = {
            'channel'     : "#bot-alerts",
            'username'    : "gamebotsc",
            'icon_url'    : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text'        : "Flip Win by *{user}* ({sender_id}):\n_{item_name}_\n{pin_code}".format(user=sender_id if get_session_name(sender_id) is None else get_session_name(sender_id), sender_id=sender_id, item_name=flip_item['name'], pin_code=flip_item['pin_code']),
            'attachments' : [{
                'image_url' : flip_item['image_url']
            }]
        }
        response = requests.post("https://hooks.slack.com/services/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",data={'payload': json.dumps(payload)})

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                if sender_id != Const.ADMIN_FB_PSID:
                    cur.execute('UPDATE `flip_inventory` SET `quantity` = `quantity` - 1 WHERE `id` = %s AND quantity > 0 LIMIT 1;', (flip_item['item_id'],))
                cur.execute('INSERT INTO `item_winners` (`fb_id`, `pin`, `item_id`, `item_name`, `added`) VALUES (%s, %s, %s, %s, NOW());', (sender_id, flip_item['pin_code'], flip_item['item_id'], flip_item['name']))
                conn.commit()
                cur.execute('SELECT @@IDENTITY AS `id` FROM `item_winners`;')
                flip_item['claim_id'] = cur.fetchone()['id']

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                cur.close()

        send_image(sender_id, Const.FLIP_COIN_WIN_GIF_URL)
        send_card(
            recipient_id = sender_id,
            title = "{item_name}".format(item_name=flip_item['name']),
            image_url = flip_item['image_url'],
            card_url = Const.FLIP_CLAIM_URL,
            buttons = [
                {
                    'type'                 : "element_share"
                }, {
                    'type'                 : "web_url",
                    'url'                  : Const.FLIP_CLAIM_URL,
                    'title'                : "Trade",
                    'webview_height_ratio' : "compact"
                }
            ]
        )

        send_text(sender_id, Const.FLIP_WIN_TEXT.format(item_name=flip_item['name'], game_name=flip_item['game_name'], claim_url=Const.FLIP_CLAIM_URL, sender_id=sender_id))
        set_session_trade_url(sender_id, "_{PENDING}_")

    else:
        send_image(sender_id, Const.FLIP_COIN_LOSE_GIF_URL)
        send_text(
            recipient_id=sender_id,
            message_text="TRY AGAIN! You lost {item_name} from {game_name}.".format(item_name=flip_item['name'], game_name=flip_item['game_name']),
            quick_replies=coin_flip_quick_replies()
        )


def opt_out(sender_id):
    logger.info("opt_out(sender_id=%s)" % (sender_id))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        cur = conn.cursor()
        cur.execute('SELECT id FROM blacklisted_users WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is None:
            cur.execute('INSERT INTO blacklisted_users (id, fb_psid, added) VALUES (NULL, ?, ?);', (sender_id, int(time.time())))
            conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::opt_out[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('UPDATE `fbbot_logs` SET `enabled` = 0 WHERE `chat_id` = %s;', (sender_id,))
            conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    send_text(sender_id, "You will no longer recieve messages from Gamebots. If you need help visit facebook.com/gamebotsc", opt_out_quick_replies())


def get_session_state(sender_id):
    logger.info("get_session_state(sender_id=%s)" % (sender_id))
    state = 0

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT state FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            state = row['state']

        logger.info("state=%s" % (state))

    except sqlite3.Error as er:
        logger.info("::::::get_session_state[sqlite3.connect] sqlite3.Error - %s" % (er.message))

    finally:
        if conn:
            conn.close()

    return state

def set_session_state(sender_id, state=1):
    logger.info("set_session_state(sender_id=%s, state=%s)" % (sender_id, state))

    current_state = get_session_state(sender_id)
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        cur = conn.cursor()
        if current_state == 0:
            cur.execute('INSERT INTO sessions (id, fb_psid, state, added) VALUES (NULL, ?, ?, ?);', (sender_id, state, int(time.time())))

        else:
            cur.execute('UPDATE sessions SET state = ? WHERE fb_psid = ?;', (state, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_state[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_name(sender_id):
    logger.info("get_session_name(sender_id=%s)" % (sender_id))
    full_name = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT f_name, l_name FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            full_name = "%s %s" % (row['f_name'] or "", row['l_name'] or "")
            if len(full_name) == 1:
                full_name = None

        logger.info("full_name=%s" % (full_name))

    except sqlite3.Error as er:
        logger.info("::::::get_session_name[sqlite3.connect] sqlite3.Error - %s" % (er.message))

    finally:
        if conn:
            conn.close()

    return full_name


def set_session_name(sender_id, first_name=None, last_name=None):
    logger.info("set_session_name(sender_id=%s, first_name=%s, last_name=%s)" % (sender_id, first_name, last_name))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET f_name = ?, l_name = ? WHERE fb_psid = ?;', (first_name, last_name, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_name[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_item(sender_id):
    logger.info("get_session_item(sender_id=%s)" % (sender_id))
    item_id = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT flip_id FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            item_id = row['flip_id']

        logger.info("item_id=%s" % (item_id))

    except sqlite3.Error as er:
        logger.info("::::::get_session_item[sqlite3.connect] sqlite3.Error - %s" % (er.message))

    finally:
        if conn:
            conn.close()

    return item_id

def set_session_item(sender_id, item_id=0):
    logger.info("set_session_item(sender_id=%s, item_id=%s)" % (sender_id, item_id))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET flip_id = ? WHERE fb_psid = ?;', (item_id, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_item[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_trade_url(sender_id):
    logger.info("get_session_trade_url(sender_id=%s)" % (sender_id))
    trade_url = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT trade_url FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            trade_url = row['trade_url']

        logger.info("trade_url=%s" % (trade_url))

    except sqlite3.Error as er:
        logger.info("::::::get_session_trade_url[sqlite3.connect] sqlite3.Error - %s" % (er.message))

    finally:
        if conn:
            conn.close()

    return trade_url


def set_session_trade_url(sender_id, trade_url=None):
    logger.info("set_session_trade_url(sender_id=%s, trade_url=%s)" % (sender_id, trade_url))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET trade_url = ? WHERE fb_psid = ?;', (trade_url, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_trade_url[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_purchase(sender_id):
    logger.info("get_session_purchase(sender_id=%s)" % (sender_id))
    purchase_id = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT purchase_id FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            purchase_id = row['purchase_id']

        logger.info("purchase_id=%s" % (purchase_id))

    except sqlite3.Error as er:
        logger.info("::::::get_session_item[sqlite3.connect] sqlite3.Error - %s" % (er.message))

    finally:
        if conn:
            conn.close()

    return purchase_id

def set_session_purchase(sender_id, purchase_id=0):
    logger.info("set_session_purchase(sender_id=%s, purchase_id=%s)" % (sender_id, purchase_id))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET purchase_id = ? WHERE fb_psid = ?;', (purchase_id, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_item[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def purchase_item(sender_id, payment):
    logger.info("purchase_item(sender_id=%s, payment=%s)" % (sender_id, payment))

    purchase_id = 0
    item_id = re.match(r'^PURCHASE_ITEM\-(?P<item_id>\d+)$', payment['payload']).group('item_id')
    item_name = None
    customer_email = payment['requested_user_info']['contact_email']
    amount = payment['amount']['amount']
    fb_payment_id = payment['payment_credential']['fb_payment_id']
    provider = payment['payment_credential']['provider_type']
    charge_id = payment['payment_credential']['charge_id']

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `game_name`, `image_url` FROM `flip_inventory` WHERE `id` = %s LIMIT 1;', (item_id,))
            row = cur.fetchone()

            if row is not None:
                item_name = row['name']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('INSERT INTO `fb_purchases` (`id`, `fb_psid`, `email`, `item_id`, `amount`, `fb_payment_id`, `provider`, `charge_id`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s));', (sender_id, customer_email, item_id, amount, fb_payment_id, provider, charge_id, int(time.time())))
            conn.commit()
            cur.execute('SELECT @@IDENTITY AS `id` FROM `fb_purchases`;')
            row = cur.fetchone()
            purchase_id = row['id']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    if purchase_id != 0:
        set_session_purchase(sender_id, purchase_id)

        try:
            conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            cur = conn.cursor()
            cur.execute('INSERT INTO payments (id, fb_psid, email, item_id, amount, fb_payment_id, provider, charge_id, added) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);', (purchase_id, sender_id, customer_email, item_id, amount, fb_payment_id, provider, charge_id, int(time.time())))
            conn.commit()

        except sqlite3.Error as er:
            logger.info("::::::payment[cur.execute] sqlite3.Error - %s" % (er.message,))

        finally:
            if conn:
                conn.close()

    set_session_state(sender_id, 2)
    send_text(sender_id, "You have successfully purchased {item_name}, please enter your steam trade url to recieve it".format(item_name=item_name))

    payload = {
        'channel' : "#gamebots-purchases",
        'username': "gamebotsc",
        'icon_url': "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
        'text'    : "*{customer_email}* ({fb_psid}) just purchased _{item_name}_ for ${item_price:%.2f}".format(customer_email=customer_email, fb_psid=sender_id, item_name=item_name, item_price=amount),
    }
    response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})


@app.route('/', methods=['GET'])
def verify():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= VERIFY (%s)->%s\n" % (request.args.get('hub.mode'), request))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == Const.VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args['hub.challenge'], 200

    return "OK", 200


@app.route('/', methods=['POST'])
def webook():

    # return "OK", 200

    data = request.get_json()

    logger.info("[=-=-=-=-=-=-=-[POST DATA]-=-=-=-=-=-=-=-=]")
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    logger.info(data)

    if data['object'] == "page":
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                if 'delivery' in messaging_event:  # delivery confirmation
                    logger.info("-=- DELIVERY CONFIRM -=-")
                    return "OK", 200

                if 'read' in messaging_event:  # read confirmation
                    logger.info("-=- READ CONFIRM -=- %s" % (messaging_event))
                    send_tracker("read-receipt", messaging_event['sender']['id'], "")
                    return "OK", 200

                if 'optin' in messaging_event:  # optin confirmation
                    logger.info("-=- OPT-IN -=-")
                    return "OK", 200


                sender_id = messaging_event['sender']['id']


                if 'payment' in messaging_event: # payment result
                    logger.info("-=- PAYMENT -=-")
                    purchase_item(sender_id, messaging_event['payment'])
                    return "OK", 200



                try:
                    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
                    cur = conn.cursor()
                    cur.execute('SELECT id FROM blacklisted_users WHERE `fb_psid` = ?;', (sender_id,))
                    row = cur.fetchone()
                    if row is not None:
                        if 'message' in messaging_event and 'quick_reply' in messaging_event['message'] and messaging_event['message']['quick_reply']['payload'] == "OPT_IN":
                            cur.execute('DELETE FROM blacklisted_users WHERE `fb_psid` = ?;', (sender_id,))
                            conn.commit()
                            conn.close()

                            conn2 = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
                            try:
                                with conn2:
                                    cur2 = conn.cursor(mdb.cursors.DictCursor)
                                    cur2.execute('UPDATE `fbbot_logs` SET `enabled` = 1 WHERE `chat_id` = %s;', (sender_id,))
                                    conn2.commit()

                            except mdb.Error, e:
                                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

                            finally:
                                if conn2:
                                    cur2.close()

                        else:
                            send_text(sender_id, "You have opted out of Gamebots.", opt_out_quick_replies())
                            return "OK", 200

                except sqlite3.Error as er:
                    logger.info("::::::optin[cur.execute] sqlite3.Error - %s" % (er.message,))

                finally:
                    if conn:
                        cur.close()


                #-- new entry
                if get_session_state(sender_id) == 0:
                    logger.info("----------=NEW SESSION @(%s)=----------" % (time.strftime("%Y-%m-%d %H:%M:%S")))
                    send_tracker("signup-fb", sender_id, "")

                    set_session_state(sender_id)
                    send_text(sender_id, "Welcome to Gamebots. WIN pre-sale games & items with players on Messenger.\n To opt-out of further messaging, type exit, quit, or stop.")
                    send_image(sender_id, "http://i.imgur.com/QHHovfa.gif")
                    default_carousel(sender_id)

                #-- existing reply
                elif get_session_state(sender_id) == 1:
                    if get_session_name(sender_id) is None:
                        graph = fb_graph_user(sender_id)
                        set_session_name(sender_id, graph['first_name'] or "", graph['last_name'] or "")


                    # ------- POSTBACK BUTTON MESSAGE
                    if 'postback' in messaging_event:  # user clicked/tapped "postback" button in earlier message
                        logger.info("-=- POSTBACK RESPONSE -=- (%s)" % (messaging_event['postback']['payload']))

                        if messaging_event['postback']['payload'] == "WELCOME_MESSAGE":
                            logger.info("----------=NEW SESSION @(%s)=----------" % (time.strftime("%Y-%m-%d %H:%M:%S")))
                            send_tracker("signup-fb", sender_id, "")
                            default_carousel(sender_id)
                            return "OK", 200

                        if re.search('FLIP_COIN-(\d+)', messaging_event['postback']['payload']) is not None:
                            send_tracker("flip-item", sender_id, "")
                            coin_flip_results(sender_id, re.match(r'FLIP_COIN-(?P<item_id>\d+)', messaging_event['postback']['payload']).group('item_id'))

                        elif messaging_event['postback']['payload'] == "FLIP_COIN" and get_session_item(sender_id) is not None:
                            send_tracker("flip-item", sender_id, "")
                            coin_flip_results(sender_id, get_session_item(sender_id))
                            return "OK", 200

                        if messaging_event['postback']['payload'] == "NO_THANKS":
                            send_tracker("no-thanks", sender_id, "")

                        elif messaging_event['postback']['payload'] == "MAIN_MENU":
                            send_tracker("main-menu", sender_id, "")

                        default_carousel(sender_id)
                        return "OK", 200


                    # -- actual message
                    if 'message' in messaging_event:
                        logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECIEVED ->%s" % (messaging_event['sender']))

                        message = messaging_event['message']

                        # MESSAGE CREDENTIALS
                        message_id = message['mid']

                        # -- insert to log
                        write_message_log(sender_id, message_id, message)

                        # ------- IMAGE MESSAGE
                        if 'attachments' in message:
                            for attachment in message['attachments']:
                                if 'url' in attachment and get_session_trade_url(sender_id) == "_{PENDING}_":
                                    set_session_trade_url(sender_id, message['text'])

                                    try:
                                        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
                                        with conn:
                                            cur = conn.cursor(mdb.cursors.DictCursor)
                                            cur.execute('UPDATE `item_winners` SET `trade_url` = %s WHERE `fb_id` = %s ORDER BY `added` DESC LIMIT 1;', (message['text'], sender_id))
                                            conn.commit()

                                    except mdb.Error, e:
                                        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

                                    finally:
                                        if conn:
                                            conn.close()

                                    payload = {
                                        'channel'    : "#bot-alerts",
                                        'username'   : "gamebotsc",
                                        'icon_url'   : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
                                        'text'       : "Trade URL set for *{user}*:\n_{trade_url}".format(user=sender_id if get_session_name(sender_id) is None else get_session_name(sender_id), trade_url=message['text'])
                                    }
                                    response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

                                    send_text(sender_id, "Trade URL set")
                                    default_carousel(sender_id)

                                else:
                                    send_text(sender_id, "I'm sorry, I cannot understand that type of message.", main_menu_quick_replies())
                                    return "OK", 200


                        # ------- QUICK REPLY BUTTON
                        if 'quick_reply' in message and message['quick_reply']['payload'] is not None:
                            logger.info("QR --> %s" % (messaging_event['message']['quick_reply']['payload']))
                            quick_reply = messaging_event['message']['quick_reply']['payload']

                            send_tracker("{show}-button".format(show=quick_reply.split("_")[-1].lower()),  messaging_event['sender']['id'], "")

                            if quick_reply == "INVITE":
                                send_card(
                                    recipient_id=sender_id,
                                    title="Share",
                                    image_url=Const.FLIP_COIN_START_GIF_URL,
                                    card_url="http://m.me/gamebotsc",
                                    buttons=[{'type': "element_share"}],
                                    quick_replies=[{
                                        'content_type' : "text",
                                        'title'        : "Main Menu",
                                        'payload'      : "MAIN_MENU"
                                    }]
                                )

                            elif quick_reply == "SUPPORT":
                                send_text(sender_id, "If you need help visit facebook.com/gamebotsc")
                                default_carousel(sender_id)

                                payload = {
                                    'channel'  : "#pre",
                                    'username' : "gamebotsc",
                                    'icon_url' : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
                                    'text'     : "*{user}* needs help…".format(user=sender_id if get_session_name(sender_id) is None else get_session_name(sender_id)),
                                }
                                response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

                            elif quick_reply == "NEXT_ITEM":
                                send_tracker("next-item", sender_id, "")
                                default_carousel(sender_id)

                                # send_carousel(recipient_id=sender_id, elements=[coin_flip_element(sender_id, True)])

                            elif quick_reply == "NO_THANKS":
                                send_tracker("no-thanks", sender_id, "")
                                default_carousel(sender_id)

                            elif quick_reply == "MAIN_MENU":
                                send_tracker("todays-item", sender_id, "")

                                if get_session_trade_url(sender_id) == "_{PENDING}_":
                                    set_session_trade_url(sender_id)

                                default_carousel(sender_id)

                            else:
                                default_carousel(sender_id)


                        else:
                            # ------- TYPED TEXT MESSAGE
                            if 'text' in message:
                                message_text = message['text']

                                if get_session_trade_url(sender_id) == "_{PENDING}_":
                                    send_text(
                                        recipient_id = sender_id,
                                        message_text = "Invalid URL, try again...",
                                        quick_replies = [{
                                            'content_type' : "text",
                                            'title'        : "Main Menu",
                                            'payload'      : "MAIN_MENU"
                                        }]
                                    )

                                else:
                                    # -- typed '!end' / 'cancel' / 'quit'
                                    if message_text.lower() in Const.OPT_OUT_REPLIES:
                                        logger.info("-=- ENDING HELP -=- (%s)" % (time.strftime("%Y-%m-%d %H:%M:%S")))
                                        opt_out(sender_id)

                                    else:
                                        send_text(sender_id, "Welcome to Gamebots. WIN pre-sale games & items with players on Messenger.")
                                        default_carousel(sender_id)

                            else:
                                default_carousel(sender_id)


                #-- purchasing
                elif get_session_state(sender_id) == 2:
                    if 'message' in messaging_event and 'text' in messaging_event['message']:
                        message_text = messaging_event['message']['text']
                        purchase_id = get_session_purchase(sender_id)

                        try:
                            conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
                            cur = conn.cursor()
                            cur.execute('UPDATE payments SET `trade_url` = ? WHERE `id` = ? LIMIT 1;', (message_text, purchase_id))
                            conn.commit()

                        except sqlite3.Error as er:
                            logger.info("::::::payment[cur.execute] sqlite3.Error - %s" % (er.message,))

                        finally:
                            if conn:
                                conn.close()

                        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
                        try:
                            with conn:
                                cur = conn.cursor(mdb.cursors.DictCursor)
                                cur.execute('UPDATE `fb_purchases` SET `trade_url` = %s WHERE `id` = %s LIMIT 1;', (message_text, purchase_id))
                                conn.commit()

                        except mdb.Error, e:
                            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

                        finally:
                            if conn:
                                conn.close()

                        set_session_purchase(sender_id)
                        set_session_state(sender_id)
                        default_carousel(sender_id)

                else:
                    default_carousel(sender_id)

    return "OK", 200


def send_typing_indicator(recipient_id, is_typing):
    data = {
        'recipient'    : {
            'id': recipient_id
        },
        'sender_action': "typing_on" if is_typing else "typing_off"
    }

    send_message(json.dumps(data))


def send_text(recipient_id, message_text, quick_replies=None):
    logger.info("send_text(recipient_id=%s, message_text=%s, quick_replies=%s)" % (recipient_id, message_text, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message'   : {
            'text' : message_text
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_card(recipient_id, title, image_url, card_url, subtitle="", buttons=None, quick_replies=None):
    logger.info("send_card(recipient_id=%s, title=%s, image_url=%s, card_url=%s, subtitle=%s, buttons=%s, quick_replies=%s)" % (recipient_id, title, image_url, card_url, subtitle, buttons, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message'   : {
            'attachment' : {
                'type'    : "template",
                'payload' : {
                    'template_type' : "generic",
                    'elements'      : [{
                        'title'     : title,
                        'item_url'  : card_url,
                        'image_url' : image_url,
                        'subtitle'  : subtitle,
                        'buttons'   : buttons
                    }]
                }
            }
        }
    }

    if buttons is not None:
        data['message']['attachment']['payload']['elements'][0]['buttons'] = buttons

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_carousel(recipient_id, elements, quick_replies=None):
    logger.info("send_carousel(recipient_id=%s, elements=%s, quick_replies=%s)" % (recipient_id, elements, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message'   : {
            'attachment'  : {
                'type'    : "template",
                'payload' : {
                    'template_type' : "generic",
                    'elements'      : elements
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_image(recipient_id, url, quick_replies=None):
    logger.info("send_image(recipient_id=%s, url=%s, quick_replies=%s)" % (recipient_id, url, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message'   : {
            'attachment' : {
                'type'    : "image",
                'payload' : {
                    'url' : url
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_video(recipient_id, url, quick_replies=None):
    logger.info("send_image(recipient_id=%s, url=%s, quick_replies=%s)" % (recipient_id, url, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message'   : {
            'attachment' : {
                'type'    : "video",
                'payload' : {
                    'url' : url
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_message(payload):
    logger.info("send_message(payload=%s)" % (payload))

    response = requests.post(
        url="https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN),
        params={ 'access_token' : Const.ACCESS_TOKEN },
        json=json.loads(payload)
    )

    logger.info("GRAPH RESPONSE (%s): %s" % (response.status_code, response.text))
    return True


def fb_graph_user(recipient_id):
    logger.info("fb_graph_user(recipient_id=%s)" % (recipient_id))

    params = {
        'fields'      : "first_name,last_name,profile_pic,locale,timezone,gender,is_payment_enabled",
        'access_token': Const.ACCESS_TOKEN
    }
    response = requests.get("https://graph.facebook.com/v2.6/{recipient_id}".format(recipient_id=recipient_id), params=params)
    return None if 'error' in response.json() else response.json()

if __name__ == '__main__':
    app.run(debug=True)


# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#
