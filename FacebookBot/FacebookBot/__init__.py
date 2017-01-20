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
import threading
import time

import MySQLdb as mdb
import requests

from datetime import datetime
from flask import Flask, request
from gevent import monkey
from urllib2 import quote

import const as Const

monkey.patch_all()
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
Const.ACCESS_TOKEN = "EAAXFDiMELKsBADVw92wLSx3GMEpeYcMqgCoFsyw4oZCw2LyMO4MIDJljsVvh4ZAsBp5A9476i7knpaJZAiPpmVnFrRKkJ7DCdWamXJeF0HRKYDMNbJYImDoOmD3B0WmIZBEZAl3jaWusenO6jmUBg1NOEHdGp7ZAV09JxsBUBpVQZDZD"

Const.MAX_IGNORES = 4


# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


def send_tracker(category, action, label):
    logger.info("send_tracker(category={category}, action={action}, label={label})".format(category=category, action=action, label=label))

    t1 = threading.Thread(
        target=async_tracker,
        name="bot_tracker-1",
        kwargs={
            'url'     : "http://beta.modd.live/api/bot_tracker.php",
            'payload' : {
                'src'      : "facebook",
                'category' : category,
                'action'   : category,
                'label'    : action,
                'value'    : "",
                'cid'      : hashlib.md5(action.encode()).hexdigest()
            }
        }
    )

    t2 = threading.Thread(
        target=async_tracker,
        name="bot_tracker-2",
        kwargs={
            'url'     : "http://beta.modd.live/api/bot_tracker.php",
            'payload' : {
                'src'      : "facebook",
                'category' : "user-message",
                'action'   : "user-message",
                'label'    : action,
                'value'    : "",
                'cid'      : hashlib.md5(action.encode()).hexdigest()
            }
        }
    )

    t1.setDaemon(True)
    t1.start()

    t2.setDaemon(True)
    t2.start()

    return True


def async_tracker(url, payload):
    #logger.info("async_tracker(url={url}, payload={payload}".format(url=url, payload=payload))

    response = requests.get(url, params=payload)
    if response.status_code != 200:
        logger.info("TRACKER ERROR:%s" % (response.text))


def write_message_log(sender_id, message_id, message_txt):
    logger.info("write_message_log(sender_id={sender_id}, message_id={message_id}, message_txt={message_txt})".format(sender_id=sender_id, message_id=message_id, message_txt=message_txt))

    try:
        conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME)
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('INSERT IGNORE INTO `fbbot_logs` (`id`, `message_id`, `chat_id`, `body`) VALUES (NULL, "{message_id}", "{sender_id}", "{message_txt}")'.format(message_id=message_id, sender_id=sender_id, message_txt=message_txt))

    except mdb.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()


def default_carousel(sender_id):
    logger.info("default_carousel(sender_id={sender_id})".format(sender_id=sender_id))

    if coin_flip_element(sender_id) is None:
        elements = [next_product_element(sender_id)]

    else:
        elements = [
            coin_flip_element(sender_id),
            next_product_element(sender_id)
        ]

    send_carousel(
        recipient_id=sender_id,
        elements=elements,
        quick_replies=[
            {
                'content_type': "text",
                'title': "Invite Friends",
                'payload': "INVITE"
            }, {
                'content_type': "text",
                'title': "Support",
                'payload': "SUPPORT"
            }
        ]
    )

def payment_carousel(sender_id):
    logger.info("payment_carousel(sender_id={sender_id})".format(sender_id=sender_id))

    elements = [product_buy_element(sender_id)]

    send_carousel(
        recipient_id=sender_id,
        elements=elements,
        quick_replies=[
            {
                'content_type': "text",
                'title': "Invite Friends",
                'payload': "INVITE"
            }, {
                'content_type': "text",
                'title': "Support",
                'payload': "SUPPORT"
            }
        ]
    )


def next_product_element(sender_id):
    logger.info("next_product_element(sender_id={sender_id})".format(sender_id=sender_id))

    try:
        conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `info`, `image_url`, `video_url`, `price`, `added` FROM `fb_products` WHERE `enabled` = 1 ORDER BY RAND() LIMIT 1;')
            row = cur.fetchone()

            td = datetime.now() - row['added']
            m, s = divmod(td.seconds, 60)
            h, m = divmod(m, 60)

            element = {
                'title': "Reserve {item_name} for ${price}.".format(item_name=row['name'].encode('utf8'), price=row['price']),
                'subtitle': "",
                'image_url': row['image_url'],
                'item_url': "http://prekey.co/stripe.php?from_user={recipient_id}&item_id={item_id}".format(recipient_id=sender_id, item_id=row['id']),
                'buttons': [{
                    'type': "web_url",
                    'url': "http://prekey.co/stripe.php?from_user={recipient_id}&item_id={item_id}".format(recipient_id=sender_id, item_id=row['id']),
                    'title': "Tap to Reserve"
                }]
            }

    except mdb.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()

    return element

def product_buy_element(sender_id):
    logger.info("product_buy_element(sender_id={sender_id})".format(sender_id=sender_id))

    try:
        conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `info`, `image_url`, `video_url`, `price`, `added` FROM `fb_products` WHERE `enabled` = 1 LIMIT 1;')
            row = cur.fetchone()

            td = datetime.now() - row['added']
            m, s = divmod(td.seconds, 60)
            h, m = divmod(m, 60)


            element = {
                'title': "Reserve {item_name} for ${price}.".format(item_name=row['name'].encode('utf8'), price=row['price']),
                'subtitle': "",
                'image_url': row['image_url'],
                'item_url': "http://prekey.co/stripe.php?from_user={recipient_id}&item_id={item_id}".format(recipient_id=sender_id, item_id=row[0]),
                'buttons': [{
                    'type':"payment",
                    'title':"Buy",
                    'payload':"PURCHASE_{item_id}".format(item_id=row['id']),
                    'payment_summary':{
                        'currency':"USD",
                        'payment_type':"FIXED_AMOUNT",
                        "is_test_payment" : True,
                        'merchant_name':"GameBots",
                        'requested_user_info':[
                            # "shipping_address",
                            "contact_name",
                            # "contact_phone",
                            "contact_email"
                        ],
                        'price_list':[{
                            'label':"Total",
                            'amount':row['price']
                        }]
                    }
                }]
            }

    except mdb.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()


    return element


def coin_flip_element(sender_id, standalone=False):
    logger.info("coin_flip_element(sender_id={sender_id})".format(sender_id=sender_id))

    try:
        conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `game_name`, `sponsor`, `image_url`, `trade_url`, `win_video_url`, `lose_video_url` FROM `flip_inventory` WHERE `quantity` > 0 AND `type` = 1 ORDER BY RAND() LIMIT 1;')
            row = cur.fetchone()

            if row is not None:
                set_session_item(sender_id, row['id'])

                element = {
                    'title': "{item_name}".format(item_name=row['name'].encode('utf8')),
                    'subtitle': "",
                    'image_url': row['image_url'],
                    'item_url': row['trade_url'],
                    'buttons': [{
                        'type': "postback",
                        'payload': "FLIP_COIN",
                        'title': "Flip Coin"
                    }]
                }

                if standalone is True:
                    element['buttons'].append({
                        'type': "postback",
                        'payload': "NO_THANKS",
                        'title': "No Thanks"
                    })

            else:
                return None

    except mdb.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()

    return element

def coin_flip_quick_replies():
    return [
        {
            'content_type': "text",
            'title': "Next Item",
            'payload': "NEXT_ITEM"
        }, {
            'content_type': "text",
            'title': "No Thanks",
            'payload': "NO_THANKS"
        }
    ]

def coin_flip_results(sender_id, item_id):
    logger.info("coin_flip_results(sender_id={sender_id}, item_id={item_id})".format(sender_id=sender_id, item_id=item_id))

    send_image(sender_id, "http://i.imgur.com/C6Pgtf4.gif")

    try:
        conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `game_name`, `image_url`, `trade_url`, `win_video_url`, `lose_video_url` FROM `flip_inventory` WHERE `id` = {item_id};'.format(item_id=item_id))
            row = cur.fetchone()

    except mdb.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()

    if random.uniform(0, 1) <= 0.30 or sender_id == "1219553058088713":
        pin_code = hashlib.md5(str(time.time()).encode()).hexdigest()[-4:].upper()

        if sender_id != "1219553058088713":
            conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute("INSERT INTO `item_winners` (`fb_id`, `pin_code`, `item_name`, `added`) VALUES (%s, %s, %s, NOW())", (sender_id, pin_code, row['name']))
                    cur.execute("UPDATE `flip_inventory` SET `quantity` = `quantity` - 1 WHERE `id` = {item_id} LIMIT 1;".format(item_id=row['id']))
                    conn.commit()
                    cur.close()

            except mdb.Error, e:
                logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

            finally:
                if conn:
                    conn.close()

        payload = {
            'channel': "#bot-alerts",
            'username': "gamebotsc",
            'icon_url': "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text': "Flip Win by {sender_id}:\n{item_name}\n{pin_code}".format(sender_id=sender_id, item_name=row['name'], pin_code=pin_code),
            'attachments': [{
                'image_url': row['image_url']
            }]
        }
        response = requests.post("https://hooks.slack.com/services/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",data={'payload': json.dumps(payload)})

        send_image(sender_id, row['win_video_url'])
        send_card(
            recipient_id=sender_id,
            title="{item_name}".format(item_name=row['name'].encode('utf8')),
            image_url=row['image_url'],
            card_url=row['trade_url'],
            buttons=[
                {
                    'type': "element_share"
                }, {
                    'type': "web_url",
                    'url': row['trade_url'],
                    'title': "Trade"
                }
            ],
            quick_replies=coin_flip_quick_replies()
        )

        send_text(
            recipient_id=sender_id,
            message_text="WINNER! You won {item_name} - {pin_code} from {game_name}.\n\nInstructions:\n1. Share with 3 Friends.\n2. Get Gamebots on Kik: kik.me/game.bots\n3. Tap the item image above to pick your skin\n4. When you submit trade add the following comment for security: {pin_code}".format(item_name=row['name'].encode('utf8'), pin_code=pin_code, game_name=row['game_name']),
            quick_replies=coin_flip_quick_replies()
        )

    else:
        send_image(sender_id, row['lose_video_url'])
        send_text(
            recipient_id=sender_id,
            message_text="TRY AGAIN! You lost {item_name} from {game_name}.\n\nIncrease your chances by getting Gamebots on Messenger.\nm.me/gamebotsc".format(item_name=row['name'].encode('utf8'), game_name=row['game_name']),
            quick_replies=coin_flip_quick_replies()
        )


def get_session_state(sender_id):
    logger.info("get_session_state(sender_id={sender_id})".format(sender_id=sender_id))
    state = 0

    try:
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        cur = conn.cursor()
        cur.execute('SELECT state FROM sessions WHERE fb_psid = "{fb_psid}" ORDER BY added DESC LIMIT 1;'.format(fb_psid=sender_id))
        row = cur.fetchone()

        if row is not None:
            state = row[0]

        conn.close()
        logger.info("state={state}".format(state=state))

    except sqlite3.Error as er:
        logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

    return state

def set_session_state(sender_id, state):
    logger.info("set_session_state(sender_id={sender_id}, state={state})".format(sender_id=sender_id, state=state))

    current_state = get_session_state(sender_id)

    try:
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        cur = conn.cursor()

        if current_state == 0:
            cur.execute('INSERT INTO sessions (id, fb_psid, state, added) VALUES (NULL, ?, ?, ?);', (sender_id, state, int(time.time())))

        else:
            cur.execute('UPDATE sessions SET state = {state} WHERE fb_psid = "{fb_psid}";'.format(state=state, fb_psid=sender_id))

        conn.commit()
        conn.close()

    except sqlite3.Error as er:
        logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

def get_session_item(sender_id):
    logger.info("get_session_item(sender_id={sender_id})".format(sender_id=sender_id))
    item_id = 0

    try:
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        cur = conn.cursor()
        cur.execute('SELECT flip_id FROM sessions WHERE fb_psid = "{fb_psid}" LIMIT 1;'.format(fb_psid=sender_id))
        row = cur.fetchone()

        if row is not None:
            item_id = row[0]

        conn.close()
        logger.info("item_id={item_id}".format(item_id=item_id))

    except sqlite3.Error as er:
        logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

    return item_id


def set_session_item(sender_id, item_id):
    logger.info("set_session_item(sender_id={sender_id}, item_id={item_id})".format(sender_id=sender_id, item_id=item_id))

    try:
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET flip_id = {flip_id} WHERE fb_psid = "{fb_psid}";'.format(flip_id=item_id, fb_psid=sender_id))
        conn.commit()
        conn.close()

    except sqlite3.Error as er:
        logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))


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
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")

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


                #-- new entry
                if get_session_state(sender_id) == 0:
                    logger.info("----------=NEW SESSION @({timestamp})=----------".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
                    send_tracker("signup-fb", sender_id, "")

                    set_session_state(sender_id, 1)
                    send_text(sender_id, "Welcome to Gamebots. WIN pre-sale games & items with players on Messenger.")
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

                        elif messaging_event['postback']['payload'] == "NO_THANKS":
                            send_tracker("no-thanks", sender_id, "")
                            default_carousel(sender_id)

                        elif messaging_event['postback']['payload'] == "MAIN_MENU":
                            send_tracker("main-menu", sender_id, "")
                            default_carousel(sender_id)

                        elif messaging_event['postback']['payload'] == "FLIP_COIN":
                            send_tracker("flip-item", sender_id, "")
                            coin_flip_results(sender_id, get_session_item(sender_id))

                        elif re.search('FLIP_COIN-(\d+)', messaging_event['postback']['payload']) is not None:
                            send_tracker("flip-item", sender_id, "")
                            coin_flip_results(sender_id, re.match(r'FLIP_COIN-(\d+)', messaging_event['postback']['payload']).group(1))

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
                                    image_url="http://i.imgur.com/C6Pgtf4.gif",
                                    card_url="http://m.me/gamebotsc",
                                    buttons=[{'type': "element_share"}],
                                    quick_replies=[{
                                        'content_type': "text",
                                        'title': "Main Menu",
                                        'payload': "MAIN_MENU"
                                    }]
                                )

                            elif quick_reply == "SUPPORT":
                                send_text(sender_id, "If you need help message kik.me/support.gamebots.1")
                                default_carousel(sender_id)

                                payload = {
                                    'channel': "#pre",
                                    'username': "gamebotsc",
                                    'icon_url': "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
                                    'text': "*{sender_id}* needs help…".format(sender_id=sender_id),
                                }
                                response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

                            elif quick_reply == "NEXT_ITEM":
                                send_tracker("next-item", sender_id, "")
                                send_carousel(recipient_id=sender_id, elements=[coin_flip_element(sender_id, True)])

                            elif quick_reply == "NO_THANKS":
                                send_tracker("no-thanks", sender_id, "")
                                default_carousel(sender_id)

                            else:
                                default_carousel(sender_id)

                            return "OK", 200


                        # ------- TYPED TEXT MESSAGE
                        if 'text' in message:
                            message_text = message['text']

                            # -- typed '!end' / 'cancel' / 'quit'
                            if message_text.lower() == "!end" or message_text.lower() == "cancel" or message_text.lower() == "quit":
                                logger.info("-=- ENDING HELP -=- ({timestamp})".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
                                send_text(sender_id, "If you need help message kik.me/support.gamebots.1")

                            elif message_text == "/:item_purchase:/":
                                send_text(sender_id, "Test Payment Card:")
                                payment_carousel(sender_id)

                            else:
                                send_text(sender_id, "Welcome to Gamebots. WIN pre-sale games & items with players on Messenger.")
                                default_carousel(sender_id)

                            return "OK", 200

    return "OK", 200


def send_text(recipient_id, message_text, quick_replies=None):
    logger.info("send_text(recipient_id={recipient}, message_text={text}, quick_replies={quick_replies})".format(recipient=recipient_id, text=message_text, quick_replies=quick_replies))

    data = {
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'text': message_text
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))


def send_card(recipient_id, title, image_url, card_url, subtitle="", buttons=None, quick_replies=None):
    logger.info("send_card(recipient_id={recipient}, title={title}, image_url={image_url}, card_url={card_url}, subtitle={subtitle}, buttons={buttons}, quick_replies={quick_replies})".format(recipient=recipient_id, title=title, image_url=image_url, card_url=card_url, subtitle=subtitle, buttons=buttons, quick_replies=quick_replies))

    data = {
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'attachment': {
                'type': "template",
                'payload': {
                    'template_type': "generic",
                    'elements': [
                        {
                            'title': title,
                            'item_url': card_url,
                            'image_url': image_url,
                            'subtitle': subtitle,
                            'buttons': buttons
                        }
                    ]
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
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'attachment': {
                'type': "template",
                'payload': {
                    'template_type': "generic",
                    'elements': elements
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
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'attachment': {
                'type': "image",
                'payload': {
                    'url': url
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
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'attachment': {
                'type': "video",
                'payload': {
                    'url': url
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))


def send_message(payload):
    logger.info("send_message(payload={payload})".format(payload=payload))

    response = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN),data=payload, headers={'Content-Type': "application/json"})
    logger.info("GRAPH RESPONSE ({code}): {result}".format(code=response.status_code, result=response.text))

    return True

def async_send_message(payload):
    #logger.info("async_send_message(payload={payload})".format(payload=payload))

    response = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN),data=payload, headers={'Content-Type': "application/json"})
    logger.info("GRAPH RESPONSE ({code}): {result}".format(code=response.status_code, result=response.text))


if __name__ == '__main__':
    app.run(debug=True)
