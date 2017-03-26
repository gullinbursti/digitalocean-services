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
from urllib import urlencode

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


def send_tracker(fb_psid, category, action=None, label=None, value=None):
    logger.info("send_tracker(fb_psid=%s, category=%s, action=%s, label=%s, value=%s)" % (fb_psid, category, action, label, value))

    action = action or category
    label = label or fb_psid
    value = value or "0"

    payload = {
        'v'   : 1,
        't'   : "event",
        'tid' : Const.GA_TRACKING_ID,
        'cid' : hashlib.md5(fb_psid.encode()).hexdigest(),
        'ec'  : category,
        'ea'  : action,
        'el'  : label,
        'ev'  : value
    }

    c = pycurl.Curl()
    c.setopt(c.URL, Const.GA_TRACKING_URL)
    c.setopt(c.POSTFIELDS, urlencode(payload))
    c.setopt(c.WRITEDATA, StringIO())
    c.perform()
    c.close()


    # c = pycurl.Curl()
    # c.setopt(c.URL, "http://beta.modd.live/api/bot_tracker.php?src=facebook&category={category}&action={category}&label={label}&value=&cid={cid}".format(category=category, action=category, label=action, cid=hashlib.md5(action.encode()).hexdigest()))
    # c.setopt(c.WRITEDATA, StringIO())
    # c.perform()
    # c.close()
    #
    # c = pycurl.Curl()
    # c.setopt(c.URL, "http://beta.modd.live/api/bot_tracker.php?src=facebook&category=user-message&action=user-message&label={label}&value=&cid={cid}".format(label=action, cid=hashlib.md5(action.encode()).hexdigest()))
    # c.setopt(c.WRITEDATA, StringIO())
    # c.perform()
    # c.close()

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


def main_menu_quick_reply():
    logger.info("home_quick_replies()")
    return [{
        'content_type': "text",
        'title'       : "Main Menu",
        'payload'     : "MAIN_MENU"
    }]


def home_quick_replies():
    logger.info("home_quick_replies()")
    return main_menu_quick_reply() + [
        {
            'content_type' : "text",
            'title'        : "Invite Friends Now",
            'payload'      : "INVITE"
        }, {
            'content_type' : "text",
            'title'        : "Support",
            'payload'      : "SUPPORT"
        }
    ]


def submit_quick_replies(captions=["Yes", "No"]):
    logger.info("submit_quick_replies()")
    return [{
        'content_type': "text",
        'title'       : captions[0],
        'payload'     : "SUBMIT_YES"
    }, {
        'content_type': "text",
        'title'       : captions[1],
        'payload'     : "SUBMIT_NO"
    }, {
        'content_type': "text",
        'title'       : "Cancel",
        'payload'     : "SUBMIT_CANCEL"
    }]


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


def default_carousel(sender_id, amount=1):
    logger.info("default_carousel(sender_id=%s amount=%s)" % (sender_id, amount))

    elements = []
    for i in range(amount):
        elements.append(coin_flip_element(sender_id))

    if None in elements:
        send_text(sender_id, "No items are available right now, try again later")
        return

    send_carousel(
        recipient_id=sender_id,
        elements=elements,
        quick_replies=home_quick_replies()
    )


def pay_wall_carousel(sender_id, amount=5):
    logger.info("default_carousel(sender_id=%s amount=%s)" % (sender_id, amount))

    elements = []
    for i in range(amount):
        elements.append(coin_flip_element(sender_id, True))

    if None in elements:
        send_text(sender_id, "No items are available right now, try again later")
        return

    send_carousel(
        recipient_id=sender_id,
        elements=elements,
        quick_replies=home_quick_replies()
    )


def send_paypal_card(sender_id, price, image_url=None):
    logger.info("send_paypal_card(sender_id=%s, price=%s)" % (sender_id, price))

    send_card(
        recipient_id=sender_id,
        title="GameBots Deposit",
        subtitle="${price:.2f}".format(price=price),
        image_url="https://scontent.xx.fbcdn.net/v/t31.0-8/16587327_1399560603439422_4787736195158722183_o.jpg?oh=86ba759ae6da27ba9b42c85fbc5b7a44&oe=5924F606" if image_url is None else image_url,
        card_url="https://paypal.me/gamebotsc/{price}".format(price=price),
        buttons=[{
            'type'                 : "web_url",
            #'url'                 : "http://gamebots.chat/{fb_psid}/{price}".format(fb_psid=sender_id, price=price),
            'url'                  : "http://paypal.me/gamebotsc/{price}".format(price=price),
            'title'                : "${price:.2f} Confirm".format(price=price),
            'webview_height_ratio' : "tall"
        }],
        quick_replies=main_menu_quick_reply()
    )



def flip_pay_wall(sender_id, price):
    logger.info("flip_pay_wall(sender_id=%s, price=%s)" % (sender_id, price))

    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `info`, `image_url`, `price` FROM `fb_products` WHERE `id` = 3 LIMIT 1;')
            row = cur.fetchone()

            if row is not None:
                send_card(
                    recipient_id=sender_id,
                    title=row['name'],
                    subtitle=row['info'],
                    image_url=row['image_url'],
                    buttons=[{
                        'type'           : "payment",
                        'title'          : "Buy Now",
                        'payload'        : "%s-%d" % ("PURCHASE_ITEM", row['id']),
                        'payment_summary': {
                            'currency'           : "USD",
                            'payment_type'       : "FIXED_AMOUNT",
                            'is_test_payment'    : False,
                            'merchant_name'      : "Gamebots",
                            'requested_user_info': [
                                "contact_email"
                            ],
                            'price_list'         : [{
                                'label' : "Subtotal",
                                'amount': price
                            }]
                        }
                    }],
                    quick_replies=main_menu_quick_reply()
                )

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


def coin_flip_element(sender_id, pay_wall=False):
    logger.info("coin_flip_element(sender_id=%s, standalone=%s)" % (sender_id, pay_wall))

    item_id = None
    set_session_item(sender_id)


    deposit = get_session_deposit(sender_id)

    element = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `type`, `name`, `game_name`, `image_url`, `max_buy`, `min_sell` FROM `flip_inventory` WHERE `quantity` > 0 AND (`type` = 1 OR `type` = 2) AND `min_sell` > %s AND `enabled` = 1 ORDER BY RAND() LIMIT 1;', ((0.5) * deposit if pay_wall is False else (deposit + 1) * 2,))
            row = cur.fetchone()

            if row is not None:
                item_id = row['id']
                set_session_item(sender_id, item_id)

                element = {
                    'title'     : "{item_name}".format(item_name=row['name'].encode('utf8')),
                    'subtitle'  : "",# if pay_wall is False else "${price:.2f}".format(price=deposit_amount_for_price(row['min_sell'])),
                    'image_url' : row['image_url'],
                    'item_url'  : None
                }

                if pay_wall is False:
                    element['buttons'] = [{
                        'type'   : "postback",
                        'payload': "FLIP_COIN-{item_id}".format(item_id=item_id),
                        'title'  : "Flip Coin"
                    }]

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

    set_session_bonus(sender_id)

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT COUNT(*) AS `tot` FROM `item_winners` WHERE `fb_id` = %s AND `added` > DATE_SUB(NOW(), INTERVAL 4 HOUR);', (sender_id,))
            row = cur.fetchone()
            if row is not None:
                total_wins = row['tot']

            if has_paid_flip(sender_id, 16):
                win_boost -= 0.875

            cur.execute('SELECT `id`, `type`, `name`, `game_name`, `image_url`, `trade_url` FROM `flip_inventory` WHERE `id` = %s LIMIT 1;', (item_id,))
            row = cur.fetchone()

            if row is not None:
                flip_item = {
                    'item_id'   : row['id'],
                    'type'      : row['type'],
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

    if sender_id in Const.ADMIN_FB_PSID or random.uniform(0, flip_item['win_boost']) <= (1 / float(4)) * (abs(1 - (total_wins * 0.01))):
        send_tracker(fb_psid=sender_id, category="win", label=flip_item['name'])

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
                if sender_id not in Const.ADMIN_FB_PSID:
                    cur.execute('UPDATE `flip_inventory` SET `quantity` = `quantity` - 1 WHERE `id` = %s AND quantity > 0 LIMIT 1;', (flip_item['item_id'],))

                if flip_item['type'] == 3:
                    cur.execute('UPDATE `bonus_codes` SET `counter` = `counter` - 1 WHERE `code` = %s LIMIT 1;', (get_session_bonus(sender_id),))

                cur.execute('INSERT INTO `item_winners` (`fb_id`, `pin`, `item_id`, `item_name`, `added`) VALUES (%s, %s, %s, %s, NOW());', (sender_id, flip_item['pin_code'], flip_item['item_id'], flip_item['name']))
                conn.commit()
                cur.execute('SELECT @@IDENTITY AS `id` FROM `item_winners`;')
                flip_item['claim_id'] = cur.fetchone()['id']

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_image(sender_id, Const.FLIP_COIN_WIN_GIF_URL)
        send_card(
            recipient_id = sender_id,
            title = "{item_name}".format(item_name=flip_item['name']),
            image_url = flip_item['image_url'],
            buttons = [{
                'type' : "element_share"
            }]
        )

        send_text(sender_id, Const.FLIP_WIN_TEXT.format(item_name=flip_item['name'], game_name=flip_item['game_name'], claim_url=Const.FLIP_CLAIM_URL, sender_id=sender_id), main_menu_quick_reply())

        if get_session_trade_url(sender_id) is None:
            set_session_trade_url(sender_id, "_{PENDING}_")
            set_session_state(sender_id, Const.SESSION_STATE_FLIP_TRADE_URL)

        else:
            trade_url = get_session_trade_url(sender_id)
            send_text(
                recipient_id=sender_id,
                message_text="Trade URL set to {trade_url}".format(trade_url=trade_url),
                quick_replies=[{
                    'content_type': "text",
                    'title'       : "OK",
                    'payload'     : "TRADE_URL_OK"
                }, {
                    'content_type': "text",
                    'title'       : "Change",
                    'payload'     : "TRADE_URL_CHANGE"
                }, {
                    'content_type': "text",
                    'title'       : "Cancel",
                    'payload'     : "MAIN_MENU"
                }]
            )

    else:
        send_tracker(fb_psid=sender_id, category="loss", label=flip_item['name'])
        send_image(sender_id, Const.FLIP_COIN_LOSE_GIF_URL)
        send_text(
            recipient_id=sender_id,
            message_text="TRY AGAIN! You lost {item_name}.".format(item_name=flip_item['name']),
            quick_replies=coin_flip_quick_replies()
        )
        clear_session_dub(sender_id)



def check_lmon8_url(sender_id, deeplink=None):
    logger.info("check_lmon8_url(sender_id=%s, deeplink=%s)" % (sender_id, deeplink))




def get_session_state(sender_id):
    logger.info("get_session_state(sender_id=%s)" % (sender_id))
    state = Const.SESSION_STATE_NEW_USER

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT state FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            state = row['state']

        logger.info("state=%s" % (state,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_state[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return state

def set_session_state(sender_id, state=Const.SESSION_STATE_HOME):
    logger.info("set_session_state(sender_id=%s, state=%s)" % (sender_id, state))

    current_state = get_session_state(sender_id)
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if current_state == Const.SESSION_STATE_NEW_USER:
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
    logger.info("get_session_name(sender_id=%s)" % (sender_id,))
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

        logger.info("full_name=%s" % (full_name,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_name[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return full_name


def set_session_name(sender_id, first_name=None, last_name=None):
    logger.info("set_session_name(sender_id=%s, first_name=%s, last_name=%s)" % (sender_id, first_name, last_name))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET f_name = ?, l_name = ? WHERE fb_psid = ?;', (first_name, last_name, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_name[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_item(sender_id, item_type="flip"):
    logger.info("get_session_item(sender_id=%s, item_type=%s)" % (sender_id, item_type))
    item_id = None

    if item_type == "flip":
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('SELECT flip_id FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
            row = cur.fetchone()

            if row is not None:
                item_id = row['flip_id']

            logger.info("item_id=%s" % (item_id,))

        except sqlite3.Error as er:
            logger.info("::::::get_session_item[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

        finally:
            if conn:
                conn.close()

    else:
        purchase_id, item_id = get_session_purchase(sender_id)

    return item_id

def set_session_item(sender_id, item_id=0):
    logger.info("set_session_item(sender_id=%s, item_id=%s)" % (sender_id, item_id))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET flip_id = ? WHERE fb_psid = ?;', (item_id, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_item[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_deposit(sender_id, interval=24):
    logger.info("get_session_deposit(sender_id=%s, interval=%s)" % (sender_id, interval))

    deposit = 0
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT deposit FROM sessions WHERE fb_psid = ? LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            deposit = row['deposit']

        logger.info("deposit=%s" % (deposit,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_deposit[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return deposit


def inc_session_deposit(sender_id, amount=1):
    logger.info("inc_session_deposit(sender_id=%s, amount=%s)" % (sender_id, amount))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET deposit = deposit + ? WHERE fb_psid = ?;', (amount, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::inc_session_deposit[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_bonus(sender_id):
    logger.info("get_session_bonus(sender_id=%s)" % (sender_id,))

    bonus_code = None
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT bonus FROM sessions WHERE fb_psid = ? LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            bonus_code = row['bonus']

        logger.info("bonus_code=%s" % (bonus_code,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_bonus[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return bonus_code


def set_session_bonus(sender_id, bonus_code=None):
    logger.info("set_session_bonus(sender_id=%s, bonus_code=%s)" % (sender_id, bonus_code))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET bonus = ? WHERE fb_psid = ?;', (bonus_code, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_bonus[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_trade_url(sender_id):
    logger.info("get_session_trade_url(sender_id=%s)" % (sender_id,))
    trade_url = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT trade_url FROM sessions WHERE fb_psid = ? AND trade_url IS NOT NULL LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            trade_url = row['trade_url']

        logger.info("trade_url=%s" % (trade_url))

    except sqlite3.Error as er:
        logger.info("::::::get_session_trade_url[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return trade_url


def set_session_trade_url(sender_id, trade_url=None):
    logger.info("set_session_trade_url(sender_id=%s, trade_url=%s)" % (sender_id, trade_url))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET trade_url = ? WHERE fb_psid = ?;', (trade_url, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_trade_url[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_purchase(sender_id):
    logger.info("get_session_purchase(sender_id=%s)" % (sender_id,))
    purchase_id = None
    item = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT purchase_id FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            purchase_id = row['purchase_id']
            cur.execute('SELECT item_id FROM payments WHERE id = ? ORDER BY added DESC LIMIT 1;', (purchase_id,))
            row = cur.fetchone()
            if row is not None:
                item = row


        logger.info("purchase_id=%s" % (purchase_id,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_item[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return (purchase_id, item['id'])


def set_session_purchase(sender_id, purchase_id=0):
    logger.info("set_session_purchase(sender_id=%s, purchase_id=%s)" % (sender_id, purchase_id))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET purchase_id = ? WHERE fb_psid = ?;', (purchase_id, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_item[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_item_details(item_id):
    logger.info("get_item_details(item_id=%s)" % (item_id,))

    item = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `type`, `name`, `game_name`, `image_url`, `quantity`, `max_buy`, `min_sell` FROM `flip_inventory` WHERE `id` = %s LIMIT 1;', (item_id,))
            row = cur.fetchone()
            if row is not None:
                item = row

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return item


def wins_last_day(sender_id):
    logger.info("wins_last_day(sender_id=%s)" % (sender_id,))

    total_wins = 0
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT COUNT(*) AS `tot` FROM `item_winners` WHERE `fb_id` = %s AND `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR);', (sender_id,))
            row = cur.fetchone()
            total_wins = 0 if row is None else row['tot']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    logger.info("total_wins=%d" % total_wins)
    return total_wins


def deposit_amount_for_price(price):
    logger.info("deposit_amount_for_price(price=%s)" % (price,))

    amount = 0
    if price < 1.50:
        amount = 0

    elif price < 4.50:
        amount = 1

    elif price < 6.50:
        amount = 2

    elif price < 9.50:
        amount = 3

    elif price < 15.00:
        amount = 5

    return amount


def has_paid_flip(sender_id, hours=24):
    logger.info("has_paid_flip(sender_id=%s, hours=%s)" % (sender_id, hours))

    has_paid = False
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `fb_purchases` WHERE `fb_psid` = %s AND `added` > DATE_SUB(NOW(), INTERVAL %s HOUR);', (sender_id, hours))
            has_paid = cur.fetchone() is not None

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    logger.info("has_paid=%s" % has_paid)
    return has_paid


def valid_deeplink_code(sender_id, deeplink=None):
    logger.info("valid_deeplink_code(sender_id=%s, deeplink=%s)" % (sender_id, deeplink))

    is_valid = False
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `bonus_codes` WHERE `code` = %s AND `counter` > 0 AND `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR) LIMIT 1;', (deeplink.split("/")[-1],))
            is_valid = cur.fetchone() is not None

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return is_valid


def toggle_opt_out(sender_id, is_optout=True):
    logger.info("toggle_opt_out(sender_id=%s, is_optout=%s)" % (sender_id, is_optout))

    is_prev_oo = False
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT id FROM blacklisted_users WHERE `fb_psid` = ?;', (sender_id,))
        row = cur.fetchone()

        is_prev_oo = True if row is not None else False

        if is_prev_oo == False and is_optout == True:
            cur.execute('INSERT INTO blacklisted_users (id, fb_psid, added) VALUES (NULL, ?, ?);', (sender_id, int(time.time())))
            conn.commit()

        elif is_prev_oo == True and is_optout == False:
            cur.execute('DELETE FROM blacklisted_users WHERE `fb_psid` = ?;', (sender_id,))
            conn.commit()


        conn.close()


    except sqlite3.Error as er:
        logger.info("::::::opt_out[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('UPDATE `fbbot_logs` SET `enabled` = %s WHERE `chat_id` = %s;', (1 if is_optout else 0, sender_id,))
            conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    if is_optout:
        send_text(sender_id, "You will have opted out of Gamebots & will no longer recieve messages from Gamebots. If you need help visit facebook.com/gamebotsc", opt_out_quick_replies())
        return "OK", 200


def clear_session_dub(sender_id):
    logger.info("clear_session_dub(sender_id=%s)" % (sender_id,))

    set_session_item(sender_id)

    if get_session_trade_url(sender_id) == "_{PENDING}_":
        set_session_trade_url(sender_id)


    set_session_state(sender_id)



def purchase_item(sender_id, payment):
    logger.info("purchase_item(sender_id=%s, payment=%s)" % (sender_id, payment))
    send_tracker(fb_psid=sender_id, category="purchase")

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
            cur.execute('SELECT `id`, `name`, `info`, `image_url`, `price` FROM `fb_products` WHERE `id` = %s LIMIT 1;', (item_id,))
            row = cur.fetchone()

            if row is not None:
                item_name = row['name']

            f_name = get_session_name(sender_id) or " ".split()[0]
            l_name = get_session_name(sender_id) or " ".split()[-1]
            cur.execute('INSERT INTO `fb_purchases` (`id`, `fb_psid`, `first_name`, `last_name`, `email`, `item_id`, `amount`, `fb_payment_id`, `provider`, `charge_id`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s));', (sender_id, f_name, l_name, customer_email, item_id, amount, fb_payment_id, provider, charge_id, int(time.time())))
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
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('INSERT INTO payments (id, fb_psid, email, item_id, amount, fb_payment_id, provider, charge_id, added) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);', (purchase_id, sender_id, customer_email, item_id, amount, fb_payment_id, provider, charge_id, int(time.time())))
            conn.commit()

        except sqlite3.Error as er:
            logger.info("::::::payment[cur.execute] sqlite3.Error - %s" % (er.message,))

        finally:
            if conn:
                conn.close()

    # -- state 8 means purchased, but no trade url yet…
    set_session_state(sender_id)

    payload = {
        'channel'  : "#gamebots-purchases",
        'username' : "gamebotsc",
        'icon_url' : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
        'text'     : "*{customer_email}* ({fb_psid}) just purchased _{item_name}_ for ${item_price}".format(customer_email=customer_email, fb_psid=sender_id, item_name=item_name, item_price=amount),
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
                    logger.info("-=- READ CONFIRM -=- %s" % (messaging_event,))
                    send_tracker(fb_psid=messaging_event['sender']['id'], category="read-receipt")
                    return "OK", 200

                if 'optin' in messaging_event:  # optin confirmation
                    logger.info("-=- OPT-IN -=-")
                    return "OK", 200


                sender_id = messaging_event['sender']['id']
                message = messaging_event['message'] if 'message' in messaging_event else None
                message_id = message['mid'] if message is not None and 'mid' in message else messaging_event['id'] if 'id' not in entry else entry['id']
                quick_reply = messaging_event['message']['quick_reply']['payload'] if 'message' in messaging_event and 'quick_reply' in messaging_event['message'] and 'quick_reply' in messaging_event['message']['quick_reply'] else None# (if 'message' in messaging_event and 'quick_reply' in messaging_event['message'] and 'payload' in messaging_event['message']['quick_reply']) else None:
                logger.info("QR --> %s" % (quick_reply or None,))

                if sender_id in Const.BANNED_USERS:
                    return "OK", 200

                referral = None if 'referral' not in messaging_event else messaging_event['referral']['ref'].encode('ascii', 'ignore')
                if referral is None and 'postback' in messaging_event and 'referral' in messaging_event['postback']:
                    referral = messaging_event['postback']['referral']['ref'].encode('ascii', 'ignore')

                if referral is not None:
                    send_tracker(fb_psid=sender_id, category="referral", label=referral)
                    logger.info("REFERRAL ---> %s", (referral,))
                    if valid_deeplink_code(sender_id, referral):
                        set_session_bonus(sender_id, referral.split("/")[-1])


                # -- insert to log
                write_message_log(sender_id, message_id, { key : messaging_event[key] for key in messaging_event if key != 'timestamp' })


                if 'payment' in messaging_event: # payment result
                    logger.info("-=- PAYMENT -=-")
                    set_session_state(sender_id, Const.SESSION_STATE_PURCHASE_ITEM)
                    purchase_item(sender_id, messaging_event['payment'])
                    return "OK", 200


                #-- new entry
                if get_session_state(sender_id) == Const.SESSION_STATE_NEW_USER:
                    logger.info("----------=NEW SESSION @(%s)=----------" % (time.strftime("%Y-%m-%d %H:%M:%S")))
                    send_tracker(fb_psid=sender_id, category="sign-up-fb")

                    set_session_state(sender_id)
                    send_text(sender_id, "Welcome to Gamebots. WIN pre-sale games & items with players on Messenger.\n To opt-out of further messaging, type exit, quit, or stop.")
                    send_image(sender_id, "http://i.imgur.com/QHHovfa.gif")
                    default_carousel(sender_id)

                #-- existing
                elif get_session_state(sender_id) >= Const.SESSION_STATE_HOME and get_session_state(sender_id) < Const.SESSION_STATE_CHECKOUT_ITEM:
                    if get_session_name(sender_id) is None:
                        graph = fb_graph_user(sender_id)
                        if graph is not None:
                            set_session_name(sender_id, graph['first_name'] or "", graph['last_name'] or "")
                        set_session_state(sender_id)
                        default_carousel(sender_id)

                    else:
                        # ------- POSTBACK BUTTON MESSAGE
                        if 'postback' in messaging_event:  # user clicked/tapped "postback" button in earlier message
                            logger.info("POSTBACK --> %s" % (messaging_event['postback']['payload']))
                            handle_payload(sender_id, Const.PAYLOAD_TYPE_POSTBACK, messaging_event['postback']['payload'])
                            return "OK", 200



                        # -- actual message w/ txt
                        if 'message' in messaging_event:
                            logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECIEVED ->%s" % (messaging_event['sender']))

                            # ------- QUICK REPLY BUTTON
                            if 'quick_reply' in message and message['quick_reply']['payload'] is not None:
                                logger.info("QR --> %s" % (messaging_event['message']['quick_reply']['payload']))
                                handle_payload(sender_id, Const.PAYLOAD_TYPE_QUICK_REPLY, messaging_event['message']['quick_reply']['payload'])
                                return "OK", 200

                            # ------- TYPED TEXT MESSAGE
                            if 'text' in message:
                                recieved_text_reply(sender_id, message['text'])
                                return "OK", 200

                            # ------- ATTACHMENT SENT
                            if 'attachments' in message:
                                for attachment in message['attachments']:
                                    recieved_attachment(sender_id, attachment['type'], attachment['payload'])
                                return "OK", 200

                    set_session_state(sender_id)
                    default_carousel(sender_id)

                else:
                    set_session_state(sender_id)
                    default_carousel(sender_id)

    return "OK", 200


@app.route('/paypal', methods=['POST'])
def paypal():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/paypal'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.PAYPAL_TOKEN:
        logger.info("TOKEN VALID!")

        fb_psid = request.form['fb_psid']
        amount = float(request.form['amount'])

        logger.info("fb_psid=%s, amount=%s" % (fb_psid, amount))

        inc_session_deposit(fb_psid, amount)

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                f_name = get_session_name(fb_psid) or " ".split()[0]
                l_name = get_session_name(fb_psid) or " ".split()[-1]
                cur.execute('INSERT INTO `fb_purchases` (`id`, `fb_psid`, `first_name`, `last_name`, `amount`, `added`) VALUES (NULL, %s, %s, %s, %s, NOW());', (fb_psid, f_name, l_name, amount))
                conn.commit()

                cur.execute('SELECT @@IDENTITY AS `id` FROM `fb_purchases`;')
                row = cur.fetchone()
                purchase_id = row['id']


        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


        send_text(fb_psid, "Your Gamebots credit for ${amount:.2f} has been applied!".format(amount=amount))
        payload = {
            'channel' : "#pre",
            'username': "gamebotsc",
            'icon_url': "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text'    : "*{user}* just added ${amount:.2f} in credits".format(user=fb_psid if get_session_name(fb_psid) is None else get_session_name(fb_psid), amount=amount),
        }
        response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

#
    return "OK", 200


# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


def recieved_quick_reply(sender_id, quick_reply):
    logger.info("recieved_quick_reply(sender_id=%s, quick_reply=%s)" % (sender_id, quick_reply))

    # send_tracker("{show}-button".format(show=quick_reply.split("_")[-1].lower()), sender_id, "")
    logger.info("QR --> %s" % (quick_reply,))

    handle_payload(sender_id, Const.PAYLOAD_TYPE_OTHER, quick_reply)


def recieved_trade_url(sender_id, url, action=Const.TRADE_URL_FLIP_ITEM):
    logger.info("recieved_trade_url(sender_id=%s, url=%s, action=%s)" % (sender_id, url, action))

    if action == Const.TRADE_URL_PURCHASE:
        purchase_id = get_session_purchase(sender_id)

        if get_session_state(sender_id) == Const.SESSION_STATE_PURCHASED_TRADE_URL:
            send_text(sender_id, "Set your trade url to {url}?".format(url=url), quick_replies=submit_quick_replies())


    elif action == Const.TRADE_URL_FLIP_ITEM:
        if get_session_state(sender_id) == Const.SESSION_STATE_FLIP_TRADE_URL:
            send_text(sender_id, "Set your trade url to {url}?".format(url=url), quick_replies=submit_quick_replies(["Confirm", "Re-Enter"]))


def handle_payload(sender_id, payload_type, payload):
    logger.info("handle_payload(sender_id=%s, payload_type=%s, payload=%s)" % (sender_id, payload_type, payload))

    if payload == "MAIN_MENU":
        # send_tracker("todays-item", sender_id, "")
        clear_session_dub(sender_id)
        default_carousel(sender_id)


    elif payload == "WELCOME_MESSAGE":
        logger.info("----------=NEW SESSION @(%s)=----------" % (time.strftime("%Y-%m-%d %H:%M:%S")))
        # send_tracker("signup-fb", sender_id, "")
        default_carousel(sender_id)


    elif payload == "NEXT_ITEM":
        send_tracker(fb_psid=sender_id, category="next-item")
        default_carousel(sender_id, 1)


    elif re.search('FLIP_COIN-(\d+)', payload) is not None:
        send_tracker(fb_psid=sender_id, category="flip-coin", label=re.match(r'FLIP_COIN-(?P<item_id>\d+)', payload).group('item_id'))
        item_id = re.match(r'FLIP_COIN-(?P<item_id>\d+)', payload).group('item_id')
        if item_id is not None:
            set_session_item(sender_id, item_id)
            item = get_item_details(item_id)
            logger.info("ITEM --> %s", item)

            if deposit_amount_for_price(item['min_sell']) < 1:
                if wins_last_day(sender_id) < 5 or has_paid_flip(sender_id, 24):
                    coin_flip_results(sender_id, item_id)

                else:
                    send_tracker(fb_psid=sender_id, category="pay-wall", label=item['name'])
                    pay_wall_carousel(sender_id, 4)
                    send_text(sender_id, "You must add Gamebots Credits to win this item.\n\nCredits allow players to access higher priced items.\n\nUse PayPal and enter {fb_psid} in the buyer's notes.".format(fb_psid=sender_id))
                    send_text(sender_id, sender_id)
                    send_paypal_card(sender_id, 1.00)
                    send_text(sender_id, "You can unlock credits for free by completing the following below.\n\n1. Install + Open + Screenshot 10 apps: taps.io/skins\n\n\2. Type & send message \"Upload\" to Gamebots\n\n3. Upload each screenshot & wait 1 hour for verification.", main_menu_quick_reply())

            else:
                if has_paid_flip(sender_id, 24) and get_session_deposit(sender_id) >= deposit_amount_for_price(item['min_sell']):
                    send_tracker(fb_psid=sender_id, category="bonus-flip", label=get_session_bonus(sender_id))
                    coin_flip_results(sender_id, item_id)

                else:
                    send_tracker(fb_psid=sender_id, category="pay-wall", label=item['name'])
                    pay_wall_carousel(sender_id, 4)
                    send_text(sender_id, "You must add Gamebots Credits to win this item.\n\nCredits allow players to access higher priced items.\n\nUse PayPal and enter {fb_psid} in the buyer's notes.".format(fb_psid=sender_id))
                    send_text(sender_id, sender_id)
                    send_paypal_card(sender_id, deposit_amount_for_price(item['min_sell']) - get_session_deposit(sender_id), item['image_url'])
                    send_text(sender_id, "You can unlock credits for free by completing the following below.\n\n1. Install + Open + Screenshot 10 apps: taps.io/skins\n\n\2. Type & send message \"Upload\" to Gamebots\n\n3. Upload each screenshot & wait 1 hour for verification.", main_menu_quick_reply())

        else:
            send_text(sender_id, "Can't find that item! Try flipping again")
            return "OK", 200


    elif payload == "INVITE":
        send_tracker(fb_psid=sender_id, category="invite-friends")

        send_card(
            recipient_id =sender_id,
            title="Share Gamebots",
            image_url=Const.SHARE_IMAGE_URL,
            card_url="http://m.me/gamebotsc",
            buttons=[{ 'type' : "element_share" }],
            quick_replies=main_menu_quick_reply()
        )

    elif payload == "SUPPORT":
        send_tracker(fb_psid=sender_id, category="support")
        send_text(sender_id, "Because of high support volume you must purchase credits to access direct message support.")
        send_text(sender_id, "www.paypal.me/gamebotsc/2\n\nEnter {fb_psid}-support in the buyer's notes.".format(fb_psid=sender_id))
        send_text(sender_id, "After payment DM: twitter.com/bryantapawan24", main_menu_quick_reply())

        payload = {
            'channel'  : "#pre",
            'username' : "gamebotsc",
            'icon_url' : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text'     : "*{user}* needs help…".format(user=sender_id if get_session_name(sender_id) is None else get_session_name(sender_id)),
        }
        response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

    elif payload == "NO_THANKS":
        send_tracker(fb_psid=sender_id, category="no-thanks")
        default_carousel(sender_id)

    elif payload == "TRADE_URL_OK":
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('UPDATE `item_winners` SET `trade_url` = %s WHERE `fb_id` = %s ORDER BY `added` DESC LIMIT 1;', (get_session_trade_url(sender_id), sender_id))
                conn.commit()
        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
        finally:
            if conn:
                conn.close()

        set_session_state(sender_id, Const.SESSION_STATE_FLIP_LMON8_URL)
        send_text(sender_id, "Enter your Lemonade shop name. If you don't have one go here: taps.io/makeshop\n\nInstructions for trade to process:\n\n1. Make sure your correct Steam trade URL is set.\n\n2. Make sure you enter a valid Lemonade shop URL.", main_menu_quick_reply())

    elif payload == "TRADE_URL_CHANGE":
        set_session_trade_url(sender_id, "_{PENDING}_")
        set_session_state(sender_id, Const.SESSION_STATE_FLIP_TRADE_URL)
        send_text(sender_id, "Enter your Steam Trade URL now.")

    elif payload == "SUBMIT_YES":
        if get_session_state(sender_id) == Const.SESSION_STATE_FLIP_TRADE_URL:
            trade_url = get_session_trade_url(sender_id)
            send_tracker(fb_psid=sender_id, category="trade-url-set")
            send_text(sender_id, "Trade URL set to {trade_url}".format(trade_url=trade_url))

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('UPDATE `item_winners` SET `trade_url` = %s WHERE `fb_id` = %s ORDER BY `added` DESC LIMIT 1;', (trade_url, sender_id))
                    conn.commit()
            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
            finally:
                if conn:
                    conn.close()

            payload = {
                'channel'   : "#bot-alerts",
                'username ' : "gamebotsc",
                'icon_url'  : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
                'text'      : "Trade URL set for *{user}*:\n{trade_url}".format(user=sender_id if get_session_name(sender_id) is None else get_session_name(sender_id), trade_url=trade_url)
            }
            response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

            set_session_state(sender_id, Const.SESSION_STATE_FLIP_LMON8_URL)
            send_text(sender_id, "Instructions to complete trade.\n\n1. MAKE a shop on Lemonade: taps.io/makeshop\n2. SHARE Shop with 3 friends on Messenger.\n3.Enter your Lemonade shop url now.", main_menu_quick_reply())

        elif get_session_state(sender_id) == Const.SESSION_STATE_FLIP_LMON8_URL:
            send_tracker(fb_psid=sender_id, category="lmon-name-entered")
            send_text(sender_id, "Please wait for your Trade to clear, non credit users must wait 24 hours for trade to complete.")

            clear_session_dub(sender_id)
            default_carousel(sender_id)

        elif get_session_state(sender_id) == Const.SESSION_STATE_PURCHASED_TRADE_URL:
            purchase_id, item_id = get_session_purchase(sender_id)
            trade_url = get_session_trade_url(sender_id)
            send_text(sender_id, "Trade URL set to {trade_url}".format(trade_url=trade_url))

            conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            try:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('UPDATE payments SET `trade_url` = ? WHERE `id` = ? LIMIT 1;', (trade_url, purchase_id))
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
                    cur.execute('UPDATE `fb_purchases` SET `trade_url` = %s WHERE `id` = %s LIMIT 1;', (trade_url, purchase_id))
                    conn.commit()

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

        else:
            clear_session_dub(sender_id)
            default_carousel(sender_id)

    elif payload == "SUBMIT_NO":
        if get_session_state(sender_id) == Const.SESSION_STATE_FLIP_TRADE_URL:
            send_text(sender_id, "Re-enter your steam trade url to claim {item_name}".format(item_name=get_session_item(sender_id)), main_menu_quick_reply())
            set_session_state(sender_id, Const.SESSION_STATE_FLIP_TRADE_URL)

        elif get_session_state(sender_id) == Const.SESSION_STATE_PURCHASED_TRADE_URL:
            purchase_id = get_session_purchase(sender_id)

            set_session_state(sender_id, Const.SESSION_STATE_PURCHASED_ITEM)
            send_text(sender_id, "Re-enter your steam trade url to recieve {item_name}".format(item_name=get_session_purchase(sender_id)), main_menu_quick_reply())

        elif get_session_state(sender_id) == Const.SESSION_STATE_FLIP_LMON8_URL:
            send_text(sender_id, "Re-enter your lmon8 shop url to recieve {item_name}".format(item_name=get_session_item(sender_id)), main_menu_quick_reply())

        else:
            clear_session_dub(sender_id)
            default_carousel(sender_id)

    elif payload == "SUBMIT_CANCEL":
        clear_session_dub(sender_id)
        default_carousel(sender_id)

    elif payload == "NO_THANKS":
        # send_tracker("no-thanks", sender_id, "")
        default_carousel(sender_id)

    else:
        default_carousel(sender_id)
    return "OK", 200


def recieved_text_reply(sender_id, message_text):
    logger.info("recieved_text_reply(sender_id=%s, message_text=%s)" % (sender_id, message_text))

    if message_text.lower() in Const.OPT_OUT_REPLIES:
        logger.info("-=- ENDING HELP -=- (%s)" % (time.strftime("%Y-%m-%d %H:%M:%S")))
        toggle_opt_out(sender_id, True)

    elif message_text.lower() in Const.MAIN_MENU_REPLIES:
        clear_session_dub(sender_id)
        default_carousel(sender_id)

    elif message_text.lower() in Const.GIVEAWAY_REPLIES:
        send_text(sender_id, "You are entry #{queue} into today's flash giveaway.\n\nTo increase your chances you can install & upload free apps or buy a Gamebots credit.".format(queue=int(random.uniform(100, 900))))
        send_text(sender_id, "Instructions:\n1. Install game: Taps.io/skins\n\n2. Open & screenshot game\n\n3. Upload screenshot here")
        send_text(sender_id, "Purchase credits: paypal.me/gamebotsc/1", main_menu_quick_reply())

    elif message_text.lower() in Const.UPLOAD_REPLIES:
        send_text(sender_id, "Please upload a screenshot of the moderator task you have completed. Once approved you will be rewarded your skins. (wait time: 24 hours)")

    elif message_text.lower() in Const.APPNEXT_REPLIES:
        send_text(sender_id, "Instructions…\n\n1. GO: taps.io/skins\n\n2. OPEN & Screenshot each free game or app you install.\n\n3. SEND screenshots for proof on Twitter.com/gamebotsc\n\nEvery free game or app you install increases your chances of winning.", main_menu_quick_reply())

    elif message_text.lower() in Const.MODERATOR_REPLIES:
        send_text(sender_id, "Mod Tasks for Skins:\n\n1. Install 5 free games get 1 Mac Neon. \nTaps.io/skins\n\n2. Share Lemonade shop on 10 Facebook Groups get 1 Mac Neon.\n\n3. Create an auto shop on Lemonade and sell 1 item get 1 blue laminate.\n\n4. Share Gamebots with 200 friends on Messenger get 1 Misty Frontside.\n\n5. Share Lemonade with 200 friends on Messenger and get 1 Misty Frontside.\n\n6. Make a Gamebots post on Reddit and get 1 Mac 10 Neon Rider.\n\n7. Make a Gamebots Discord channel and invite 5 friends and get 1 Mac 10 Neon Rider.\n\nWhen you finish a task take a screenshot & upload it to Gamebots by typing \"Upload\".")

    else:
        if get_session_state(sender_id) == Const.SESSION_STATE_FLIP_TRADE_URL or get_session_state(sender_id) == Const.SESSION_STATE_PURCHASED_TRADE_URL:
            if re.search(r'.*steamcommunity\.com\/tradeoffer\/.*$', message_text) is not None:
                set_session_trade_url(sender_id, message_text)
                recieved_trade_url(sender_id, message_text)

            else:
                send_text(
                    recipient_id=sender_id,
                    message_text="Invalid URL, try again...",
                    quick_replies=main_menu_quick_reply()
                )

        elif get_session_state(sender_id) == Const.SESSION_STATE_FLIP_LMON8_URL:
            url = "http://m.me/lmon8?ref={deeplink}".format(deeplink=re.sub(r'[\,\'\"\`\~\ \:\;\^\%\#\&\*\$\@\!\/\?\=\+\-\|\(\)\[\]\{\}\\\<\>]', "", message_text.encode('ascii', 'ignore')))
            send_text(sender_id, "Set your lmon8 shop link to {url}?".format(url=url), quick_replies=submit_quick_replies())

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('UPDATE `item_winners` SET `prebot_url` = %s WHERE `fb_id` = %s ORDER BY `added` DESC LIMIT 1;', (url, sender_id))
                    conn.commit()
            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
            finally:
                if conn:
                    conn.close()

        else:
            default_carousel(sender_id)


def recieved_attachment(sender_id, attachment_type, attachment):
    logger.info("recieved_attachment(sender_id=%s, attachment_type=%s, attachment=%s)" % (sender_id, attachment_type, attachment))

    if attachment_type == Const.PAYLOAD_ATTACHMENT_IMAGE.split("-")[-1]:
        payload = {
            'channel'     : "#bot-alerts",
            'username '   : "gamebotsc",
            'icon_url'    : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text'        : "Image upload from *{user}* _{fb_psid}_:\n{image_url}".format(user=sender_id if get_session_name(sender_id) is None else get_session_name(sender_id), fb_psid=sender_id, image_url=attachment['url']),
            'attachments' : [{
                'image_url' : attachment['url']
            }]
        }
        response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

        send_text(sender_id, "You have won 100 skin pts! Every 1000 skin pts you get a MAC 10 Neon Rider!\n\nTerms: your pts will be rewarded once the screenshot you upload is verified.", main_menu_quick_reply())

    elif attachment_type != Const.PAYLOAD_ATTACHMENT_URL.split("-")[-1] or attachment_type != Const.PAYLOAD_ATTACHMENT_FALLBACK.split("-")[-1]:
        send_text(sender_id, "I'm sorry, I cannot understand that type of message.", home_quick_replies())


def send_typing_indicator(recipient_id, is_typing):
    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'sender_action' : "typing_on" if is_typing else "typing_off"
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


def send_card(recipient_id, title, image_url, card_url=None, subtitle=None, buttons=None, quick_replies=None):
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
                        'subtitle'  : subtitle or "",
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
            'id'          : recipient_id
        },
        'message'   : {
            'attachment'  : {
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
    logger.info("send_message(payload=%s)" % (payload,))

    response = requests.post(
        url="https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN),
        params={ 'access_token' : Const.ACCESS_TOKEN },
        json=json.loads(payload)
    )

    logger.info("GRAPH RESPONSE (%s): %s" % (response.status_code, response.text))
    return True


def fb_graph_user(recipient_id):
    logger.info("fb_graph_user(recipient_id=%s)" % (recipient_id,))

    params = {
        'fields'      : "first_name,last_name,profile_pic,locale,timezone,gender,is_payment_enabled",
        'access_token': Const.ACCESS_TOKEN
    }
    response = requests.get("https://graph.facebook.com/v2.6/{recipient_id}".format(recipient_id=recipient_id), params=params)
    return None if 'error' in response.json() else response.json()

if __name__ == '__main__':
    app.run(debug=True)


# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#
