#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import hashlib
import json
import MySQLdb as mdb
import json
import time
import requests
import urllib2
import logging
import gevent
import random
import sqlite3
import threading

import pycurl

from datetime import date, datetime
from urllib2 import quote
from gevent import monkey;

monkey.patch_all()
reload(sys)
sys.setdefaultencoding('utf8')

import const as Const

from flask import Flask, request

app = Flask(__name__)

gevent.monkey.patch_all()

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
                'action'   : action,
                'label'    : label,
                'value'    : "",
                'cid'      : hashlib.md5(label.encode()).hexdigest()
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
                'action'   : action,
                'label'    : label,
                'value'    : "",
                'cid'      : hashlib.md5(label.encode()).hexdigest()
            }
        }
    )

    t1.start()
    t2.start()

    # payload = {
    #     'src': "facebook",
    #     'category': category,
    #     'action': action,
    #     'label': label
    # }
    # response = requests.get("http://beta.modd.live/api/bot_tracker.php", data=payload)
    #
    # payload = {
    #     'src': "facebook",
    #     'category': "user-message",
    #     'action': action,
    #     'label': label
    # }
    # response = requests.get("http://beta.modd.live/api/bot_tracker.php", data=payload)

    return True


def async_tracker(url, payload):
    #logger.info("async_tracker(url={url}, payload={payload}".format(url=url, payload=payload))

    response = requests.get(url, params=payload)
    if response.status_code != 200:
        logger.info("TRACKER ERROR:%s" % (response.text))


def slack_send(topic_name, message_txt, from_user="game.bots"):
    logger.info("slack_send(topic_name={topic_name}, message_txt={message_txt}, from_user=%{from_user})".format(topic_name=topic_name, message_txt=message_txt, from_user=from_user))

    _obj = fetch_slack_webhook(topic_name)
    print "SLACK_OBJ:%s" % (_obj)

    payload = {
        'channel': "#{channel_name}".format(channel_name=_obj['channel_name']),
        'username': from_user,
        'icon_url': "http://i.imgur.com/08JS1F5.jpg",
        'text': message_txt,
    }
    response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})
    return


def write_message_log(sender_id, message_id, message_txt):
    logger.info("write_message_log(sender_id={sender_id}, message_id={message_id}, message_txt={message_txt})".format(sender_id=sender_id, message_id=message_id, message_txt=message_txt))

    try:
        conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
        with conn:
            cur = conn.cursor()
            cur.execute("INSERT IGNORE INTO `fbbot_logs` (`id`, `message_id`, `chat_id`, `body`) VALUES (NULL, \'{message_id}\', \'{sender_id}\', \'{message_txt}\')".format(message_id=message_id, sender_id=sender_id, message_txt=message_txt))

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
            cur = conn.cursor()
            cur.execute("SELECT `id`, `name`, `info`, `image_url`, `video_url`, `price`, `added` FROM `fb_products` WHERE `enabled` = 1 ORDER BY RAND() LIMIT 1;")
            row = cur.fetchone()

            td = datetime.now() - row[6]
            m, s = divmod(td.seconds, 60)
            h, m = divmod(m, 60)

            element = {
                'title': "Reserve {item_name} for ${price}.".format(item_name=row[1].encode('utf8'), price=row[5]),
                'subtitle': "",
                'image_url': row[3],
                'item_url': "http://prekey.co/stripe.php?from_user={recipient_id}&item_id={item_id}".format(recipient_id=sender_id, item_id=row[0]),
                'buttons': [{
                    'type': "web_url",
                    'url': "http://prekey.co/stripe.php?from_user={recipient_id}&item_id={item_id}".format(recipient_id=sender_id, item_id=row[0]),
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
            cur = conn.cursor()
            cur.execute("SELECT `id`, `name`, `info`, `image_url`, `video_url`, `price`, `added` FROM `fb_products` WHERE `enabled` = 1 LIMIT 1;")
            row = cur.fetchone()

            td = datetime.now() - row[6]
            m, s = divmod(td.seconds, 60)
            h, m = divmod(m, 60)


            element = {
                'title': "Reserve {item_name} for ${price}.".format(item_name=row[1].encode('utf8'), price=row[5]),
                'subtitle': "",
                'image_url': row[3],
                'item_url': "http://prekey.co/stripe.php?from_user={recipient_id}&item_id={item_id}".format(recipient_id=sender_id, item_id=row[0]),
                'buttons': [{
                    'type':"payment",
                    'title':"Buy",
                    'payload':"PURCHASE_{item_id}".format(item_id=row[0]),
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
                            'amount':row[5]
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
            cur = conn.cursor()
            cur.execute("SELECT `id`, `name`, `game_name`, `sponsor`, `image_url`, `trade_url`, `win_video_url`, `lose_video_url` FROM `flip_inventory` WHERE `quantity` > 0 AND `type` = 1 ORDER BY RAND() LIMIT 1;")
            row = cur.fetchone()

            if row is not None:
                element = {
                    'title': "{item_name}".format(item_name=row[1].encode('utf8')),
                    'subtitle': "",
                    'image_url': row[4],
                    'item_url': row[5],
                    'buttons': [{
                        'type': "postback",
                        'payload': "FLIP_COIN-{item_id}".format(item_id=row[0]),
                        'title': "Flip Coin"
                    }]
                }

                if standalone is True:
                    element['buttons'].append({
                        'type': "postback",
                        'payload': "NO_THANKS",
                        'title': "No Thanks"
                    })

                help_session = get_help_session(sender_id)
                help_session = set_help_session({
                    'id': help_session['id'],
                    'state': help_session['state'],
                    'sender_id': help_session['sender_id'],
                    'ignore_count': 0,
                    'started': help_session['started'],
                    'ended': help_session['ended'],
                    'topic_name': row[0]
                })

            else:
                return None

    except mdb.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()

    return element


def start_help(sender_id):
    logger.info("start_help(sender_id={sender_id})".format(sender_id=sender_id))

    session_obj = set_help_session({
        'id': 0,
        'state': 0,
        'sender_id': sender_id,
        'ignore_count': 0,
        'started': time.strftime("%Y-%m-%d %H:%M:%S"),
        'ended': "0000-00-00 00:00:00",
        'topic_name': "N/A",
        'messages': []
    })

    send_text(sender_id, "Welcome to Gamebots. WIN pre-sale games & items with players on Messenger.")
    send_image(sender_id, "http://i.imgur.com/QHHovfa.gif")
    default_carousel(sender_id)

    return session_obj


def end_help(session_obj, from_user=True):
    logger.info("end_help(session_obj={session_obj}, from_user={from_user})".format(session_obj=session_obj, from_user=from_user))

    if (from_user):
        slack_send(session_obj['topic_name'], "_Help session closed_ : *{sender_id}*".format(sender_id=session_obj['sender_id']))

    session_obj = set_help_session({
        'id': session_obj['id'],
        'state': 5,
        'sender_id': session_obj['sender_id'],
        'ignore_count': session_obj['ignore_count'],
        'started': session_obj['started'],
        'ended': time.strftime("%Y-%m-%d %H:%M:%S"),
        'topic_name': session_obj['topic_name']
    })
    send_text(session_obj['sender_id'], "This {topic_name} help session is now closed.".format(topic_name=session_obj['topic_name']))


def fetch_slack_webhook(display_name):
    logger.info("fetch_slack_webhook(display_name={display_name})".format(display_name=display_name))
    _obj = {}

    try:
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        cur = conn.cursor()
        cur.execute("SELECT slack_channels.channel_name, slack_channels.webhook FROM slack_channels INNER JOIN topics ON topics__slack_channels.slack_channel_id = topics.id INNER JOIN topics__slack_channels ON topics__slack_channels.topic_id = topics.id AND topics__slack_channels.slack_channel_id = slack_channels.id WHERE topics.display_name = \'{display_name}\';".format(display_name=display_name))

        row = cur.fetchone()
        if row is not None:
            _obj = {
                'channel_name': row[0],
                'webhook': row[1]
            }

        conn.close()

    except sqlite3.Error as er:
        logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

    finally:
        pass

    return _obj


def faq_quick_replies():
    return [{
        'content_type': "text",
        'title': "More Details",
        'payload': "faq_more-details"
    }, {
        'content_type': "text",
        'title': "Cancel",
        'payload': "faq_cancel"
    }]


def fetch_faq(topic_name):
    logger.info("fetch_faq(topic_name={topic_name})".format(topic_name=topic_name))

    _arr = []

    try:
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        cur = conn.cursor()
        cur.execute("SELECT faq_content.entry FROM faqs JOIN faq_content ON faqs.id = faq_content.faq_id WHERE faqs.title = \'{topic_name}\';".format(topic_name=topic_name))

        for row in cur.fetchall():
            _arr.append(row[0])

        conn.close()

    except sqlite3.Error as er:
        logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

    finally:
        pass

    return _arr


def help_session_state(sender_id):
    # logger.info("help_session_state(sender_id={sender_id})".format(sender_id=sender_id))
    help_state = -1

    try:
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        cur = conn.cursor()
        # cur.execute("SELECT state FROM help_sessions WHERE sender_id = \'{sender_id}\' AND state < 4 ORDER BY added DESC LIMIT 1".format(sender_id=sender_id))
        cur.execute("SELECT state FROM help_sessions WHERE sender_id = \'{sender_id}\' ORDER BY added DESC LIMIT 1".format(sender_id=sender_id))
        row = cur.fetchone()

        if row is not None:
            if row[0] < 4:
                help_state = row[0]

            else:
                help_state = -1

        conn.close()
        logger.info("help_state={help_state}".format(help_state=help_state))

    except sqlite3.Error as er:
        logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

    finally:
        pass

    return help_state


def get_help_session(sender_id):
    logger.info("get_help_session(sender_id={sender_id})".format(sender_id=sender_id))
    _obj = {}

    try:
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        cur = conn.cursor()
        cur.execute("SELECT id, state, topic, ignore_count, started, ended, added FROM help_sessions WHERE sender_id = \'{sender_id}\' ORDER BY added DESC LIMIT 1".format(sender_id=sender_id))

        row = cur.fetchone()
        if row is not None:
            _obj = {
                'id': int(row[0]),
                'state': int(row[1]),
                'sender_id': sender_id,
                # 'topic_name': row[2].encode('utf-8'),
                'topic_name': row[2],
                'ignore_count': row[3],
                'started': row[4],
                'ended': row[5],
                'added': row[6]
            }

        conn.close()

    except sqlite3.Error as er:
        logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

    finally:
        pass

    return _obj


def set_help_session(session_obj):
    logger.info("set_help_session(session_obj={session_obj})".format(session_obj=session_obj))

    try:
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        cur = conn.cursor()

        if session_obj['id'] == 0:
            try:
                cur.execute("INSERT INTO help_sessions (id, sender_id, topic) VALUES (NULL, ?, ?)", (session_obj['sender_id'], session_obj['topic_name']))
                conn.commit()

            except sqlite3.Error as er:
                logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

        else:
            try:
                cur.execute("UPDATE help_sessions SET state = {state}, topic = \'{topic}\', ignore_count=\'{ignore_count}\', started = \'{started}\', ended = \'{ended}\' WHERE id = {id} LIMIT 1".format(state=session_obj['state'], topic=session_obj['topic_name'], ignore_count=session_obj['ignore_count'], started=session_obj['started'], ended=session_obj['ended'], id=session_obj['id']))
                conn.commit()

            except sqlite3.Error as er:
                logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

        conn.close()

    except sqlite3.Error as er:
        logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

    finally:
        pass

    return get_help_session(session_obj['sender_id'])


@app.route('/slack', methods=['POST'])
def slack():
    logger.info("=-=-=-=-=-=-=-=-=-=-= SLACK RESPONSE =-=-=-=-=-=-=-=-=-=-=")
    logger.info("{form}".format(form=request.form))
    if request.form.get('token') == "uKA7dgfnfadLN4QApLYmmn4m":
        help_session = {}

        _arr = request.form.get('text').split(' ')
        _arr.pop(0)

        sender_id = _arr[0]
        _arr.pop(0)

        message = " ".join(_arr).replace("'", "")

        try:
            conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute(
                    "SELECT `id` FROM `fbbot_logs` WHERE `chat_id` = '%s' ORDER BY `added` DESC LIMIT 1;" % (sender_id))

                if cur.rowcount == 1:
                    help_session = get_help_session(sender_id)
                    help_session = set_help_session({
                        'id': help_session['id'],
                        'state': help_session['state'],
                        'sender_id': help_session['sender_id'],
                        'ignore_count': 0,
                        'started': help_session['started'],
                        'ended': help_session['ended'],
                        'topic_name': help_session['topic_name']
                    })

                    if message == "!end" or message.lower() == "cancel" or message.lower() == "quit":
                        logger.info("-=- ENDING HELP -=- ({timestamp})".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
                        end_help(help_session, False)

                    else:
                        send_text(sender_id, "{topic_name} coach:\n{message}".format(topic_name=help_session['topic_name'], message=message))


        except mdb.Error, e:
            logger.info("MySqlError {code}: {message}".format(code=e.args[0], message=e.args[1]))

        finally:
            if conn:
                conn.close()

    return "OK", 200


@app.route('/', methods=['GET'])
def verify():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info(
        "=-=-=-=-=-=-=-=-=-=-=-=-= VERIFY ({hub_mode})->{request}\n".format(hub_mode=request.args.get('hub.mode'),
                                                                            request=request))
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

                if 'postback' in messaging_event:  # user clicked/tapped "postback" button in earlier message
                    logger.info("-=- POSTBACK RESPONSE -=- (%s)" % (messaging_event['postback']['payload']))

                    sender_id = messaging_event['sender']['id']
                    if messaging_event['postback']['payload'] == "WELCOME_MESSAGE":
                        logger.info("----------=NEW SESSION @({timestamp})=----------".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
                        send_tracker("signup-fb-pre", sender_id, "")
                        help_session = start_help(sender_id)

                    elif 'FLIP_COIN' in messaging_event['postback']['payload']:
                        item_id = int(messaging_event['postback']['payload'].split("-")[-1])
                        send_tracker("flip-item", sender_id, "")
                        send_image(sender_id, "http://i.imgur.com/C6Pgtf4.gif")
                        help_session = get_help_session(sender_id)

                        try:
                            conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
                            with conn:
                                cur = conn.cursor()
                                cur.execute("SELECT `id`, `name`, `game_name`, `image_url`, `trade_url`, `win_video_url`, `lose_video_url` FROM `flip_inventory` WHERE `id` = {item_id};".format(item_id=item_id))
                                row = cur.fetchone()

                        except mdb.Error, e:
                            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                        finally:
                            if conn:
                                conn.close()

                        if random.random() <= 0.45 or sender_id == 1046211495488285:
                            help_session = set_help_session({
                                'id': help_session['id'],
                                'state': help_session['state'],
                                'sender_id': help_session['sender_id'],
                                'ignore_count': 1,
                                'started': help_session['started'],
                                'ended': help_session['ended'],
                                'topic_name': help_session['topic_name'],
                            })

                            print(">>>>>>>>>>>>> row[4] = %s <<<<<<<<<<<<<<<<<" % row[4])

                            conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
                            try:
                                with conn:
                                    cur = conn.cursor()
                                    cur.execute(
                                        "INSERT INTO `item_winners` (`fb_id`, `item_name`, `added`) VALUES (%s, %s, NOW())", (sender_id, row[1]))
                                    cur.execute(
                                        "UPDATE `flip_inventory` SET `quantity` = `quantity` - 1 WHERE `id` = {item_id} LIMIT 1;".format(item_id=row[0]))
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
                                'text': "Flip Win by {sender_id}:\n{item_name}\n{trade_url}".format(sender_id=sender_id, item_name=row[1], trade_url=row[2]),
                                'attachments': [{
                                    'image_url': row[3]
                                }]
                            }
                            response = requests.post("https://hooks.slack.com/services/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",data={'payload': json.dumps(payload)})

                            send_image(sender_id, row[5])
                            send_card(
                                recipient_id=sender_id,
                                title="{item_name}".format(item_name=row[1].encode('utf8')),
                                image_url=row[3],
                                card_url=row[4],
                                buttons=[
                                    {
                                        'type': "element_share"
                                    }, {
                                        'type': "web_url",
                                        'url': row[4],
                                        'title': "Trade"
                                    }
                                ],
                                quick_replies=[
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
                            )

                            send_image(recipient_id=sender_id, url=row[5])
                            send_text(
                                recipient_id=sender_id,
                                message_text="YOU WON!\n{item_name} from {game_name}.\n\nTo claim:\nTap the Trade URL and select your items (we verify the items you select)".format(item_name=row[1].encode('utf8'), game_name=row[2]),
                                quick_replies=[
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
                            )

                        else:
                            send_image(sender_id, row[6])
                            send_text(
                                recipient_id=sender_id,
                                message_text="TRY AGAIN!\n\nYou lost {item_name} from {game_name}.".format(item_name=row[1].encode('utf8'), game_name=row[2]),
                                quick_replies=[
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
                            )

                    elif messaging_event['postback']['payload'] == "BOUNTY":
                        send_tracker("bounty", sender_id, "")
                        default_carousel(sender_id)

                    elif messaging_event['postback']['payload'] == "INVITE":
                        send_card(
                            recipient_id=sender_id,
                            title="Share",
                            image_url="http://i.imgur.com/C6Pgtf4.gif",
                            card_url="http://prebot.chat",
                            buttons=[{'type': "element_share"}],
                            quick_replies=[{
                                'content_type': "text",
                                'title': "Main Menu",
                                'payload': "MAIN_MENU"
                            }]
                        )

                    elif messaging_event['postback']['payload'] == "NO_THANKS":
                        send_tracker("cancel", sender_id, "")
                        default_carousel(sender_id)

                    elif messaging_event['postback']['payload'] == "MAIN_MENU":
                        send_tracker("main-menu", sender_id, "")
                        default_carousel(sender_id)

                    return "OK", 200

                # -- actual message
                if messaging_event.get('message'):
                    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECIEVED ->{message}".format(message=messaging_event['sender']))

                    # ------- IMAGE MESSAGE
                    if 'attachments' in messaging_event['message']:
                        # send_text(messaging_event['sender']['id'], "I'm sorry, I cannot understand that type of message.")
                        return "OK", 200

                    # MESSAGE CREDENTIALS
                    sender_id = messaging_event['sender']['id']  # the facebook ID of the person sending you the message
                    recipient_id = messaging_event['recipient']['id']  # the recipient's ID, which should be your page's facebook ID
                    message_id = messaging_event['message']['mid']
                    message_text = messaging_event['message']['text']  # the message's text
                    timestamp = messaging_event['timestamp']
                    quick_reply = None

                    if 'quick_reply' in messaging_event['message'] and messaging_event['message']['quick_reply']['payload'] is not None:
                        logger.info("QR --> {quick_replies}".format(quick_replies=quote(messaging_event['message']['quick_reply']['payload'])))
                        quick_reply = quote(messaging_event['message']['quick_reply']['payload'])

                    # -- insert to log
                    write_message_log(sender_id, message_id, messaging_event['message'])

                    help_state = help_session_state(sender_id)

                    if help_state > -1:
                        help_session = get_help_session(sender_id)

                    else:
                        help_session = {}

                    logger.info(":::::::::::]- help_state={help_state}".format(help_state=help_state))

                    # -- typed '!end' / 'cancel' / 'quit'
                    if message_text == "!end" or message_text.lower() == "cancel" or message_text.lower() == "quit":
                        logger.info("-=- ENDING HELP -=- ({timestamp})".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))

                        if help_state > -1:
                            help_session = set_help_session({
                                'id': help_session['id'],
                                'state': 6,
                                'sender_id': help_session['sender_id'],
                                'ignore_count': help_session['ignore_count'],
                                'started': help_session['started'],
                                'ended': time.strftime("%Y-%m-%d %H:%M:%S"),
                                'topic_name': help_session['topic_name']
                            })
                            send_text(help_session['sender_id'], "You are using Pre (on Messenger). If you need support please email us at support@prebot.chat")

                        return "OK", 200

                    elif message_text == "/:item_purchase:/":
                        send_text(sender_id, "Test Payment Card:")
                        payment_carousel(sender_id)
                        #send_carousel(sender_id, product_buy_element(sender_id))
                        return "OK", 200

                    # -- non-existant
                    if help_state == -1:
                        logger.info("----------=NEW SESSION @({timestamp})=----------".format(
                            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
                        send_tracker("signup-fb-pre", messaging_event['sender']['id'], "")
                        help_session = start_help(sender_id)


                    # -- started
                    elif help_state == 0:
                        logger.info("----------=CREATED SESSION=----------")
                        logger.info("help_session={help_session}".format(help_session=help_session))

                        if quick_reply is None:
                            send_text(sender_id, "Welcome to Gamebots. WIN pre-sale games & items with players on Messenger.")
                            default_carousel(sender_id)

                        else:
                            send_tracker("{show}-button".format(show=quick_reply.split("_")[-1].lower()),  messaging_event['sender']['id'], "")

                            if quick_reply == "BOUNTY":
                                send_text(sender_id, "Do you want to win today's item for FREE?\n\nEarn points with Pre's Bounty! taps.io/gamebounty")
                                default_carousel(sender_id)

                            elif quick_reply == "INVITE":
                                send_card(
                                    recipient_id=sender_id,
                                    title="Share",
                                    image_url="http://i.imgur.com/C6Pgtf4.gif",
                                    card_url="http://prebot.chat",
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

                            else:
                                default_carousel(sender_id)


                                # help_session = set_help_session({
                                #  'id': help_session['id'],
                                #  'state': 1,
                                #  'sender_id': help_session['sender_id'],
                                #  'ignore_count': 0,
                                #  'started': time.strftime("%Y-%m-%d %H:%M:%S"),
                                #  'ended': help_session['ended'],
                                #  'topic_name': quick_reply.split("_")[-1]
                                # })
                                # send_text(sender_id, "Please describe what you need help with. Note your messages will be sent to %s coaches for support." % (help_session['topic_name']))


                    # -- requesting help
                    elif help_state == 1:
                        logger.info("----------=REQUESTED SESSION=----------")

                        slack_send(help_session['topic_name'], "Requesting help: *{sender_id}*\n_\"{message_text}\"_".format(sender_id=sender_id, message_text=message_text), sender_id)

                        send_text(sender_id, "Locating {topic_name} coaches...".format(topic_name=help_session['topic_name']))
                        gevent.sleep(3)

                        send_text(sender_id, "Your question has been added to the {topic_name} queue and will be answered shortly.".format(topic_name=help_session['topic_name']))
                        gevent.sleep(2)

                        send_text(sender_id,"Pro tip: Keep asking questions, each will be added to your queue! Type Cancel to end the conversation.")

                        help_session = set_help_session({
                            'id': help_session['id'],
                            'state': 2,
                            'sender_id': help_session['sender_id'],
                            'ignore_count': help_session['ignore_count'],
                            'started': help_session['started'],
                            'ended': help_session['ended'],
                            'topic_name': help_session['topic_name']
                        })


                    # -- in session
                    elif help_state == 2:
                        logger.info("----------=IN PROGRESS SESSION=----------")

                        if help_session['ignore_count'] >= Const.MAX_IGNORES - 1:
                            logger.info("-=- TOO MANY UNREPLIED - ({count}) CLOSE OUT SESSION -=-".format(count=Const.MAX_IGNORES))

                            help_session = set_help_session({
                                'id': help_session['id'],
                                'state': 3,
                                'sender_id': help_session['sender_id'],
                                'ignore_count': help_session['ignore_count'],
                                'started': help_session['started'],
                                'ended': time.strftime("%Y-%m-%d %H:%M:%S"),
                                'topic_name': help_session['topic_name']
                            })

                            send_text(sender_id, "Sorry! GameBots is taking so long to answer your question. What would you like to do?", faq_quick_replies())

                        # -- continue convo
                        else:

                            slack_send(help_session['topic_name'], "Requesting help: *{sender_id}*\n_\"{message_text}\"_".format(sender_id=sender_id, message_text=message_text), sender_id)

                            help_session = set_help_session({
                                'id': help_session['id'],
                                'state': 2,
                                'sender_id': help_session['sender_id'],
                                'ignore_count': help_session['ignore_count'] + 1,
                                'started': help_session['started'],
                                'ended': help_session['ended'],
                                'topic_name': help_session['topic_name']
                            })


                    # -- display faq
                    elif help_state == 3:
                        logger.info("----------=FAQ PERIOD=----------")

                        if quick_reply is None:
                            logger.info("----------=PROMPT FOR FAQ ({topic_name})=----------".format(topic_name=help_session['topic_name']))
                            send_text(sender_id, "Sorry! GameBots is taking so long to answer your question. What would you like to do?", faq_quick_replies())

                        else:
                            if quick_reply.split("_")[-1] == "more-details":
                                for entry in fetch_faq(help_session['topic_name']):
                                    send_text(sender_id, quote(entry))
                                    gevent.sleep(5)

                            else:
                                pass

                            send_text(sender_id, "Ok, Thanks for using GameBots!")

                            help_session = set_help_session({
                                'id': help_session['id'],
                                'state': 4,
                                'sender_id': help_session['sender_id'],
                                'ignore_count': help_session['ignore_count'] + 1,
                                'started': help_session['started'],
                                'ended': help_session['ended'],
                                'topic_name': help_session['topic_name']
                            })

                            # if quick_reply.split("_")[-1] == "more-details":
                            #   gevent.sleep(3)
                            #   help_session = start_help(help_session['sender_id'])

                    # -- completed
                    elif help_state == 4:
                        pass


                    # closed by coach
                    elif help_state == 5:
                        pass

                    # -- canceled / quit
                    elif help_state == 6:
                        send_text(sender_id, "Ok, Thanks for using GameBots!")


                    else:
                        pass

    return "OK", 200


def send_text(recipient_id, message_text, quick_replies=[]):
    # logger.info("send_text(recipient_id={recipient}, message_text={text}, quick_replies={quick_replies})".format(recipient=recipient_id, text=message_text, quick_replies=quick_replies))
    data = {
        'recipient': {
            'id': recipient_id
        },
        'message': {
            'text': message_text
        }
    }

    if len(quick_replies) > 0:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))


def send_card(recipient_id, title, image_url, card_url, subtitle="", buttons=[], quick_replies=[]):
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

    if len(quick_replies) > 0:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))


def send_carousel(recipient_id, elements, quick_replies=[]):
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

    if len(quick_replies) > 0:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))


def send_image(recipient_id, url, quick_replies=[]):
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

    if len(quick_replies) > 0:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))


def send_video(recipient_id, url, quick_replies=[]):
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

    if len(quick_replies) > 0:
        data['message']['quick_replies'] = quick_replies
    send_message(json.dumps(data))


def send_message(payload):
    logger.info("send_message(payload={payload})".format(payload=payload))

    # t1 = threading.Thread(
    #     target=async_send_message,
    #     name="FB-Message-Sender",
    #     kwargs={ 'payload' : payload }
    # )
    #
    # t1.start()

    response = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN),data=payload, headers={'Content-Type': "application/json"})
    logger.info("GRAPH RESPONSE ({code}): {result}".format(code=response.status_code, result=response.text))

    return True

def async_send_message(payload):
    logger.info("async_send_message(payload={payload})".format(payload=payload))

    response = requests.post("https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN),data=payload, headers={'Content-Type': "application/json"})
    logger.info("GRAPH RESPONSE ({code}): {result}".format(code=response.status_code, result=response.text))


if __name__ == '__main__':
    app.run(debug=True)
