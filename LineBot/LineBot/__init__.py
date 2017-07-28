#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import csv
import hashlib
import json
import locale
import logging
import os
import random
import re
import sqlite3
import sys
import time

from datetime import datetime
from itertools import cycle
from StringIO import StringIO
from urllib import urlencode

import MySQLdb as mdb
import pycurl
import requests
import urllib

from flask import Flask, escape, request, session
from flask_cors import CORS, cross_origin

from constants import Const


reload(sys)
sys.setdefaultencoding('utf8')
locale.setlocale(locale.LC_ALL, 'en_US.utf8')

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler('/var/log/FacebookBot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#

def bot_webhook_type(webhook):
    logger.info("bot_webhook_type(webhook=%s)" % (webhook,))

    if webhook == "happy-hour":
        return 1

    elif webhook == "top-style":
        return 2


def bot_access_token(bot_type):
    logger.info("bot_webhook_type(webhook=%s)" % (webhook,))

    if bot_type == 1:
        return Const.HAPPYHOUR_ACCESS_TOKEN

    elif bot_type == 2:
        return Const.TOPSTYLE_ACCESS_TOKEN


def carousel_cards(bot_type):
    logger.info("carousel_cards(bot_type=%s)" % (bot_type,))

    cards = [[{
        'id'       : 1,
        'title'    : "98 Turk",
        'subtitle' : "Starts at 5pm. Ends at 6pm",
        'image_url': "https://imgur.com/0hfrKK1.png",
        'card_url' : "http://example.com"
    }, {
        'id'       : 2,
        'title'    : "Black Cat",
        'subtitle' : "Starts at 4pm. Ends at 6pm",
        'image_url': "https://i.imgur.com/qZF2Ix5.png",
        'card_url' : "http://example.com"
    }, {
        'id'       : 3,
        'title'    : "Mezcalito",
        'subtitle' : "Starts at 4pm. Ends at 7pm",
        'image_url': "https://i.imgur.com/mAqjn4w.png",
        'card_url' : "http://example.com"
    }, {
        'id'       : 4,
        'title'    : "The Treasury",
        'subtitle' : "Starts at 4pm. Ends at 5:30",
        'image_url': "https://i.imgur.com/LiqtzoF.png",
        'card_url' : "http://example.com"
    }], [{
        'id'       : 1,
        'title'    : "Jenny (@jennyInsta)",
        'subtitle' : "",
        'image_url': "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/ccbe43e029714325635391627bad51cd/hair1.jpg",
        'card_url' : None
    }, {
        'id'       : 2,
        'title'    : "Megan (@julieInsta)",
        'subtitle' : "",
        'image_url': "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/e466f78fcc08ba52f7a258fc57072a67/hair2.jpg",
        'card_url' : None
    }, {
        'id'       : 3,
        'title'    : "Julie (@julieInsta)",
        'subtitle' : "",
        'image_url': "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/a71fd2bb3b8608e9b2869ecfe5e0bf0f/hair3.jpg",
        'card_url' : None
    }, {
        'id'       : 4,
        'title'    : "Kyle (@julieInsta)",
        'subtitle' : "",
        'image_url': "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/a080d2c164f6d048d3ec416e0149b88c/hair4.jpg",
        'card_url' : None
    }, {
        'id'       : 5,
        'title'    : "Mandy (@mandyInsta)",
        'subtitle' : "",
        'image_url': "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/33d1124b002d14d215dc04ecc6c2f52a/hair5.jpg",
        'card_url' : None
    }]]

    return cards[max(0, bot_type - 1)]


def set_user(sender_id):
    logger.info("set_user(sender_id=%s)" % (sender_id,))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE fb_psid = ? LIMIT 1;', (sender_id,))
        row = cur.fetchone()
        if row is None:
            cur.execute('INSERT INTO users (id, bot_type, fb_psid, flipped, added) VALUES (NULL, ?, ?, ?, ?);', (0, sender_id, 0, int(time.time())))
            conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_user[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_user_bot_type(sender_id):
    logger.info("get_user_bot_type(sender_id=%s)" % (sender_id,))

    bot_type = 0
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT bot_type FROM users WHERE fb_psid = ? LIMIT 1;', (sender_id,))
        row = cur.fetchone()
        if row is not None:
            bot_type = row['bot_type']

    except sqlite3.Error as er:
        logger.info("::::::get_user_bot_type[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return bot_type


def set_user_bot_type(sender_id, bot_type=0):
    logger.info("set_user_bot_type(sender_id=%s, bot_type=%s)" % (sender_id, bot_type))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE users SET bot_type = ? WHERE fb_psid = ?;', (bot_type, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_flipped[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_zipcode(sender_id):
    logger.info("get_zipcode(sender_id=%s)" % (sender_id,))

    zipcode = ""
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT zipcode FROM users WHERE fb_psid = ? LIMIT 1;', (sender_id,))
        row = cur.fetchone()
        if row is not None:
            zipcode = row['zipcode']

    except sqlite3.Error as er:
        logger.info("::::::get_zipcode[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return zipcode


def set_zipcode(sender_id, zipcode=None):
    logger.info("set_zipcode(sender_id=%s, zipcode=%s)" % (sender_id, zipcode))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE users SET zipcode = ? WHERE fb_psid = ?;', (zipcode, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_zipcode[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_flipped(sender_id):
    logger.info("get_flipped(sender_id=%s)" % (sender_id,))

    flipped = 0
    updated = 0
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT flipped, updated FROM users WHERE fb_psid = ? LIMIT 1;', (sender_id,))
        row = cur.fetchone()
        if row is not None:
            flipped = row['flipped']
            updated = row['updated']

    except sqlite3.Error as er:
        logger.info("::::::get_flipped[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return (flipped, updated)


def set_flipped(sender_id, flipped=0):
    logger.info("set_flipped(sender_id=%s, flipped=%s)" % (sender_id, flipped))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE users SET flipped = ?, updated = ? WHERE fb_psid = ?;', (flipped, int(time.time()), sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_flipped[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_email(sender_id):
    logger.info("get_email(sender_id=%s)" % (sender_id,))

    email = None
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT email FROM users WHERE "fb_psid" = ? LIMIT 1;', (sender_id,))
        row = cur.fetchone()
        if row is not None:
            email = row['email']

    except sqlite3.Error as er:
        logger.info("::::::get_email[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return email


def set_email(sender_id, email=None):
    logger.info("set_email(sender_id=%s, email=%s)" % (sender_id, email))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE users SET email = ? WHERE fb_psid = ?;', (email, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_email[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_optout(sender_id):
    logger.info("get_optout(sender_id=%s)" % (sender_id,))

    optout = None
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT optout FROM users WHERE "fb_psid" = ? LIMIT 1;', (sender_id,))
        row = cur.fetchone()
        if row is not None:
            optout = row['optout']

    except sqlite3.Error as er:
        logger.info("::::::get_optout[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return optout == 1


def set_optout(sender_id, optout=True):
    logger.info("set_email(sender_id=%s, optout=%s)" % (sender_id, optout))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE users SET optout = ? WHERE fb_psid = ?;', (optout, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_optout[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()




def build_cancel_button():
    logger.info("build_cancel_button()")

    return {
        'content_type': "text",
        'title'       : "Cancel",
        'payload'     : "CANCEL"
    }

def build_quick_replies(sender_id=None):
    logger.info("build_quick_replies(sender_id=%s)" % (sender_id,))


    if get_user_bot_type(sender_id) == 1:
        quick_replies = [{
            'content_type': "text",
            'title'       : "Enter Zipcode",
            'payload'     : "ZIPCODE"
        }]

    else:
        quick_replies = []


    quick_replies.append({
        'content_type': "text",
        'title'       : "Menu",
        'payload'     : "MENU"
    })

    flipped, updated = get_flipped(sender_id)
    if updated <= int(time.time()) - 86400:
        quick_replies.append({
            'content_type': "text",
            'title'       : "Flip",
            'payload'     : "FLIP"
        })

    return quick_replies + [{
        'content_type': "text",
        'title'       : "Website",
        'payload'     : "WEBSITE"
    }, {
        'content_type': "text",
        'title'       : "Support",
        'payload'     : "SUPPORT"
    }]


def build_flip_element(sender_id):
    logger.info("build_flip_element(sender_id=%s)" % (sender_id,))

    return {
        'title'    : "Flip to win",
        'subtitle' : "Flip to Win NOW!!!!!!",
        'image_url': "https://trello-attachments.s3.amazonaws.com/5976e90fdffb46d99a6cf75d/597a2fd869f992c24758180d/747d255167409849886bde0229a5e1d9/flip_to_win02.png" if get_user_bot_type(sender_id) == 1 else "https://i.imgur.com/DJN4AKL.png",
        'item_url' : None,
        'buttons'  : [{
            'type'   : "postback",
            'payload': "FLIP-{item_id}".format(item_id=1),
            'title'  : "Flip"
        }]
    }


def build_carousel_elements(sender_id):
    logger.info("build_carousel_elements(sender_id=%s)" % (sender_id,))

    elements = []
    for element in carousel_cards(get_user_bot_type(sender_id)):
        elements.append({
            'title'    : element['title'],
            'subtitle' : element['subtitle'] or "",
            'image_url': element['image_url'],
            'item_url' : None,
            'buttons'  : [{
                'type'   : "postback",
                'payload': "VIEW-{item_id}".format(item_id=len(elements) + 1),
                'title'  : "Call an Uber" if get_user_bot_type(sender_id) == 1 else "View Style"
            }]
        })

    return elements


def send_flip(sender_id, item_id):
    logger.info("send_flip(sender_id=%s, item_id=%s)" % (sender_id, item_id))

    flipped, updated = get_flipped(sender_id)
    logger.info("flipped=%s, updated=%s)" % (flipped, updated))

    if updated >= int(time.time()) - 86400:
        send_text(sender_id, "Already flipped today!")
        send_default_carousel(sender_id)

    else:
        outcome = random.uniform(0, 100) < 500
        set_flipped(sender_id, 3 if outcome is True else 2)

        send_image(sender_id, "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/9a11e8d50e223bc2c765f4e7f83f1cc7/flip_happyhour.gif" if get_user_bot_type(sender_id) == 1 else "https://i.imgur.com/1o4YoY1.gif")
        time.sleep(2)

        if outcome is True:
            set_email(sender_id, "_{PENDING}_")

            if get_user_bot_type(sender_id) == 1:
                send_card(
                    recipient_id=sender_id,
                    title="Visit Ease",
                    image_url="https://i.imgur.com/K8gubpY.jpg",
                    card_url="https://www.eaze.com/",
                    quick_replies=build_quick_replies(sender_id)
                )

                send_text(sender_id, "You Won! A free sample provided by Eaze. To claim please enter a valid email address now.", [build_cancel_button()])

            else:
                send_text(sender_id, "You won! A free haircut from Fox and Salon. Please enter a valid email address we can send your reward information to.", [build_cancel_button()])

        else:
            send_text(sender_id, "Lost", build_quick_replies(sender_id))


def send_item_card(sender_id, item_id):
    logger.info("send_item_card(sender_id=%s, item_id=%s)" % (sender_id, item_id))

    element = carousel_cards(get_user_bot_type(sender_id))[max(0, int(item_id) - 1)]

    send_card(
        recipient_id=sender_id,
        title=element['title'],
        image_url=element['image_url'],
        card_url=element['card_url'] or "",
        quick_replies=build_quick_replies(sender_id)
    )


def send_default_carousel(sender_id, amount=3):
    logger.info("send_default_carousel(sender_id=%s amount=%s)" % (sender_id, amount))

    elements = []
    flipped, updated = get_flipped(sender_id)
    if updated <= int(time.time()) - 86400:
        elements.append(build_flip_element(sender_id))

    send_carousel(
        recipient_id=sender_id,
        elements=elements + build_carousel_elements(sender_id),
        quick_replies=build_quick_replies(sender_id)
    )



# =- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
# =- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



@app.route('/<bot_webhook>/', methods=['GET'])
def verify(bot_webhook):
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= VERIFY (%s)->%s [%s]\n" % (bot_webhook, request.args.get('hub.mode'), request))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == Const.VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args['hub.challenge'], 200

    return "OK", 200


# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


@app.route('/<bot_webhook>/', methods=['POST'])
def webhook(bot_webhook):
    bot_type = bot_webhook_type(bot_webhook)
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
                    # send_tracker(fb_psid=messaging_event['sender']['id'], category="read-receipt")
                    return "OK", 200

                if 'optin' in messaging_event:  # optin confirmation
                    logger.info("-=- OPT-IN -=-")
                    return "OK", 200

                payload = None
                sender_id = messaging_event['sender']['id']
                message = messaging_event['message'] if 'message' in messaging_event else None
                message_id = message['mid'] if message is not None and 'mid' in message else messaging_event['id'] if 'id' not in entry else entry['id']

                # ------- REFERRAL MESSAGE
                referral = None if 'referral' not in messaging_event else messaging_event['referral']['ref'].encode('ascii', 'ignore')
                if referral is None and 'postback' in messaging_event and 'referral' in messaging_event['postback']:
                    referral = messaging_event['postback']['referral']['ref'].encode('ascii', 'ignore')

                # ------- POSTBACK BUTTON MESSAGE
                if 'postback' in messaging_event:
                    logger.info("POSTBACK --> %s" % (messaging_event['postback']['payload']))
                    payload = messaging_event['postback']['payload']

                # ------- QUICK REPLY MESSAGE
                if message is not None and 'quick_reply' in message and message['quick_reply']['payload'] is not None:
                    payload = message['quick_reply']['payload']
                    logger.info("QR --> %s" % (payload,))


                if get_optout(sender_id) is True:
                    return "OK", 200


                # -- insert to log
                # send_text(sender_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), build_quick_replies(sender_id))

                if referral is not None:
                    logger.info("REFERRAL ---> %s", (referral,))

                if payload is not None:
                    session['payload'] = payload
                    handle_payload(sender_id, payload, bot_webhook_type(bot_webhook))

                else:
                    # ------- TYPED TEXT MESSAGE
                    if message is not None and 'text' in message:
                        if get_user_bot_type(sender_id) == 0:
                            set_user(sender_id)
                            set_user_bot_type(sender_id, bot_webhook_type(bot_webhook))


                        if message['text'] in Const.RESERVED_ALERT_REPLIES.split("|"):
                            send_text(sender_id, "It's 4pm. Time to Get Happy!", build_quick_replies(sender_id))
                            return "OK", 200

                        elif message['text'] in Const.RESERVED_OPTOUT_REPLIES.split("|"):
                            set_optout(sender_id)
                            send_text(sender_id, "You have opted out.")
                            return "OK", 200

                        elif get_email(sender_id) == "_{PENDING}_":
                            if re.search(r'^.+\@.+\..*$', message['text']) is not None:
                                set_email(sender_id, message['text'])
                                send_text(sender_id, "{email_addr} saved".format(email_addr=message['text']), build_quick_replies(sender_id))

                            else:
                                send_text(sender_id, "Invalid email", [build_cancel_button()])
                                return "OK", 200

                        elif get_zipcode(sender_id) == "_{PENDING}_":
                            if re.search(r'^\d+$', message['text']) is not None:
                                set_zipcode(sender_id, message['text'])
                                send_text(sender_id, "{zipcode} saved".format(zipcode=message['text']), build_quick_replies(sender_id))

                            else:
                                send_text(sender_id, "Invalid zipcode", [build_cancel_button()])
                                return "OK", 200

                        send_default_carousel(sender_id)


    return "OK", 200


# =- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


def handle_payload(sender_id, payload, bot_type):
    logger.info("handle_payload(sender_id=%s, payload=%s, bot_type=%s)" % (sender_id, payload, bot_type))

    if payload == "WELCOME_MESSAGE":
        set_user(sender_id)
        set_user_bot_type(sender_id, bot_type)

        send_text(sender_id, "Welcome to {bot_title}. To opt-out of further messaging, type exit, quit, or stop.".format(bot_title="HappyHour" if bot_type == 1 else "Top Style"))
        send_image(sender_id, "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/9a11e8d50e223bc2c765f4e7f83f1cc7/flip_happyhour.gif" if bot_type == 1 else "https://i.imgur.com/1o4YoY1.gif")

        if bot_type == 1:
            set_zipcode(sender_id, "_{PENDING}_")
            send_text(sender_id, "Please enter your Zip Code to receive updates on daily happy hours in your area.", [build_cancel_button()])

        else:
            send_default_carousel(sender_id)

    elif payload == "ZIPCODE":
        set_zipcode(sender_id, "_{PENDING}_")
        send_text(sender_id, "Please enter your Zip Code to receive updates on daily happy hours in your area.", [build_cancel_button()])

    elif payload == "MENU":
        send_default_carousel(sender_id)

    elif payload == "FLIP":
        send_flip(sender_id, 1)
        # send_carousel(
        #     recipient_id=sender_id,
        #     elements=[build_flip_element(sender_id)],
        #     quick_replies=build_quick_replies(sender_id)
        # )

    elif payload == "WEBSITE":
        send_card(
            recipient_id=sender_id,
            title="happyhour.bot" if bot_type == 1 else "foxandjanesalon.com",
            image_url="https://scontent-sjc2-1.xx.fbcdn.net/v/t1.0-9/20294516_106493256703647_5694536636197485639_n.png?oh=dc6ae511db1644ca247b30f5d16be5a6&oe=5A378726" if bot_type == 1 else "https://scontent-sjc2-1.xx.fbcdn.net/v/t1.0-9/20294515_254659165032297_7229853044888461966_n.png?oh=2b270114e028ff27a733d85e58a01c53&oe=5A07B2EE",
            card_url="http://www.happyhour.bot" if bot_type == 1 else "http://www.foxandjanesalon.com",
            quick_replies=build_quick_replies(sender_id)
        )

    elif payload == "SUPPORT":
        send_text(sender_id, "Send support to {support_email}".format(support_email="support@happyhour.bot" if bot_type == 1 else "support@foxandjanesalon.com"), build_quick_replies(sender_id))

    elif re.search(r'^VIEW\-(\d+)$', payload):
        if bot_type == 1:
            send_item_card(sender_id, re.match(r'^VIEW\-(?P<item_id>\d+)$', payload).group('item_id'))

        else:
            send_text(sender_id, "Content not available in demo.", build_quick_replies(sender_id))

    elif re.search(r'^FLIP\-(\d+)$', payload):
        send_flip(sender_id, re.match(r'^FLIP\-(?P<item_id>\d+)$', payload).group('item_id'))

    elif payload == "CANCEL":
        set_email(sender_id)
        set_zipcode(sender_id)
        send_default_carousel(sender_id)


# =- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
# =- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



def send_card(recipient_id, title, image_url, card_url=None, subtitle=None, buttons=None, quick_replies=None):
    logger.info("send_card(recipient_id=%s, title=%s, image_url=%s, card_url=%s, subtitle=%s, buttons=%s, quick_replies=%s)" % (recipient_id, title, image_url, card_url, subtitle, buttons, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient': {
            'id': recipient_id
        },
        'message'  : {
            'attachment': {
                'type'   : "template",
                'payload': {
                    'template_type': "generic",
                    'elements'     : [{
                        'title'    : title,
                        'item_url' : card_url,
                        'image_url': image_url,
                        'subtitle' : subtitle or "",
                        'buttons'  : buttons
                    }]
                }
            }
        }
    }

    if buttons is not None:
        data['message']['attachment']['payload']['elements'][0]['buttons'] = buttons

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(get_user_bot_type(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_carousel(recipient_id, elements, quick_replies=None):
    logger.info("send_carousel(recipient_id=%s, elements=%s, quick_replies=%s)" % (recipient_id, elements, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient': {
            'id': recipient_id
        },
        'message'  : {
            'attachment': {
                'type'   : "template",
                'payload': {
                    'template_type': "generic",
                    'elements'     : elements
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(get_user_bot_type(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_typing_indicator(recipient_id, is_typing):
    data = {
        'recipient'    : {
            'id': recipient_id
        },
        'sender_action': "typing_on" if is_typing else "typing_off"
    }

    send_message(get_user_bot_type(recipient_id), json.dumps(data))


def send_text(recipient_id, message_text, quick_replies=None):
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient': {
            'id': recipient_id
        },
        'message'  : {
            'text': message_text
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(get_user_bot_type(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_image(recipient_id, url, attachment_id=None, quick_replies=None):
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient': {
            'id': recipient_id
        },
        'message'  : {
            'attachment': {
                'type'   : "image",
                'payload': {
                    'url': url
                }
            }
        }
    }

    if attachment_id is not None:
        data['message']['attachment']['payload'] = {'attachment_id': attachment_id}

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(get_user_bot_type(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_video(recipient_id, url, attachment_id=None, quick_replies=None):
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient': {
            "id": recipient_id
        },
        'message'  : {
            'attachment': {
                'type'   : "video",
                'payload': {
                    'url'        : url,
                    'is_reusable': True
                }
            }
        }
    }

    if attachment_id is not None:
        data['message']['attachment']['payload'] = {'attachment_id': attachment_id}

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(get_user_bot_type(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_message(bot_type, payload):
    logger.info("send_message(bot_type=%s, payload=%s)" % (bot_type, payload))

    response = requests.post(
        url="https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=bot_access_token(bot_type)),
        headers={'Content-Type': "application/json"},
        data=payload
    )
    logger.info("SEND MESSAGE response: %s" % (response.json()))

    return True


if __name__ == '__main__':
    logger.info("Firin up FbBot using verify token [%s]." % (Const.VERIFY_TOKEN))
    app.run(debug=True)
