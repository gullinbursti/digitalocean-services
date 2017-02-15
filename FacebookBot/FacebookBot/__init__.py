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

import const as Const

reload(sys)
sys.setdefaultencoding('utf8')


app = Flask(__name__)

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler('/var/log/FacebookBot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

Const.DB_HOST = 'external-db.s4086.gridserver.com'
Const.DB_NAME = 'db4086_modd'
Const.DB_USER = 'db4086_modd_usr'
Const.DB_PASS = 'f4zeHUga.age'

Const.VERIFY_TOKEN = "d41d8cd98f00b204e9800998ecf8427e"
Const.ACCESS_TOKEN = "EAAXFDiMELKsBAESoNb9hvGcOarJZCSuHJOQCjC835GS1QwwlOn8D255xPF86We1Wxg4DtxQqr91aHFYjFoOybUOVBTdtDalFKNLcjA2EXTEIGHXEMRbsA4vghEWKiIpB6nbzsX6G5rYBZCHuBc1UlsUnOqwZAS2jY56xppiIgZDZD"

Const.FLIP_COIN_START_GIF_URL = "http://i.imgur.com/C6Pgtf4.gif"
Const.FLIP_COIN_WIN_GIF_URL = "http://i.imgur.com/9fmZntz.gif"
Const.FLIP_COIN_LOSE_GIF_URL = "http://i.imgur.com/7YNujdq.gif"

Const.MAX_IGNORES = 4

Const.OPT_OUT_REPLIES = "optout|quit|end|stop|cancel|exit"

# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


def send_tracker(category, action, label):
    logger.info("send_tracker(category={category}, action={action}, label={label})".format(category=category, action=action, label=label))


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
    logger.info("write_message_log(sender_id={sender_id}, message_id={message_id}, message_txt={message_txt})".format(sender_id=sender_id, message_id=message_id, message_txt=json.dumps(message_txt)))

    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME)
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('INSERT INTO `fbbot_logs` (`id`, `message_id`, `chat_id`, `body`) VALUES (NULL, %s, %s, %s)', (message_id, sender_id, json.dumps(message_txt)))

    except mdb.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()


def main_menu_quick_replies():
    logger.info("main_menu_quick_replies()")
    return [
        {
            'content_type' : "text",
            'title'        : "Today's Big Item",
            'payload'      : "TODAYS_ITEM"
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
    logger.info("default_carousel(sender_id={sender_id})".format(sender_id=sender_id))

    elements = [
        coin_flip_element(sender_id)
    ]

    if sender_id == "1298454546880273":
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
    logger.info("daily_item_element(sender_id={sender_id}, standalone={standalone})".format(sender_id=sender_id, standalone=standalone))

    element = None

    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `game_name`, `image_url`, `price` FROM `flip_inventory` WHERE `type` = 2 ORDER BY RAND() LIMIT 1;')
            row = cur.fetchone()

            if row is not None:
                set_session_item(sender_id, row['id'])

                element = {
                    'title'     : "{item_name}".format(item_name=row['name'].encode('utf8')),
                    'subtitle'  : "",
                    'image_url' : row['image_url'],
                    'item_url'  : None,
                    'buttons'   : [{
                        'type'            : "payment",
                        'title'           : "Buy",
                        'payload'         : "%s-%d" % ("PURCHASE_ITEM", row['id']),
                        'payment_summary' : {
                            'currency'            : "USD",
                            'payment_type'        : "FIXED_AMOUNT",
                            'is_test_payment'     : True,
                            'merchant_name'       : "Gamebots",
                            'requested_user_info' : [
                                "contact_email"
                            ],
                            'price_list' : [{
                                'label'  : "Subtotal",
                                'amount' : row['price']
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
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()

    return element

def coin_flip_element(sender_id, standalone=False):
    logger.info("coin_flip_element(sender_id={sender_id}, standalone={standalone})".format(sender_id=sender_id, standalone=standalone))

    element = None

    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
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
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()

    return element


def coin_flip_results(sender_id, item_id=None):
    logger.info("coin_flip_results(sender_id={sender_id}, item_id={item_id})".format(sender_id=sender_id, item_id=item_id))

    send_image(sender_id, Const.FLIP_COIN_START_GIF_URL)

    if item_id is None:
        send_text(sender_id, "Can't find your item! Try flipping for it again")
        return "OK", 200

    total_wins = 1
    flip_item = None
    win_boost = 1

    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `kik_name` FROM `item_winners` WHERE `fb_id` = {sender_id} LIMIT 1;'.format(sender_id=sender_id))
            if cur.fetchone() is not None:
                win_boost = 0.5

            cur.execute('SELECT COUNT(*) AS `tot` FROM `item_winners` WHERE `fb_id` = {sender_id} AND `added` > DATE_SUB(NOW(), INTERVAL 2 HOUR);'.format(sender_id=sender_id))
            row = cur.fetchone()
            if row is not None:
                total_wins = row['tot']

            cur.execute('SELECT `id`, `name`, `game_name`, `image_url`, `trade_url` FROM `flip_inventory` WHERE `id` = {item_id} LIMIT 1;'.format(item_id=item_id))
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
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()


    if random.uniform(0, flip_item['win_boost']) <= ((1 / float(4)) * (abs(1 - (total_wins * 0.01)))) or sender_id == "1219553058088713":
        total_wins += 1
        payload = {
            'channel'     : "#bot-alerts",
            'username'    : "gamebotsc",
            'icon_url'    : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text'        : "Flip Win by *{sender_id}*:\n_{item_name}_\n{pin_code}".format(sender_id=sender_id, item_name=flip_item['item_id'], pin_code=flip_item['pin_code']),
            'attachments' : [{
                'image_url' : flip_item['image_url']
            }]
        }
        response = requests.post("https://hooks.slack.com/services/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",data={'payload': json.dumps(payload)})

        conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('UPDATE `flip_inventory` SET `quantity` = `quantity` - 1 WHERE `id` = {item_id} LIMIT 1;'.format(item_id=flip_item['item_id']))
                cur.execute('INSERT INTO `item_winners` (`fb_id`, `pin`, `item_id`, `item_name`, `added`) VALUES (%s, %s, %s, %s, NOW());', (sender_id, flip_item['pin_code'], flip_item['item_id'], flip_item['name']))
                conn.commit()
                flip_item['claim_id'] = cur.lastrowid

        except mdb.Error, e:
            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

        finally:
            if conn:
                cur.close()

        send_image(sender_id, Const.FLIP_COIN_WIN_GIF_URL)
        send_card(
            recipient_id=sender_id,
            title="{item_name}".format(item_name=flip_item['name']),
            image_url=flip_item['image_url'],
            card_url="http://prebot.me/claim/{claim_id}/{sender_id}".format(claim_id=flip_item['claim_id'], sender_id=sender_id),
            buttons=[
                {
                    'type'  : "element_share"
                }, {
                    'type'                 : "web_url",
                    'url'                  : "http://prebot.me/claim/{claim_id}/{sender_id}".format(claim_id=flip_item['claim_id'], sender_id=sender_id),
                    'title'                : "Trade",
                    'webview_height_ratio' : "compact"
                }
            ]
        )

        if total_wins >= 5:
            send_text(sender_id, "You must install one of these apps before claiming {item_name}.\n\nhttp://taps.io/BgNYg".format(item_name=flip_item['name']))

        send_text(
            recipient_id=sender_id,
            message_text="WINNER! You won {item_name} - {pin_code} from {game_name}.\n\nSign into Steam: {claim_url}\n\nFollow all instructions to get items.".format(item_name=flip_item['name'], pin_code=flip_item['pin_code'], game_name=flip_item['game_name'],claim_url="http://prebot.me/claim/{claim_id}/{sender_id}".format(claim_id=flip_item['claim_id'], sender_id=sender_id)),
            quick_replies=coin_flip_quick_replies()
        )

    else:
        send_image(sender_id, Const.FLIP_COIN_LOSE_GIF_URL)
        send_text(
            recipient_id=sender_id,
            message_text="TRY AGAIN! You lost {item_name} from {game_name}.".format(item_name=flip_item['name'], game_name=flip_item['game_name']),
            quick_replies=coin_flip_quick_replies()
        )


def opt_out(sender_id):
    logger.info("opt_out(sender_id={sender_id})".format(sender_id=sender_id))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        cur = conn.cursor()
        cur.execute('SELECT id FROM blacklisted_users WHERE fb_psid = "{fb_psid}" ORDER BY added DESC LIMIT 1;'.format(fb_psid=sender_id))
        row = cur.fetchone()

        if row is None:
            cur.execute('INSERT INTO blacklisted_users (id, fb_psid, added) VALUES (NULL, ?, ?);', (sender_id, int(time.time())))
            conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

    finally:
        if conn:
            conn.close()

    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('UPDATE `fbbot_logs` SET `enabled` = 0 WHERE `chat_id` = {fb_psid};'.format(fb_psid=sender_id))
            conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()

    send_text(sender_id, "You will no longer recieve messages from Gamebots. If you need help visit facebook.com/gamebotsc", opt_out_quick_replies())


def get_session_state(sender_id):
    logger.info("get_session_state(sender_id={sender_id})".format(sender_id=sender_id))
    state = 0

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        cur = conn.cursor()
        cur.execute('SELECT state FROM sessions WHERE fb_psid = "{fb_psid}" ORDER BY added DESC LIMIT 1;'.format(fb_psid=sender_id))
        row = cur.fetchone()

        if row is not None:
            state = row[0]

        logger.info("state={state}".format(state=state))

    except sqlite3.Error as er:
        logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

    finally:
        if conn:
            conn.close()

    return state

def set_session_state(sender_id, state):
    logger.info("set_session_state(sender_id={sender_id}, state={state})".format(sender_id=sender_id, state=state))

    current_state = get_session_state(sender_id)

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        cur = conn.cursor()
        if current_state == 0:
            cur.execute('INSERT INTO sessions (id, fb_psid, state, added) VALUES (NULL, ?, ?, ?);', (sender_id, state, int(time.time())))

        else:
            cur.execute('UPDATE sessions SET state = {state} WHERE fb_psid = "{fb_psid}";'.format(state=state, fb_psid=sender_id))

        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

    finally:
        if conn:
            conn.close()


def get_session_item(sender_id):
    logger.info("get_session_item(sender_id={sender_id})".format(sender_id=sender_id))
    item_id = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        cur = conn.cursor()
        cur.execute('SELECT flip_id FROM sessions WHERE fb_psid = "{fb_psid}" ORDER BY added DESC;'.format(fb_psid=sender_id))
        row = cur.fetchone()

        if row is not None:
            item_id = row[0]

        logger.info("item_id={item_id}".format(item_id=item_id))

    except sqlite3.Error as er:
        logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

    finally:
        if conn:
            conn.close()

    return item_id

def set_session_item(sender_id, item_id):
    logger.info("set_session_item(sender_id={sender_id}, item_id={item_id})".format(sender_id=sender_id, item_id=item_id))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET flip_id = {flip_id} WHERE fb_psid = "{fb_psid}";'.format(flip_id=item_id, fb_psid=sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

    finally:
        if conn:
            conn.close()



@app.route('/', methods=['GET'])
def verify():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info(
        "=-=-=-=-=-=-=-=-=-=-=-=-= VERIFY ({hub_mode})->{request}\n".format(hub_mode=request.args.get('hub.mode'), request=request))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == Const.VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args['hub.challenge'], 200

    return "OK", 200


@app.route('/', methods=['POST'])
def webook():
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

                    purchase_id = 0
                    payment = messaging_event['payment']
                    item_id = re.match(r'^PURCHASE_ITEM\-(?P<item_id>\d+)$', payment['payload']).group('item_id')
                    item_name = None
                    customer_email = payment['requested_user_info']['contact_email']
                    amount = payment['amount']['amount']
                    fb_payment_id = payment['payment_credential']['fb_payment_id']
                    provider = payment['payment_credential']['provider_type']
                    charge_id = payment['payment_credential']['charge_id']

                    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
                    try:
                        with conn:
                            cur = conn.cursor(mdb.cursors.DictCursor)
                            cur.execute('SELECT `id`, `name`, `game_name`, `image_url` FROM `flip_inventory` WHERE `id` = {item_id} LIMIT 1;'.format(item_id=item_id))
                            row = cur.fetchone()

                            if row is not None:
                                item_name = row['name']

                    except mdb.Error, e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()


                    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
                    try:
                        with conn:
                            cur = conn.cursor(mdb.cursors.DictCursor)
                            cur.execute('INSERT INTO `fb_purchases` (`id`, `fb_psid`, `email`, `item_id`, `amount`, `fb_payment_id`, `provider`, `charge_id`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s));', (sender_id, customer_email, item_id, amount, fb_payment_id, provider, charge_id, int(time.time())))
                            conn.commit()
                            cur.execute('SELECT @@IDENTITY AS `id` FROM `fb_purchases`;')
                            row = cur.fetchone()
                            purchase_id = row['id']

                    except mdb.Error, e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()

                    if purchase_id != 0:
                        try:
                            conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
                            cur = conn.cursor()
                            cur.execute('INSERT INTO payments (id, fb_psid, email, item_id, amount, fb_payment_id, provider, charge_id, added) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);', (purchase_id, sender_id, customer_email, item_id, amount, fb_payment_id, provider, charge_id, int(time.time())))
                            conn.commit()

                        except sqlite3.Error as er:
                            logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

                        finally:
                            if conn:
                                conn.close()


                    send_text(sender_id, "You have successfully purchased {item_name}!".format(item_name=item_name))
                    return "OK", 200



                try:
                    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
                    cur = conn.cursor()
                    cur.execute('SELECT id FROM blacklisted_users WHERE fb_psid = "{fb_psid}";'.format(fb_psid=sender_id))
                    row = cur.fetchone()
                    if row is not None:
                        if 'message' in messaging_event and 'quick_reply' in messaging_event['message'] and messaging_event['message']['quick_reply']['payload'] == "OPT_IN":
                            cur.execute('DELETE FROM blacklisted_users WHERE fb_psid = "{fb_psid}";'.format(fb_psid=sender_id))
                            conn.commit()
                            conn.close()

                            conn2 = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
                            try:
                                with conn2:
                                    cur2 = conn.cursor(mdb.cursors.DictCursor)
                                    cur2.execute('UPDATE `fbbot_logs` SET `enabled` = 1 WHERE `chat_id` = {fb_psid};'.format(fb_psid=sender_id))
                                    conn2.commit()

                            except mdb.Error, e:
                                logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                            finally:
                                if conn2:
                                    cur2.close()

                        else:
                            conn.close()
                            send_text(sender_id, "You have opted out of Gamebots.", opt_out_quick_replies())
                            return "OK", 200

                except sqlite3.Error as er:
                    logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

                finally:
                    if conn:
                        cur.close()


                #-- new entry
                if get_session_state(sender_id) == 0:
                    logger.info("----------=NEW SESSION @({timestamp})=----------".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
                    send_tracker("signup-fb", sender_id, "")

                    set_session_state(sender_id, 1)
                    send_text(sender_id, "Welcome to Gamebots. WIN pre-sale games & items with players on Messenger.\n To opt-out of further messaging, type exit, quit, or stop.")
                    send_image(sender_id, "http://i.imgur.com/QHHovfa.gif")
                    default_carousel(sender_id)

                #-- existing reply
                else:
                    # ------- POSTBACK BUTTON MESSAGE
                    if 'postback' in messaging_event:  # user clicked/tapped "postback" button in earlier message
                        logger.info("-=- POSTBACK RESPONSE -=- (%s)" % (messaging_event['postback']['payload']))

                        if messaging_event['postback']['payload'] == "WELCOME_MESSAGE":
                            logger.info("----------=NEW SESSION @({timestamp})=----------".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
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
                        logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECIEVED ->{message}".format(message=messaging_event['sender']))

                        message = messaging_event['message']

                        # MESSAGE CREDENTIALS
                        message_id = message['mid']

                        # -- insert to log
                        write_message_log(sender_id, message_id, message)

                        # ------- IMAGE MESSAGE
                        if 'attachments' in messaging_event['message']:
                            send_text(sender_id, "I'm sorry, I cannot understand that type of message.")
                            return "OK", 200


                        # ------- QUICK REPLY BUTTON
                        if 'quick_reply' in message and message['quick_reply']['payload'] is not None:
                            logger.info("QR --> {quick_replies}".format(quick_replies=quote(messaging_event['message']['quick_reply']['payload'])))
                            quick_reply = quote(messaging_event['message']['quick_reply']['payload'])

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
                                    'text'     : "*{sender_id}* needs help…".format(sender_id=sender_id),
                                }
                                response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

                            elif quick_reply == "NEXT_ITEM":
                                send_tracker("next-item", sender_id, "")
                                default_carousel(sender_id)

                                # send_carousel(recipient_id=sender_id, elements=[coin_flip_element(sender_id, True)])

                            elif quick_reply == "NO_THANKS":
                                send_tracker("no-thanks", sender_id, "")
                                default_carousel(sender_id)

                            elif quick_reply == "TODAYS_ITEM":
                                send_tracker("todays-item", sender_id, "")
                                default_carousel(sender_id)

                            else:
                                default_carousel(sender_id)

                            return "OK", 200


                        # ------- TYPED TEXT MESSAGE
                        if 'text' in message:
                            message_text = message['text']

                            # -- typed '!end' / 'cancel' / 'quit'
                            if message_text.lower() in Const.OPT_OUT_REPLIES:
                                logger.info("-=- ENDING HELP -=- ({timestamp})".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
                                opt_out(sender_id)

                            else:
                                send_text(sender_id, "Welcome to Gamebots. WIN pre-sale games & items with players on Messenger.")
                                default_carousel(sender_id)

    return "OK", 200


def send_text(recipient_id, message_text, quick_replies=None):
    logger.info("send_text(recipient_id={recipient}, message_text={text}, quick_replies={quick_replies})".format(recipient=recipient_id, text=message_text, quick_replies=quick_replies))

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


def send_card(recipient_id, title, image_url, card_url, subtitle="", buttons=None, quick_replies=None):
    logger.info("send_card(recipient_id={recipient}, title={title}, image_url={image_url}, card_url={card_url}, subtitle={subtitle}, buttons={buttons}, quick_replies={quick_replies})".format(recipient=recipient_id, title=title, image_url=image_url, card_url=card_url, subtitle=subtitle, buttons=buttons, quick_replies=quick_replies))

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


def send_carousel(recipient_id, elements, quick_replies=None):
    logger.info("send_carousel(recipient_id={recipient}, elements={elements}, quick_replies={quick_replies})".format(recipient=recipient_id, elements=elements, quick_replies=quick_replies))

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


def send_image(recipient_id, url, quick_replies=None):
    logger.info("send_image(recipient_id={recipient}, url={url}, quick_replies={quick_replies})".format(recipient=recipient_id, url=url, quick_replies=quick_replies))

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


def send_video(recipient_id, url, quick_replies=None):
    logger.info("send_image(recipient_id={recipient}, url={url}, quick_replies={quick_replies})".format(recipient=recipient_id, url=url, quick_replies=quick_replies))

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


def send_message(payload):
    logger.info("send_message(payload={payload})".format(payload=payload))


    response = requests.post(
        url="https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN),
        params={ 'access_token' : Const.ACCESS_TOKEN },
        json=json.loads(payload)
    )

    logger.info("GRAPH RESPONSE ({code}): {result}".format(code=response.status_code, result=response.text))

    return True


if __name__ == '__main__':
    app.run(debug=True)


# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#

