#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import hashlib
import json
import locale
import logging
import os
import random
import re
import statistics
import sqlite3
import sys
import time

from itertools import cycle
from StringIO import StringIO
from urllib import urlencode

import MySQLdb as mdb
import pycurl
import requests

from flask import Flask, request

from constants import Const

reload(sys)
sys.setdefaultencoding('utf8')
locale.setlocale(locale.LC_ALL, 'en_US.utf8')

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


def buy_credits_button(sender_id, item_id, price):
    logger.info("buy_credits_button(sender_id=%s item_id=%s, price=%s)" % (sender_id, item_id, price))

    return {
        'type'            : "payment",
        'title'           : "Buy",
        'payload'         : "%s-%d" % ("PURCHASE_ITEM", item_id),
        'payment_summary' : {
            'currency'            : "USD",
            'payment_type'        : "FIXED_AMOUNT",
            'is_test_payment'     : Const.TEST_PAYMENTS == 1,
            'merchant_name'       : "Gamebots",
            'requested_user_info' : [
                "contact_email"
            ],
            'price_list'          : [{
                'label'  : "Subtotal",
                'amount' : price
            }]
        }
    }

def default_carousel(sender_id, amount=1):
    logger.info("default_carousel(sender_id=%s amount=%s)" % (sender_id, amount))

    set_session_item(sender_id)

    elements = []
    for i in range(amount):# + 5 if sender_id in Const.ADMIN_FB_PSID else amount):
        elements.append(coin_flip_element(sender_id))

    if None in elements:
        send_text(sender_id, "No items are available right now, try again later")
        return

    send_carousel(
        recipient_id=sender_id,
        elements=elements,
        quick_replies=home_quick_replies()
    )


def pay_wall_carousel(sender_id, amount=1):
    logger.info("pay_wall_carousel(sender_id=%s amount=%s)" % (sender_id, amount))
    set_session_item(sender_id)

    obj = {}
    for i in range(int(amount * 3)):
        element = coin_flip_element(sender_id, True, True)
        obj[element['title']] = element
        if len(obj) == amount:
            break

    elements = [value for key, value in obj.items()]
    send_carousel(
        recipient_id=sender_id,
        elements=random.sample(elements, min(amount, len(elements))) if len(elements) > 0 else [coin_flip_element(sender_id, True, True)],
        quick_replies=home_quick_replies()
    )


def send_paypal_card(sender_id, price, image_url=None):
    logger.info("send_paypal_card(sender_id=%s, price=%s)" % (sender_id, price))

    send_card(
        recipient_id=sender_id,
        title="GameBots Deposit",
        subtitle="${price:.2f}".format(price=price),
        image_url="https://scontent.xx.fbcdn.net/v/t31.0-8/16587327_1399560603439422_4787736195158722183_o.jpg?oh=86ba759ae6da27ba9b42c85fbc5b7a44&oe=5924F606" if image_url is None else image_url,
        buttons=[{
            'type'                 : "web_url",
            'url'                  : "http://gamebots.chat/paypal/{fb_psid}/{price}".format(fb_psid=sender_id, price=price), # if sender_id in Const.ADMIN_FB_PSID else "http://paypal.me/gamebotsc/{price}".format(price=price),
            'title'                : "${price:.2f} Confirm".format(price=price),
            'webview_height_ratio' : "tall"
        }],
        quick_replies=main_menu_quick_reply()
    )


def send_pay_wall(sender_id, item):
    logger.info("send_pay_wall(sender_id=%s, item=%s)" % (sender_id, item))

    send_tracker(fb_psid=sender_id, category="pay-wall", label=item['asset_name'])
    send_text(sender_id, "You have hit the daily win limit for free users. Please purchase credits to continue." if get_session_deposit(sender_id) < 1 else "You have hit the daily win limit for credit users. Please purchase another pack to continue.")
    pay_wall_carousel(sender_id, 3)
    #send_paypal_card(sender_id, item['price'], item['image_url'])


def next_coin_flip_item(sender_id, pay_wall=False):
    logger.info("next_coin_flip_item(sender_id=%s, pay_wall=%s)" % (sender_id, pay_wall))

    row = None
    item_id = None
    deposit = get_session_deposit(sender_id)

    if pay_wall is True or random.uniform(1, 100) >80:# or sender_id in Const.ADMIN_FB_PSID:
        deposit_cycle = cycle([0.00, 1.00, 2.00, 5.00, 15.00])
        next_deposit = deposit_cycle.next()
        while next_deposit <= deposit:
            next_deposit = deposit_cycle.next()
        deposit = next_deposit

    min_price, max_price = price_range_for_deposit(deposit)

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)

            if get_session_bonus(sender_id) is None:
                logger.info("1ST ATTEMPT AT ITEM FOR (%s) =|=|=|=|=|=|=|=|=|=|=|=> %s" % (sender_id, ('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `quantity` > 0 AND `price` >= %s AND `price` < %s AND `type_id` = 1 ORDER BY RAND() LIMIT 1;', (min_price, max_price)),))
                cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `quantity` > 0 AND `price` >= %s AND `price` < %s AND `type_id` = 1 ORDER BY RAND() LIMIT 1;', (min_price, max_price))
                row = cur.fetchone()

                if row is None:
                    logger.info("ROW WAS BLANK!! -- 2nd ATTEMPT AT ITEM =|=|=|=|=|=|=|=|=|=|=|=> %s" % (('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `quantity` > 0 AND `price` >= %s AND `price` < %s AND `type_id` = 1 ORDER BY RAND() LIMIT 1;', (min_price, max_price)),))
                    cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `quantity` > 0 AND `type_id` = 1 ORDER BY RAND() LIMIT 1;' if pay_wall is False and deposit == get_session_deposit(sender_id) else 'SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `quantity` > 0 AND `type_id` = 1 ORDER BY `price` DESC LIMIT 1;')
                    row = cur.fetchone()

            else:
                cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `quantity` > 0 AND `type_id` = 3 ORDER BY RAND() LIMIT 1;')
                row = cur.fetchone()

            if row is not None:
                item_id = row['id']
                set_session_item(sender_id, item_id)


    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return row


def coin_flip_element(sender_id, pay_wall=False, share=False):
    logger.info("coin_flip_element(sender_id=%s, pay_wall=%s, share=%s)" % (sender_id, pay_wall, share))

    element = None
    row = next_coin_flip_item(sender_id, pay_wall)
    if row is not None:
        item_id = row['id']
        set_session_item(sender_id, item_id)

        if pay_wall is False:
            element = {
                'title'    : row['asset_name'].encode('utf8'),
                'subtitle' : "${price:.2f}".format(price=row['price']) if sender_id == "1298454546880273" else "" if pay_wall is False else "Requires ${price:.2f} deposit".format(price=deposit_amount_for_price(row['price'])),
                #'subtitle' : "" if pay_wall is False else "Requires ${price:.2f} deposit".format(price=deposit_amount_for_price(row['price'])),
                'image_url': row['image_url'],
                'item_url' : None,
                'buttons'  : [{
                    'type'   : "postback",
                    'payload': "FLIP_COIN-{item_id}".format(item_id=item_id),
                    'title'  : "Flip Coin"
                }, {
                    'type'   : "postback",
                    'payload': "INVITE",
                    'title'  : "Share"
                }]
            }

        else:
            image_url = ""
            if deposit_amount_for_price(row['price']) == 1:
                image_url = "https://i.imgur.com/KrObpgY.png"

            elif deposit_amount_for_price(row['price']) == 2:
                image_url = "https://i.imgur.com/SFCsAGx.png"

            elif deposit_amount_for_price(row['price']) == 5:
                image_url = "https://i.imgur.com/IDdqOWO.png"

            elif deposit_amount_for_price(row['price']) == 10:
                image_url = "https://i.imgur.com/9s1JeqD.png"


            element = {
                'title'    : "Flip ${price:.2f} Dollar Items".format(price=deposit_amount_for_price(row['price'])),
                'subtitle' : "Buy Now to Win",
                'image_url': image_url,
                'item_url' : None,
                'buttons'  : []
            }

            graph = fb_graph_user(sender_id)
            if graph is not None and graph['is_payment_enabled'] is True:
                element['buttons'].append(buy_credits_button(sender_id, item_id, deposit_amount_for_price(row['price'])))

            element['buttons'].append({
                'type'                : "web_url",
                'url'                 : "http://gamebots.chat/paypal/{fb_psid}/{price}".format(fb_psid=sender_id, price=deposit_amount_for_price(row['price'])),  # if sender_id in Const.ADMIN_FB_PSID else "http://paypal.me/gamebotsc/{price}".format(price=price),
                'title'               : "Pay with Paypal",
                'webview_height_ratio': "tall"
            })

            element['buttons'].append({
                'type'   : "postback",
                'payload': "POINTS-{price}".format(price=deposit_amount_for_price(row['price'])),
                'title'  : "{points} Points".format(points=locale.format('%d', (deposit_amount_for_price(row['price']) * 20000), grouping=True))
            })

    return element


def coin_flip_prep(sender_id, deposit=0, item_id=None, interval=12):
    logger.info("coin_flip_prep(sender_id=%s, deposit=%s, item_id=%s, interval=%s)" % (sender_id, deposit, item_id, interval))

    item = get_item_details(item_id)
    # return False if sender_id in Const.ADMIN_FB_PSID else coin_flip(wins_last_day(sender_id), min(max(get_session_loss_streak(sender_id), 1), int(Const.MAX_LOSSING_STREAK)), deposit, item['price'], item['quantity'], all_available_quantity())
    return coin_flip(wins_last_day(sender_id), min(max(get_session_loss_streak(sender_id), 1), int(Const.MAX_LOSSING_STREAK)), deposit, item['price'], item['quantity'], all_available_quantity())


def coin_flip(wins=0, losses=0, deposit=0, item_cost=0.01, quantity=1, total_quantity=1):
    # logger.info("coin_flip(wins=%s, losses=%s, deposit=%s, item_cost=%s, quantity=%s)" % (wins, losses, deposit, item_cost, quantity))]

    probility = (losses * (1.0 / (Const.MAX_LOSSING_STREAK ** 1.1))) + statistics.stdev([min(max(random.expovariate(1.0 / float(wins * 3.0) if wins >= 1 else float(3.0)), 0), 1) for i in range(int(random.gauss(21, 3 + (1 / float(3)))))]) if deposit >= deposit_amount_for_price(item_cost) else 0.00
    # dice_roller = 1 - int(round(random.uniform(1, 6))) / float(6)
    dice_roller = 1 - random.uniform(0, 1)
    outcome = probility * (1.50 if deposit >= 1 else 1) >= dice_roller
    logger.info("[:::::::] wins=%02d, losses=%02d, dep=$%05.2f, cost=$%05.2f, quant=%03d, tot_quant=%03d [::::] FLIP-CHANCE --> %5.2f%% // %.2f -[%s]-" % (wins, losses, deposit, item_cost, quantity, total_quantity, probility * 100, dice_roller, ("%s" % (outcome,)[0])))

    return outcome


def coin_flip_results(sender_id, item_id=None):
    logger.info("coin_flip_results(sender_id=%s, item_id=%s)" % (sender_id, item_id))

    send_image(sender_id, Const.FLIP_COIN_START_GIF_URL)
    time.sleep(3.33)

    if item_id is None:
        send_text(sender_id, "Can't find your item! Try flipping for it again")
        default_carousel(sender_id)
        return "OK", 200

    flip_item = None

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)

            cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `quantity`, `price` FROM `flip_items` WHERE `id` = %s LIMIT 1;', (item_id,))
            row = cur.fetchone()
            if row is not None:
                flip_item = {
                    'item_id'    : row['id'],
                    'type_id'    : row['type_id'],
                    'asset_name' : row['asset_name'].encode('utf8'),
                    'game_name'  : row['game_name'],
                    'image_url'  : row['image_url'],
                    'quantity'   : row['quantity'],
                    'price'      : row['price'],
                    'claim_id'   : None,
                    'claim_url'  : None,
                    'pin_code'   : hashlib.md5(str(time.time()).encode()).hexdigest()[-4:].upper()
                }

                if flip_item['type_id'] == 3:
                    cur.execute('UPDATE `bonus_codes` SET `enabled` = 0 WHERE `code` = %s LIMIT 1;', (get_session_bonus(sender_id),))
                    conn.commit()

            else:
                send_text(sender_id, "Looks like that item isn't available anymore, try another one")
                send_carousel(recipient_id=sender_id, elements=[coin_flip_element(sender_id, True)])
                return "OK", 0

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    set_session_bonus(sender_id)

    if coin_flip_prep(sender_id, get_session_deposit(sender_id), item_id) is True:# or sender_id in Const.ADMIN_FB_PSID:
        send_tracker(fb_psid=sender_id, category="win", label=flip_item['asset_name'], value=flip_item['price'])

        payload = {
            'v'  : 1,
            't'  : "event",
            'tid': "UA-79705534-2",
            'cid': hashlib.md5(sender_id.encode()).hexdigest(),
            'ec' : "purchase",
            'ea' : "purchase",
            'el' : flip_item['asset_name'],
            'ev' : flip_item['price']
        }

        c = pycurl.Curl()
        c.setopt(c.URL, Const.GA_TRACKING_URL)
        c.setopt(c.POSTFIELDS, urlencode(payload))
        c.setopt(c.WRITEDATA, StringIO())
        c.perform()
        c.close()


        set_session_loss_streak(sender_id)
        record_coin_flip(sender_id, item_id, True)

        full_name, f_name, l_name = get_session_name(sender_id)
        payload = {
            'channel'     : "#bot-alerts",
            'username'    : "gamebotsc",
            'icon_url'    : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text'        : "Flip Win by *{user}* ({sender_id}):\n_{item_name}_\n{pin_code}".format(user=sender_id if full_name is None else full_name, sender_id=sender_id, item_name=flip_item['asset_name'], pin_code=flip_item['pin_code']),
            'attachments' : [{
                'image_url' : flip_item['image_url']
            }]
        }
        response = requests.post("https://hooks.slack.com/services/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",data={'payload': json.dumps(payload)})

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('INSERT INTO `item_winners` (`fb_id`, `pin`, `item_id`, `item_name`, `added`) VALUES (%s, %s, %s, %s, NOW());', (sender_id, flip_item['pin_code'], flip_item['item_id'], flip_item['asset_name']))

                if sender_id not in Const.ADMIN_FB_PSID:
                    cur.execute('UPDATE `flip_items` SET `quantity` = `quantity` - 1 WHERE `id` = %s AND quantity > 0 LIMIT 1;', (flip_item['item_id'],))

                conn.commit()
                cur.execute('SELECT @@IDENTITY AS `id` FROM `item_winners`;')
                flip_item['claim_id'] = cur.fetchone()['id']

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(sender_id, "You won {item_name}.".format(item_name=flip_item['asset_name']))

        if get_session_trade_url(sender_id) is None:
            set_session_trade_url(sender_id, "_{PENDING}_")
            set_session_state(sender_id, Const.SESSION_STATE_FLIP_TRADE_URL)

        else:
            trade_url = get_session_trade_url(sender_id)
            send_text(
                recipient_id=sender_id,
                message_text="Your Steam Trade URL is set to:\n\n{trade_url}".format(trade_url=trade_url),
                quick_replies=[{
                    'content_type': "text",
                    'title'       : "Confirm",
                    'payload'     : "TRADE_URL_OK"
                }, {
                    'content_type': "text",
                    'title'       : "Edit URL",
                    'payload'     : "TRADE_URL_CHANGE"
                }]
            )

    else:
        send_tracker(fb_psid=sender_id, category="loss", label=flip_item['asset_name'], value=flip_item['price'])
        record_coin_flip(sender_id, item_id, False)
        inc_session_loss_streak(sender_id)

        # send_image(sender_id, Const.FLIP_COIN_LOSE_GIF_URL)
        send_text(
            recipient_id=sender_id,
            message_text="TRY AGAIN! You lost {item_name}.".format(item_name=flip_item['asset_name']),
            quick_replies=coin_flip_quick_replies()
        )
        clear_session_dub(sender_id)



def record_coin_flip(sender_id, item_id, won):
    logger.info("record_coin_flip(sender_id=%s, item_id=%s, won=%s)" % (sender_id, item_id, won))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('INSERT INTO flips (id, fb_psid, item_id, won, added) VALUES (NULL, ?, ?, ?, ?);', (sender_id, item_id, 1 if won is True else 0, int(time.time())))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::record_coin_flip[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('INSERT INTO `fb_flips` (`id`, `fb_psid`, `item_id`, `won`, `added`) VALUES (NULL, %s, %s, %s, NOW());', (sender_id, item_id, 1 if won is True else 0))
            conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


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

    f_name = None
    l_name = None
    full_name = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT f_name, l_name FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            f_name = row['f_name']
            l_name = row['l_name']
            full_name = "%s %s" % (f_name, l_name)

        logger.info("get_session_name=%s" % (full_name,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_name[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return (full_name, f_name, l_name)


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


def get_session_deposit(sender_id, interval=24, remote=False):
    logger.info("get_session_deposit(sender_id=%s, interval=%s, remote=%s)" % (sender_id, interval, remote))

    deposit = 0
    if remote is True:
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('SELECT SUM(`amount`) AS `tot` FROM `fb_purchases` WHERE `fb_psid` = %s AND `added` >= DATE_SUB(NOW(), INTERVAL %s HOUR);', (sender_id, interval))
                row = cur.fetchone()
                deposit = row['tot'] or 0

            logger.info("deposit=%s" % (deposit,))


        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


    else:
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

    return deposit# if sender_id not in Const.ADMIN_FB_PSID else random.choice([0.00, 1.00, 2.00, 5.00, 15.00])


def set_session_deposit(sender_id, amount=1):
    logger.info("set_session_deposit(sender_id=%s, amount=%s)" % (sender_id, amount))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET deposit = ? WHERE fb_psid = ?;', (amount, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_deposit[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def sync_session_deposit(sender_id):
    logger.info("sync_session_deposit(sender_id=%s)" % (sender_id,))
    set_session_deposit(sender_id, get_session_deposit(sender_id, 24, True))


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
    flip_id = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT purchase_id FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            purchase_id = row['purchase_id']
            cur.execute('SELECT flip_id FROM payments WHERE id = ? ORDER BY added DESC LIMIT 1;', (purchase_id,))
            row = cur.fetchone()
            if row is not None:
                flip_id = row['flip_id']


        logger.info("purchase_id=%s, flip_id=" % (purchase_id,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_item[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return (purchase_id, flip_id)


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
            cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `quantity`, `price` FROM `flip_items` WHERE `id` = %s LIMIT 1;', (item_id,))
            row = cur.fetchone()
            if row is not None:
                item = row

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return item


def get_session_loss_streak(sender_id):
    logger.info("get_session_loss_streak(sender_id=%s)" % (sender_id,))

    streak = 0
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT flips FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()
        streak = row['flips'] or 0
        logger.info("streak=%s" % (streak,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_loss_streak[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

        return streak


def inc_session_loss_streak(sender_id, amt=1):
    logger.info("set_session_loss_streak(sender_id=%s, amt=%s)" % (sender_id, amt))
    set_session_loss_streak(sender_id, get_session_loss_streak(sender_id) + amt)


def set_session_loss_streak(sender_id, streak=0):
    logger.info("set_session_loss_streak(sender_id=%s, streak=%s)" % (sender_id, streak))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET flips = ? WHERE fb_psid = ?;', (streak, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_loss_streak[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()



def all_available_quantity():
    logger.info("all_available_quantity()")

    quantity = 0
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT SUM(`quantity`) AS `tot` FROM `flip_items` WHERE `quantity` > 0;')
            row = cur.fetchone()
            quantity = 0 if row is None else row['tot']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    logger.info("quantity=%d" % quantity)
    return quantity


def win_mulitplier(sender_id):
    logger.info("win_mulitplier(sender_id=%s)" % (sender_id,))

    if get_session_deposit(sender_id) < 1:
        return 1

    elif get_session_deposit(sender_id) < 2:
        return 2

    elif get_session_deposit(sender_id) < 5:
        return 3

    elif get_session_deposit(sender_id) < 10:
        return 4


def flips_last_day(sender_id):
    logger.info("flips_last_day(sender_id=%s)" % (sender_id,))

    total_flips = 0
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT COUNT(*) AS `tot` FROM `fb_flips` WHERE `fb_psid` = %s AND `added` >= DATE_SUB(NOW(), INTERVAL 24 HOUR);', (sender_id,))
            row = cur.fetchone()
            total_flips = 0 if row is None else row['tot']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    logger.info("total_flips=%d" % total_flips)
    return total_flips



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
    # logger.info("deposit_amount_for_price(price=%s)" % (price,))

    amount = 0
    if price < 1.00:
        amount = 0

    elif price < 2.00:
        amount = 1

    elif price < 4.00:
        amount = 2

    elif price < 6.00:
        amount = 5

    elif price < 15.00:
        amount = 10

    return amount


def price_range_for_deposit(deposit):
    logger.info("price_range_for_deposit(deposit=%s)" % (deposit,))

    if deposit < 1:
        price = (0.00, 1.00)

    elif deposit < 2:
        price = (1.00, 2.00)

    elif deposit < 5:
        price = (2.00, 6.00)

    elif deposit < 10:
        price = (6.00, 15.00)

    else:
        price = (15.00, 1066.00)

    return price



def valid_bonus_code(sender_id, deeplink=None):
    logger.info("valid_bonus_code(sender_id=%s, deeplink=%s)" % (sender_id, deeplink))

    is_valid = False
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `enabled` FROM `bonus_codes` WHERE `code` = %s AND `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR) LIMIT 1;', (deeplink.split("/")[-1],))
            is_valid = False if cur.fetchone() is None else cur.fetchone()['enabled'] == 1

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return is_valid


def valid_purchase_code(sender_id, deeplink=None):
    logger.info("valid_purchase_code(sender_id=%s, deeplink=%s)" % (sender_id, deeplink))

    is_valid = False
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `fb_purchases` WHERE `charge_id` = %s AND `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR) LIMIT 1;', (deeplink.split("/")[-1],))
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
        send_text(sender_id, "You have opted out of Gamebots & will no longer recieve messages from Gamebots. If you need help visit facebook.com/gamebotsc", opt_out_quick_replies())
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

    full_name, f_name, l_name = get_session_name(sender_id)

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `info`, `image_url`, `price` FROM `fb_products` WHERE `id` = %s LIMIT 1;', (item_id,))
            row = cur.fetchone()

            if row is not None:
                item_name = row['asset_name']

            full_name, f_name, l_name = get_session_name(sender_id)
            cur.execute('INSERT INTO `fb_purchases` (`id`, `fb_psid`, `first_name`, `last_name`, `email`, `item_id`, `amount`, `fb_payment_id`, `provider`, `charge_id`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP());', (sender_id, f_name or "", l_name or "", customer_email, item_id, amount, fb_payment_id, provider, charge_id))
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
        set_session_deposit(sender_id, amount)
        set_session_purchase(sender_id, purchase_id)
        flip_id = get_session_item(sender_id)

        try:
            conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('INSERT INTO payments (id, fb_psid, email, item_id, flip_id, amount, fb_payment_id, provider, charge_id, added) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);', (purchase_id, sender_id, customer_email, item_id, flip_id, amount, fb_payment_id, provider, charge_id, int(time.time())))
            conn.commit()

        except sqlite3.Error as er:
            logger.info("::::::payment[cur.execute] sqlite3.Error - %s" % (er.message,))

        finally:
            if conn:
                conn.close()


    # -- state 10 means purchased, but no trade url yet…
    set_session_state(sender_id, Const.SESSION_STATE_PURCHASED_ITEM)
    payload = {
        'channel'  : "#gamebots-purchases",
        'username' : "gamebotsc",
        'icon_url' : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
        'text': "*{user}* just added ${amount:.2f} in credits.".format(user=sender_id if full_name is None else full_name, amount=float(amount)),
    }
    response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

    time.sleep(3.33)

    min_price, max_price = price_range_for_deposit(amount)
    send_text(sender_id, "You have unlocked 100 Item Flips between ${min_price:.2f} to ${max_price:.2f}. This will last 24 hours.".format(min_price=min_price, max_price=max_price), main_menu_quick_reply())


def item_setup(sender_id, item_id, preview=False):
    logger.info("item_setup(sender_id=%s, item_id=%s, preview=%s)" % (sender_id, item_id, preview))

    if flips_last_day(sender_id) >= Const.MAX_FLIPS_PER_DAY:
        send_text(sender_id, "You have hit the daily flip limit.", main_menu_quick_reply())
        return "OK", 200

    set_session_item(sender_id, item_id)
    item = get_item_details(item_id)
    logger.info("ITEM --> %s", item)

    item = get_item_details(item_id)
    logger.info("ITEM --> %s", item)

    if item is None:
        send_text(sender_id, "Can't find that item! Try flipping again")
        return "OK", 200

    if get_session_bonus(sender_id) is not None:
        coin_flip_results(sender_id, item_id)
        return "OK", 200

    if deposit_amount_for_price(item['price']) < 1:
        if wins_last_day(sender_id) < Const.MAX_TIER_WINS * win_mulitplier(sender_id):
            if preview:
                send_card(
                    recipient_id=sender_id,
                    title=item['asset_name'].encode('utf8'),
                    image_url=item['image_url']
                )
            coin_flip_results(sender_id, item_id)

        else:
            send_pay_wall(sender_id, item)

    else:
        if wins_last_day(sender_id) < Const.MAX_TIER_WINS * win_mulitplier(sender_id):
            if preview:
                send_card(
                    recipient_id=sender_id,
                    title=item['asset_name'].encode('utf8'),
                    image_url=item['image_url']
                )
            coin_flip_results(sender_id, item_id)

        else:
            send_pay_wall(sender_id, item)


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

    time.sleep(random.uniform(1.5, 3.5))

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


                if sender_id == "1395098457218675" or sender_id == "1034583493310197":
                    logger.info("-=- BYPASS-USER -=-")
                    return "OK", 200



                #-- catch all
                if sender_id not in Const.ADMIN_FB_PSID:
                    send_text(sender_id, "Gamebots is currently down for maintenance.")
                    return "OK", 200


                referral = None if 'referral' not in messaging_event else messaging_event['referral']['ref'].encode('ascii', 'ignore')
                if referral is None and 'postback' in messaging_event and 'referral' in messaging_event['postback']:
                    referral = messaging_event['postback']['referral']['ref'].encode('ascii', 'ignore')

                if referral is not None:
                    send_tracker(fb_psid=sender_id, category="referral", label=referral)
                    logger.info("REFERRAL ---> %s", (referral,))
                    if referral.split("/")[-1].startswith("gb"):
                        if valid_purchase_code(sender_id, referral):
                            purchase_code = referral.split("/")[-1]
                            full_name, first_name, last_name = get_session_name(sender_id)
                            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
                            try:
                                with conn:
                                    cur = conn.cursor(mdb.cursors.DictCursor)
                                    cur.execute('UPDATE `fb_purchases` SET `fb_psid` = %s, `first_name` = %s, `last_name` = %s WHERE `charge_id` = %s ORDER BY `added` DESC LIMIT 1;', (sender_id, first_name, last_name, purchase_code))
                                    conn.commit()
                                    cur.execute('SELECT `amount` FROM `fb_purchases` WHERE `charge_id` = %s ORDER BY `added` DESC LIMIT 1;', (purchase_code,))
                                    row = cur.fetchone()
                                    send_text(sender_id, "Your purchase for ${amount:.2f} has been applied!.".format(amount=row['amount']))

                            except mdb.Error, e:
                                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

                            finally:
                                if conn:
                                    conn.close()

                            default_carousel(sender_id)

                    else:
                        if valid_bonus_code(sender_id, referral):
                            set_session_bonus(sender_id, referral.split("/")[-1])

                            row = next_coin_flip_item(sender_id)
                            if row is not None:
                                item_id = row['id']
                                set_session_item(sender_id, item_id)
                                item = get_item_details(item_id)
                                logger.info("ITEM --> %s", item)

                                send_text(sender_id, "You have unlocked a Mystery Flip.")
                                send_card(
                                    recipient_id=sender_id,
                                    title=row['asset_name'].encode('utf8'),
                                    # subtitle=row['price'] if sender_id in Const.ADMIN_FB_PSID else None,
                                    subtitle=None,
                                    image_url=row['image_url'],
                                    buttons=[{
                                        'type'   : "postback",
                                        'payload': "FLIP_COIN-{item_id}".format(item_id=item_id),
                                        'title'  : "Flip Coin"
                                    }, {
                                        'type'   : "postback",
                                        'payload': "MAIN_MENU",
                                        'title'  : "Cancel"
                                    }]
                                )

                            else:
                                send_text(sender_id, "You can only use 1 Mystery Flip per day. Please try again in 24 hours.")
                                default_carousel(sender_id)

                        else:
                            send_text(sender_id, "You have already used this Mystery Flip.")
                            default_carousel(sender_id)

                    return "OK", 200



                # -- insert to log
                write_message_log(sender_id, message_id, { key : messaging_event[key] for key in messaging_event if key != 'timestamp' })
                sync_session_deposit(sender_id)

                if 'payment' in messaging_event: # payment result
                    logger.info("-=- PAYMENT -=-")
                    set_session_state(sender_id, Const.SESSION_STATE_PURCHASED_ITEM)
                    purchase_item(sender_id, messaging_event['payment'])
                    return "OK", 200


                #-- new entry
                if get_session_state(sender_id) == Const.SESSION_STATE_NEW_USER:
                    logger.info("----------=NEW SESSION @(%s)=----------" % (time.strftime('%Y-%m-%d %H:%M:%S')))
                    send_tracker(fb_psid=sender_id, category="sign-up-fb")

                    set_session_state(sender_id)
                    send_text(sender_id, "Welcome to Gamebots. WIN pre-sale games & items with players on Messenger.\n To opt-out of further messaging, type exit, quit, or stop.")
                    send_image(sender_id, "http://i.imgur.com/QHHovfa.gif")
                    default_carousel(sender_id)
                    graph = fb_graph_user(sender_id)
                    if graph is not None:
                        set_session_name(sender_id, graph['first_name'] or "", graph['last_name'] or "")

                #-- existing
                elif get_session_state(sender_id) >= Const.SESSION_STATE_HOME and get_session_state(sender_id) < Const.SESSION_STATE_PURCHASED_ITEM:

                    # if sender_id in Const.ADMIN_FB_PSID:
                    #     for losses in range(Const.MAX_LOSSING_STREAK + 1):
                    #         for wins in range(Const.MAX_TIER_WINS + 1):
                    #             for cost in [0.11 + random.uniform(0.01, 0.10), 0.43 + random.uniform(0.2, 0.13), 0.85 + random.uniform(0.3, 0.11), 1.23 + random.uniform(0.06, 0.15), 2.22 + random.uniform(0.07, 0.10), 3.60 + random.uniform(0.14, 0.18), 4.20 + random.uniform(0.16, 0.19), 5.00 + random.uniform(0.25, 0.30), 7.32 + random.uniform(0.23, 0.57), 9.69 + random.uniform(0.46, 0.91), 13.71 + random.uniform(0.93, 2.10)]:
                    #                 for deposit in [0, 1, 2, 3, 5]:
                    #                     if deposit < deposit_amount_for_price(cost):
                    #                         continue
                    #
                    #                     coin_flip(wins, losses, deposit, cost)

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
        set_session_deposit(fb_psid, int(round(amount)))

        full_name, f_name, l_name = get_session_name(fb_psid)

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('INSERT INTO `fb_purchases` (`id`, `fb_psid`, `first_name`, `last_name`, `amount`, `added`) VALUES (NULL, %s, %s, %s, %s, UTC_TIMESTAMP());', (fb_psid, f_name, l_name, amount))
                conn.commit()

                cur.execute('SELECT @@IDENTITY AS `id` FROM `fb_purchases`;')
                row = cur.fetchone()
                purchase_id = row['id']


        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


        min_price, max_price = price_range_for_deposit(amount)
        send_text(fb_psid, "You have unlocked 100 Item Flips between ${min_price:.2f} to ${max_price:.2f}. This will last 24 hours.".format(min_price=min_price, max_price=max_price), main_menu_quick_reply())
        payload = {
            'channel' : "#gamebots-purchases",
            'username': "gamebotsc",
            'icon_url': "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text': "*{user}* just added ${amount:.2f} in credits.".format(user=fb_psid if full_name is None else full_name, amount=amount),
        }
        response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })

    return "OK", 200


@app.route('/bonus-flip', methods=['POST'])
def bonus_flip():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/bonus-flip'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.BONUS_TOKEN:
        logger.info("TOKEN VALID!")

        if 'bonus_code' in request.form:
            bonus_code = request.form['bonus_code']
            logger.info("bonus_code=%s" % (bonus_code,))

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('SELECT `id` FROM `bonus_codes` WHERE `code` = %s AND `added` > DATE_SUB(UTC_TIMESTAMP(), INTERVAL 24 HOUR) LIMIT 1;', (bonus_code,))
                    if cur.fetchone() is None:
                        cur.execute('INSERT INTO `bonus_codes` (`id`, `code`, `added`) VALUES (NULL, %s, UTC_TIMESTAMP());', (bonus_code,))
                        conn.commit()

                        cur.execute('SELECT @@IDENTITY AS `id` FROM `bonus_codes`;')
                        row = cur.fetchone()

                    else:
                        return "code-exists", 200

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

    return "OK", 200


@app.route('/points-purchase', methods=['POST'])
def points_purchase():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/points-purchase'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.POINTS_TOKEN:
        logger.info("TOKEN VALID!")

        if 'purchase_code' in request.form and 'amount' in request.form:
            purchase_code = request.form['purchase_code']
            amount = request.form['amount']
            logger.info("amount=%s" % (amount,))

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('SELECT `id` FROM `fb_purchases` WHERE `charge_id` = %s AND `added` > DATE_SUB(UTC_TIMESTAMP(), INTERVAL 24 HOUR) LIMIT 1;', (purchase_code,))
                    # if cur.fetchone() is None:
                    cur.execute('INSERT INTO `fb_purchases` (`id`, `amount`, `charge_id`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());', (request.form['amount'], purchase_code,))
                    conn.commit()

                    cur.execute('SELECT @@IDENTITY AS `id` FROM `fb_purchases`;')
                    row = cur.fetchone()

                    # else:
                    #     return "code-exists", 200

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

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
        purchase_id, flip_id = get_session_purchase(sender_id)

        if get_session_state(sender_id) == Const.SESSION_STATE_PURCHASED_TRADE_URL:
            send_text(sender_id, "Steam Trade URL is set to: {url}".format(url=url), quick_replies=submit_quick_replies())


    elif action == Const.TRADE_URL_FLIP_ITEM:
        if get_session_state(sender_id) == Const.SESSION_STATE_FLIP_TRADE_URL:
            send_text(sender_id, "Your Steam Trade URL is set to:\n\n{url}".format(url=url), quick_replies=submit_quick_replies(["Confirm", "Enter URL"]))





def handle_payload(sender_id, payload_type, payload):
    logger.info("handle_payload(sender_id=%s, payload_type=%s, payload=%s)" % (sender_id, payload_type, payload))

    if payload == "MAIN_MENU":
        # send_tracker("todays-item", sender_id, "")
        clear_session_dub(sender_id)
        default_carousel(sender_id)


    elif payload == "WELCOME_MESSAGE":
        logger.info("----------=NEW SESSION @(%s)=----------" % (time.strftime('%Y-%m-%d %H:%M:%S')))
        # send_tracker("signup-fb", sender_id, "")
        default_carousel(sender_id)


    elif payload == "NEXT_ITEM":
        send_tracker(fb_psid=sender_id, category="next-item")
        row = next_coin_flip_item(sender_id)

        if row is None:
            send_text(sender_id, "Can't find that item! Try flipping again")
            default_carousel(sender_id)
            return "OK", 200

        item_id = row['id']
        item_setup(sender_id, item_id, True)


    elif re.search('FLIP_COIN-(\d+)', payload) is not None:
        send_tracker(fb_psid=sender_id, category="flip-coin", label=re.match(r'FLIP_COIN-(?P<item_id>\d+)', payload).group('item_id'))
        item_id = re.match(r'FLIP_COIN-(?P<item_id>\d+)', payload).group('item_id')
        if item_id is not None:
            item_setup(sender_id, item_id, False)

        else:
            send_text(sender_id, "Can't find that item! Try flipping again")
            return "OK", 200


    elif re.search('POINTS-(\d+)', payload) is not None:
        price = int(re.match(r'POINTS-(?P<price>\d+)', payload).group('price'))
        send_text(sender_id, "Tap below to purchase the item in Lmon8 using Points.")

        image_url = ""
        if price == 1:
            image_url = "https://i.imgur.com/j3zxHam.png"

        elif price == 2:
            image_url = "https://i.imgur.com/jdqSWbe.png"

        elif price == 5:
            image_url = "https://i.imgur.com/KDngY5d.png"

        elif price == 10:
            image_url = "https://i.imgur.com/DAPjlMQ.png"

        send_card(
            recipient_id=sender_id,
            title="Share Gamebots",
            image_url=image_url,
            card_url="http://m.me/lmon8?ref=GamebotsDeposit{price}".format(price=price),
            buttons=[{
                'type'                 : "web_url",
                'url'                  : "http://m.me/lmon8?ref=GamebotsDeposit{price}".format(price=price),  # if sender_id in Const.ADMIN_FB_PSID else "http://paypal.me/gamebotsc/{price}".format(price=price),
                'title'                : "{points} Points".format(points=locale.format('%d', (price * 20000), grouping=True))
            }, {
                'type' : "element_share"
            }],
            quick_replies=main_menu_quick_reply()
        )


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
        send_text(sender_id, "For support please direct message us on Twitter.com/gamebotsc")

        full_name, f_name, l_name = get_session_name(sender_id)

        payload = {
            'channel'  : "#pre",
            'username' : "gamebotsc",
            'icon_url' : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text'     : "*{user}* needs help…".format(user=sender_id if full_name is None else full_name),
        }
        response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})
        default_carousel(sender_id)

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

        # set_session_state(sender_id, Const.SESSION_STATE_FLIP_LMON8_URL)

        trade_url = get_session_trade_url(sender_id)
        send_tracker(fb_psid=sender_id, category="trade-url-set")

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

        full_name, f_name, l_name = get_session_name(sender_id)
        payload = {
            'channel'  : "#bot-alerts",
            'username ': "gamebotsc",
            'icon_url' : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text'     : "Trade URL set for *{user}*:\n{trade_url}".format(user=sender_id if full_name is None else full_name, trade_url=trade_url)
        }
        response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})
        send_text(sender_id, "Please wait for your free item to be verified. Note non credit users must wait 24 hours for item to transfer.")

        set_session_state(sender_id)
        default_carousel(sender_id)


    elif payload == "TRADE_URL_CHANGE":
        set_session_trade_url(sender_id, "_{PENDING}_")
        set_session_state(sender_id, Const.SESSION_STATE_FLIP_TRADE_URL)
        send_text(sender_id, "Enter your Steam Trade URL now.")

    elif payload == "SUBMIT_YES":
        if get_session_state(sender_id) == Const.SESSION_STATE_FLIP_TRADE_URL:
            trade_url = get_session_trade_url(sender_id)
            send_tracker(fb_psid=sender_id, category="trade-url-set")

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

            full_name, f_name, l_name = get_session_name(sender_id)
            payload = {
                'channel'   : "#bot-alerts",
                'username ' : "gamebotsc",
                'icon_url'  : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
                'text'      : "Trade URL set for *{user}*:\n{trade_url}".format(user=sender_id if full_name is None else full_name, trade_url=trade_url)
            }
            response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})
            send_text(sender_id, "Please wait for your Trade to clear, non credit users must wait 24 hours for trade to complete.")

            set_session_state(sender_id)
            default_carousel(sender_id)

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

        elif get_session_state(sender_id) == Const.SESSION_STATE_PURCHASED_TRADE_URL:
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


    elif payload == "CANCEL":
        return "OK", 200

    else:
        default_carousel(sender_id)
    return "OK", 200


def recieved_text_reply(sender_id, message_text):
    logger.info("recieved_text_reply(sender_id=%s, message_text=%s)" % (sender_id, message_text))

    if message_text.lower() in Const.OPT_OUT_REPLIES.split("|"):
        logger.info("-=- ENDING HELP -=- (%s)" % (time.strftime('%Y-%m-%d %H:%M:%S')))
        toggle_opt_out(sender_id, True)

    elif message_text.lower() in Const.MAIN_MENU_REPLIES.split("|"):
        clear_session_dub(sender_id)
        default_carousel(sender_id)

    elif message_text.lower() in Const.GIVEAWAY_REPLIES.split("|"):
        queue_index = 0
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('INSERT INTO queue_indexer (id, fb_psid, added) VALUES (NULL, ?, ?);', (sender_id, int(time.time())))
            conn.commit()
            queue_index += cur.lastrowid

        except sqlite3.Error as er:
            logger.info("::::::queue_indexer[cur.execute] sqlite3.Error - %s" % (er.message,))

        finally:
            if conn:
                conn.close()

        #send_text(sender_id, "You are the {queue} user in line.".format(queue=locale.format('%d', queue_index, grouping=True)))
        #send_text(sender_id, "Follow instructions to complete your entry:\n\n1. OPEN 3 free games: taps.io/skins\n\n2. GET m.me/lmon8\n\n3. CREATE an auto shop off the main menu\n\n4. Upload screenshots to m.me/gamebotsc\n\nSupport: @gamebotsc", main_menu_quick_reply())
        send_text(sender_id, "You have completed a virtual item giveaway entry. User {queue} of {total}. You will be messaged here when the winner is selected.".format(queue=locale.format('%d', queue_index, grouping=True), total=locale.format('%d', queue_index * 2.125, grouping=True)), main_menu_quick_reply())

    elif message_text.lower() in Const.UPLOAD_REPLIES.split("|"):
        send_text(sender_id, "Upload screenshots now.")

    elif message_text.lower() in Const.APPNEXT_REPLIES.split("|"):
        send_text(sender_id, "Instructions…\n\n1. GO: taps.io/skins\n\n2. OPEN & Screenshot each free game or app you install.\n\n3. SEND screenshots for proof on Twitter.com/gamebotsc\n\nEvery free game or app you install increases your chances of winning.", main_menu_quick_reply())

    elif message_text.lower() in Const.MODERATOR_REPLIES.split("|"):
        send_text(sender_id, "You have signed up to be a mod. We will send you details shortly.", main_menu_quick_reply())

    elif message_text.lower() in Const.FBPSID_REPLIES.split("|"):
        send_text(sender_id, "Your ID is:")
        send_text(sender_id, sender_id, main_menu_quick_reply())

    elif message_text.lower() in Const.TASK_REPLIES.split("|"):
        send_text(sender_id, "Mod tasks:\n\n1. 100 PTS: Invite a friend to join & txt Lmon8 your referral ID.\n2. 50 PTS: Add \"mod for @gamebotsc\" to your Twitter & Steam Profile. \n3. 1000 PTS: Become a reseller and sell an item on Lmon8. Sale has to complete. \n4. 100 PTS: Like & 5 star review Lmon8 on Facebook. fb.com/lmon8\n5. 100 PTS: Like & 5 star review Gamebots on Facebook. fb.com/gamebotsc \n6. 25 PTS: Invite friends to @lmon8 and @gamebotsc in Twitter. Have each invite @reply us your Lmon8 referral id.\n7. 500 PTS: Install 10 free games taps.io/skins\n8: 50 PTS: add your referral id to your Twitter and Steam Profile.")

    elif message_text.lower() == ":payment":
        amount = get_session_deposit(sender_id)
        set_session_deposit(sender_id, -amount)

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('UPDATE `fb_purchases` SET `amount` = 0 WHERE `fb_psid` = %s;', (sender_id,))
                conn.commit()

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(sender_id, "Cleared payments!")


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

    if attachment_type == Const.PAYLOAD_ATTACHMENT_IMAGE.split("-")[-1] and re.search('^.*t39\.1997\-6.*$', attachment['url']) is None:
        full_name, f_name, l_name = get_session_name(sender_id)
        payload = {
            'channel'     : "#mods",
            'username '   : "gamebotsc",
            'icon_url'    : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text'        : "Image upload from *{user}* _{fb_psid}_:\n{image_url}".format(user=sender_id if full_name is None else full_name, fb_psid=sender_id, image_url=attachment['url']),
            'attachments' : [{
                'image_url' : attachment['url']
            }]
        }
        response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

        #send_text(sender_id, "You have won 100 skin pts! Every 1000 skin pts you get a MAC 10 Neon Rider!\n\nTerms: your pts will be rewarded once the screenshot you upload is verified.", main_menu_quick_reply())
        send_text(sender_id, "Terms: your pts will be rewarded once the screenshot you upload is verified.", main_menu_quick_reply())

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
