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

    bot_id = 0
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `bots` WHERE `webhook` = %s LIMIT 1;', (webhook,))
            row = cur.fetchone()
            if row is not None:
                bot_id = row['id']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return bot_id


def bot_access_token_type(bot_id):
    logger.info("bot_access_token_type(bot_id=%s)" % (bot_id,))

    access_token = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `access_token` FROM `bots` WHERE `id` = %s LIMIT 1;', (bot_id,))
            row = cur.fetchone()
            if row is not None:
                access_token = row['access_token']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return access_token


def bot_title_type(bot_id):
    logger.info("bot_title_type(bot_id=%s)" % (bot_id,))

    title = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `title` FROM `bots` WHERE `id` = %s LIMIT 1;', (bot_id,))
            row = cur.fetchone()
            if row is not None:
                title = row['title']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return title


def write_log(sender_id, bot_id, message):
    logger.info("write_log(sender_id=%s, bot_id=%s, message=%s)" % (sender_id, bot_id, message))

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('INSERT INTO `logs` (`id`, `bot_id`, `fb_psid`, `message`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (bot_id, sender_id, json.dumps(message)))
            conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


def app_store(bot_id):
    logger.info("app_store(bot_id=%s)" % (bot_id,))

    rating = 0
    previews = None

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `rating`, `preview_urls` FROM `app_store` WHERE `bot_id` = %s LIMIT 1;', (bot_id,))
            row = cur.fetchone()
            if row is not None:
                rating = row['rating']
                previews = row['preview_urls'].split("|")

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return (rating, previews)


def carousel_cards(bot_id):
    logger.info("carousel_cards(bot_id=%s)" % (bot_id,))

    cards = []
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `title`, `subtitle`, `image_url`, `card_url`, `media_url` FROM `cards` WHERE `bot_id` = %s AND `enabled` = 1 ORDER BY `sort`;', (bot_id,))
            for row in cur.fetchall():
                cards.append({
                    'id'       : row['id'],
                    'title'    : row['title'],
                    'subtitle' : row['subtitle'],
                    'image_url': row['image_url'],
                    'card_url' : row['card_url'],
                    'media_url': row['media_url'] if len(row['media_url']) > 0 else None
                })

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    if len(cards) == 0:
        cards = [{
            'id'       : 0,
            'title'    : "Video Carousel",
            'subtitle' : "",
            'image_url': "http://via.placeholder.com/640x320",
            'buttons'  : [{ 'type' : "element_share" }],
            'card_url' : None,
            'media_url': None
        }]

    logger.info("cards=%s" % (cards))
    return cards


    # cards = [[{
    #     'id'       : 1,
    #     'title'    : "98 Turk",
    #     'subtitle' : "Starts at 5pm. Ends at 6pm",
    #     'image_url': "https://imgur.com/0hfrKK1.png",
    #     'card_url' : "http://example.com"
    # }, {
    #     'id'       : 2,
    #     'title'    : "Black Cat",
    #     'subtitle' : "Starts at 4pm. Ends at 6pm",
    #     'image_url': "https://i.imgur.com/qZF2Ix5.png",
    #     'card_url' : "http://example.com"
    # }, {
    #     'id'       : 3,
    #     'title'    : "Mezcalito",
    #     'subtitle' : "Starts at 4pm. Ends at 7pm",
    #     'image_url': "https://i.imgur.com/mAqjn4w.png",
    #     'card_url' : "http://example.com"
    # }, {
    #     'id'       : 4,
    #     'title'    : "The Treasury",
    #     'subtitle' : "Starts at 4pm. Ends at 5:30",
    #     'image_url': "https://i.imgur.com/LiqtzoF.png",
    #     'card_url' : "http://example.com"
    # }], [{
    #     'id'       : 1,
    #     'title'    : "Jenny (@jennyInsta)",
    #     'subtitle' : "",
    #     'image_url': "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/ccbe43e029714325635391627bad51cd/hair1.jpg",
    #     'card_url' : None
    # }, {
    #     'id'       : 2,
    #     'title'    : "Megan (@julieInsta)",
    #     'subtitle' : "",
    #     'image_url': "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/e466f78fcc08ba52f7a258fc57072a67/hair2.jpg",
    #     'card_url' : None
    # }, {
    #     'id'       : 3,
    #     'title'    : "Julie (@julieInsta)",
    #     'subtitle' : "",
    #     'image_url': "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/a71fd2bb3b8608e9b2869ecfe5e0bf0f/hair3.jpg",
    #     'card_url' : None
    # }, {
    #     'id'       : 4,
    #     'title'    : "Kyle (@julieInsta)",
    #     'subtitle' : "",
    #     'image_url': "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/a080d2c164f6d048d3ec416e0149b88c/hair4.jpg",
    #     'card_url' : None
    # }, {
    #     'id'       : 5,
    #     'title'    : "Mandy (@mandyInsta)",
    #     'subtitle' : "",
    #     'image_url': "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/33d1124b002d14d215dc04ecc6c2f52a/hair5.jpg",
    #     'card_url' : None
    # }], [{
    #     'id'       : 1,
    #     'title'    : "Video I",
    #     'subtitle' : "",
    #     'image_url': "http://via.placeholder.com/640x320",
    #     'card_url' : None
    # }, {
    #     'id'       : 2,
    #     'title'    : "Video II",
    #     'subtitle' : "",
    #     'image_url': "http://via.placeholder.com/640x320",
    #     'card_url' : None
    # }, {
    #     'id'       : 3,
    #     'title'    : "Video III",
    #     'subtitle' : "",
    #     'image_url': "http://via.placeholder.com/640x320",
    #     'card_url' : None
    # }]]
    #
    # return cards[min(max(0, bot_id - 1), len(cards) - 1)]


def get_user_fb_psid(user_id):
    logger.info("get_user_fb_psid(user_id=%s)" % (user_id,))

    fb_psid = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `fb_psid` FROM `users` WHERE `id` = %s LIMIT 1;', (user_id,))
            row = cur.fetchone()
            if row is not None:
                fb_psid = row['fb_psid']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return fb_psid


def get_user_id(sender_id):
    logger.info("get_user_id(sender_id=%s)" % (sender_id,))

    user_id = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `users` WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
            row = cur.fetchone()
            if row is not None:
                user_id = row['id']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return user_id


def set_user(sender_id, bot_id):
    logger.info("set_user(sender_id=%s, bot_id=%s)" % (sender_id, bot_id))

    params = {
        'fields'      : "first_name,last_name,profile_pic,locale,timezone,gender,is_payment_enabled",
        'access_token': bot_access_token_type(bot_id)
    }

    logger.info("params=%s" % (params,))
    response = requests.get("https://graph.facebook.com/v2.6/{recipient_id}".format(recipient_id=sender_id), params=params)

    graph = response.json()
    logger.info("graph=%s" % (graph,))
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `users` WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
            row = cur.fetchone()
            if row is None:
                cur.execute('INSERT INTO  `users` (`id`, `bot_id`, `fb_psid`, `first_name`, `last_name`, `image_url`, `last_active`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, UTC_TIMESTAMP(), UTC_TIMESTAMP());', (bot_id, sender_id, "" if 'first_name' not in graph else graph['first_name'], "" if 'last_name' not in graph else graph['last_name'], "" if 'profile_pic' not in graph else graph['profile_pic']))
                conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


def get_user_bot_id(sender_id):
    logger.info("get_user_bot_id(sender_id=%s)" % (sender_id,))

    bot_id = 0
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `bot_id` FROM `users` WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
            row = cur.fetchone()
            if row is not None:
                bot_id = row['bot_id']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return bot_id

def get_user_name(sender_id):
    logger.info("get_user_name(sender_id=%s)" % (sender_id,))

    f_name = None
    l_name = None

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `first_name`, `last_name` FROM `users` WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
            row = cur.fetchone()
            if row is not None:
                f_name = row['first_name']
                l_name = row['last_name']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return (f_name, l_name)



def get_zipcode(sender_id):
    logger.info("get_zipcode(sender_id=%s)" % (sender_id,))

    zipcode = None
    # conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    # try:
    #     with conn:
    #         cur = conn.cursor(mdb.cursors.DictCursor)
    #         cur.execute('SELECT `zipcode` FROM `users` WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
    #         row = cur.fetchone()
    #         if row is not None:
    #             zipcode = row['zipcode']
    #
    # except mdb.Error, e:
    #     logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
    #
    # finally:
    #     if conn:
    #         conn.close()

    return zipcode


def set_zipcode(sender_id, zipcode=None):
    logger.info("set_zipcode(sender_id=%s, zipcode=%s)" % (sender_id, zipcode))

    # conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    # try:
    #     with conn:
    #         cur = conn.cursor(mdb.cursors.DictCursor)
    #         cur.execute('UPDATE `users` SET `zipcode` = %s WHERE `fb_psid` = %s LIMIT 1;', (zipcode or "", sender_id))
    #         conn.commit()
    #
    # except mdb.Error, e:
    #     logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
    #
    # finally:
    #     if conn:
    #         conn.close()


def get_flipped(sender_id):
    logger.info("get_flipped(sender_id=%s)" % (sender_id,))

    epoch = 0
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `last_flip` FROM `users` WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
            row = cur.fetchone()
            logger.info("row=%s" % (row))
            if row is not None and row['last_flip'] is not None:
                epoch = time.mktime(row['last_flip'].timetuple())

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return epoch


def set_flipped(sender_id):
    logger.info("set_flipped(sender_id=%s)" % (sender_id,))

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('UPDATE `users` SET `last_flip` = UTC_TIMESTAMP() WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
            conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


def get_email(sender_id):
    logger.info("get_email(sender_id=%s)" % (sender_id,))

    email = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `email` FROM `users` WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
            row = cur.fetchone()
            if row is not None:
                email = row['email']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return email


def set_email(sender_id, email=None):
    logger.info("set_email(sender_id=%s, email=%s)" % (sender_id, email))

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('UPDATE `users` SET `email` = %s WHERE `fb_psid` = %s LIMIT 1;', (email, sender_id))
            conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


def get_optout(sender_id):
    logger.info("get_optout(sender_id=%s)" % (sender_id,))

    optout = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `optout` FROM `users` WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
            row = cur.fetchone()
            if row is not None:
                optout = row['optout']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return optout == 1


def set_optout(sender_id, optout=True):
    logger.info("set_email(sender_id=%s, optout=%s)" % (sender_id, optout))

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('UPDATE `users` SET `optout` = %s WHERE `fb_psid` = %s LIMIT 1;', (1 if optout is True else 0, sender_id))
            conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

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

    bot_id = get_user_bot_id(sender_id)
    if bot_id == Const.BOT_TYPE_HAPPYHOUR or bot_id == Const.BOT_TYPE_TOPSTYLE:
        if bot_id == Const.BOT_TYPE_HAPPYHOUR:
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
            'payload'     : "MAIN_MENU"
        })

    else:
        quick_replies = [{
            'content_type': "text",
            'title'       : "Get {bot_title}".format(bot_title=bot_title_type(bot_id)),
            'payload'     : "LANDING_URL"
        }, {
            'content_type': "text",
            'title'       : "Next Video",
            'payload'     : "NEXT_VIDEO"
        }, {
            'content_type': "text",
            'title'       : "Screenshots",
            'payload'     : "APP_SCREENSHOTS"
        }]

    return quick_replies


def build_flip_element(sender_id):
    logger.info("build_flip_element(sender_id=%s)" % (sender_id,))

    element = None
    bot_id = get_user_bot_id(sender_id)
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `title`, `description`, `image_url`, `terms`, `email` FROM `giveaways` WHERE `bot_id` = %s LIMIT 1;', (bot_id,))
            row = cur.fetchone()
            if row is not None:
                element = {
                    'title'    : row['title'],
                    'subtitle' : row['description'],
                    'image_url': row['image_url'],
                    'item_url' : None,
                    'buttons'  : [{
                        'type'   : "postback",
                        'payload': "FLIP-{giveaway_id}".format(giveaway_id=row['id']),
                        'title'  : "Tap Here to Win"
                    }]
                }

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return element


def build_carousel_elements(sender_id):
    logger.info("build_carousel_elements(sender_id=%s)" % (sender_id,))

    bot_id = get_user_bot_id(sender_id)
    elements = []
    for element in carousel_cards(get_user_bot_id(sender_id)):
        # if bot_id == 15:
        #     elements.append({
        #         'title'    : element['title'],
        #         'subtitle' : element['subtitle'] or "",
        #         'image_url': "{image_url}?r={rand}".format(image_url=element['image_url'], rand=random.uniform(0, 1)),
        #         'item_url' : None,
        #         'buttons'  : [{
        #             'type'   : "postback",
        #             'payload': "PLAY_VIDEO-{card_id}".format(card_id=element['id']),
        #             'title'  : "Play Now"
        #         }]
        #     })
        #
        # else:
        elements.append({
            'title'    : element['title'],
            'subtitle' : element['subtitle'] or "",
            'image_url': "{image_url}?r={rand}".format(image_url=element['image_url'], rand=random.uniform(0, 1)),
            'item_url' : None,
            'buttons'  : [{
                'type'                : "web_url",
                'url'                 : "http://outro.chat/landing/{user_id}/{card_id}".format(user_id=get_user_id(sender_id), card_id=element['id']),
                'title'               : "Play Now",
                'webview_height_ratio': "compact"
            }] if element['media_url'] is not None else None
        })

    return elements


def send_welcome(sender_id, bot_id):
    logger.info("send_welcome(sender_id=%s, bot_id=%s)" % (sender_id, bot_id))

    set_user(sender_id, bot_id)

    if bot_id == Const.BOT_TYPE_HAPPYHOUR:
        image_url = "https://trello-attachments.s3.amazonaws.com/596cff877f832eab7df9b621/59790100fd912da6f9a952ad/9a11e8d50e223bc2c765f4e7f83f1cc7/flip_happyhour.gif"

    elif bot_id == Const.BOT_TYPE_TOPSTYLE:
        image_url = "https://i.imgur.com/1o4YoY1.gif"

    else:
        image_url = "http://via.placeholder.com/640x320"

    f_name, l_name = get_user_name(sender_id)
    send_text(
        recipient_id=sender_id,
        message_text="Hi {first_name}, do you want to watch videos on {bot_title} for iOS and Android?".format(first_name=f_name, bot_title=bot_title_type(get_user_bot_id(sender_id))),
        quick_replies=[{
            'content_type': "text",
            'title'       : "Yes",
            'payload'     : "WELCOME_YES"
        }, {
            'content_type': "text",
            'title'       : "No",
            'payload'     : "WELCOME_NO"
        }]
    )


def send_flip(sender_id, item_id):
    logger.info("send_flip(sender_id=%s, item_id=%s)" % (sender_id, item_id))

    if get_flipped(sender_id) >= int(time.time()) - 86400:
        send_text(sender_id, "Already flipped today!")
        send_default_carousel(sender_id)

    else:
        outcome = random.uniform(0, 100) >= 99

        send_image(sender_id, "http://192.241.197.211/bots/6p_fingerprint-1.gif")
        time.sleep(2)

        if outcome is True:
            set_email(sender_id, "_{PENDING}_")
            send_text(sender_id, "You Won! A 1 month Subscription to Passkey. Please enter your email address.", [build_cancel_button()])

        else:
            send_text(sender_id, "You Lost. Enter your email address for more details on how you could win.", build_quick_replies(sender_id))


def send_item_card(sender_id, item_id, tag=True):
    logger.info("send_item_card(sender_id=%s, item_id=%s, tag=%s)" % (sender_id, item_id, tag))

    bot_id = get_user_bot_id(sender_id)
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `title`, `subtitle`, `image_url`, `card_url`, `media_url` FROM `cards` WHERE `id` = %s AND `enabled` = 1 LIMIT 1;', (item_id,))
            row = cur.fetchone()
            if row is not None:
                # if bot_id == 15:
                #     send_card(
                #         recipient_id=sender_id,
                #         title=row['title'],
                #         image_url="{image_url}?r={rand}".format(image_url=row['image_url'], rand=random.uniform(0, 1)),
                #         buttons=None if len(row['media_url']) == 0 else [{
                #             'type'   : "postback",
                #             'payload': "PLAY_VIDEO-{card_id}".format(card_id=row['id']),
                #             'title'  : "Play Now"
                #         }]
                #     )
                #
                # else:
                send_card(
                    recipient_id=sender_id,
                    title=row['title'],
                    image_url="{image_url}?r={rand}".format(image_url=row['image_url'], rand=random.uniform(0, 1)),
                    card_url=None if len(row['media_url']) == 0 else "http://outro.chat/landing/{user_id}/{card_id}".format(user_id=get_user_id(sender_id), card_id=item_id),
                    buttons=None if len(row['media_url']) == 0 else [{
                        'type'                : "web_url",
                        'url'                 : "http://outro.chat/landing/{user_id}/{card_id}".format(user_id=get_user_id(sender_id), card_id=item_id),
                        'title'               : "Play Now",
                        'webview_height_ratio': "compact"
                    }, {
                        'type': "element_share",
                    }]
                )

            else:
                send_card(
                    recipient_id=sender_id,
                    title="Video Placeholder",
                    image_url="http://via.placeholder.com/640x320",
                    buttons=[{ 'type' : "element_share" }],
                    quick_replies=build_quick_replies(sender_id)
                )

            if tag is True:
                cur.execute('SELECT `tag_line` FROM `bots` WHERE `id` = %s LIMIT 1;', (bot_id,))
                row = cur.fetchone()
                if row is not None:
                    send_text(sender_id, row['tag_line'], build_quick_replies(sender_id))

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


def send_default_carousel(sender_id, amount=3):
    logger.info("send_default_carousel(sender_id=%s amount=%s)" % (sender_id, amount))

    if get_user_bot_id(sender_id) == Const.BOT_TYPE_HAPPYHOUR or get_user_bot_id(sender_id) == Const.BOT_TYPE_TOPSTYLE:
        elements = []
        if get_flipped(sender_id) <= int(time.time()) - 86400:
            elements.append(build_flip_element(sender_id))

        send_carousel(
            recipient_id=sender_id,
            elements=elements + build_carousel_elements(sender_id),
            quick_replies=build_quick_replies(sender_id)
        )

    else:
        flip_element = build_flip_element(sender_id)
        if flip_element is not None:
            send_carousel(
                recipient_id=sender_id,
                elements=[build_flip_element(sender_id)] + build_carousel_elements(sender_id),
                quick_replies=build_quick_replies(sender_id)
            )

        else:
            send_carousel(
                recipient_id=sender_id,
                elements=build_carousel_elements(sender_id),
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
    bot_id = bot_webhook_type(bot_webhook)
    data = request.get_json()

    if bot_id == 0:
        return "OK", 200

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

                # send_text(sender_id, "{bot_title} is down for maintenance.".format(bot_title=bot_title_type(bot_id)))
                # return "OK", 200

                # ------- REFERRAL MESSAGE
                referral = None if 'referral' not in messaging_event else None if 'ref' not in messaging_event['referral'] else messaging_event['referral']['ref'].encode('ascii', 'ignore')
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
                write_log(sender_id, bot_id, message)

                conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
                try:
                    with conn:
                        cur = conn.cursor(mdb.cursors.DictCursor)
                        cur.execute('UPDATE `users` SET `last_active` = UTC_TIMESTAMP() WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
                        conn.commit()

                except mdb.Error, e:
                    logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

                finally:
                    if conn:
                        conn.close()

                if payload is not None:
                    session['payload'] = payload
                    handle_payload(sender_id, bot_id, payload)

                if referral is not None:
                    logger.info("REFERRAL ---> %s", (referral,))
                    handle_referral(sender_id, bot_id, referral[1:])


                if payload is None and referral is None:
                    # ------- TYPED TEXT MESSAGE
                    if message is not None and 'text' in message:
                        if get_user_bot_id(sender_id) is None or get_user_bot_id(sender_id) == 0:
                            send_welcome(sender_id, bot_id)

                        handle_text_reply(sender_id, message['text'])

    return "OK", 200


# =- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


@app.route('/player/', methods=['POST'])
def player():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/player/'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.PLAYER_TOKEN:
        logger.info("TOKEN VALID!")

        if 'user_id' in request.form and 'card_id' in request.form:
            user_id = request.form['user_id']
            card_id = request.form['card_id']
            logger.info("user_id=%s, card_id=%s" % (user_id, card_id))

            fb_psid = get_user_fb_psid(user_id)
            bot_id = get_user_bot_id(fb_psid)

            rating, previews = app_store(bot_id)


            if rating != 0:
                send_text(fb_psid, "Ok, Great! {bot_title} is a {rating:.1f} ⭐️ app!".format(bot_title=bot_title_type(bot_id), rating=rating))

            if previews is not None:
                send_image(fb_psid, random.choice(previews))

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('SELECT `media_url` FROM `cards` WHERE `id` = %s LIMIT 1;', (card_id,))
                    row = cur.fetchone()
                    if row is not None:
                        send_video(
                            recipient_id=fb_psid,
                            url=row['media_url'],
                            quick_replies=build_quick_replies(fb_psid)
                        )

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

    return "OK", 200


# =- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


def handle_referral(sender_id, bot_id, deeplink=None):
    logger.info("handle_referral(sender_id=%s, bot_id=%s, deeplink=%s)" % (sender_id, bot_id, deeplink))

    if re.search(r'^(\d+)$', deeplink):
        tracking_id = re.match(r'^(?P<tracking_id>\d+)$', deeplink).group('tracking_id')

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('UPDATE `users` SET `tracking_id` = %s WHERE `fb_psid` = %s LIMIT 1;', (tracking_id, sender_id,))
                conn.commit()

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


def handle_payload(sender_id, bot_id, payload):
    logger.info("handle_payload(sender_id=%s, bot_id=%s, payload=%s)" % (sender_id, bot_id, payload))

    if payload == "WELCOME_MESSAGE":
        send_welcome(sender_id, bot_id)

    elif payload == "WELCOME_YES":
        rating, previews = app_store(bot_id)

        send_text(sender_id, "Ok, Great! {bot_title} is a {rating:.1f} ⭐️ app!".format(bot_title=bot_title_type(bot_id), rating=rating))
        send_image(sender_id, random.choice(previews))

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('SELECT `id` FROM `cards` WHERE `bot_id` = %s ORDER BY RAND() LIMIT 1;', (bot_id,))
                row = cur.fetchone()
                if row is not None:
                    send_item_card(sender_id, row['id'], False)
                else:
                    send_card(
                        recipient_id=sender_id,
                        title="Video Placeholder",
                        image_url="http://via.placeholder.com/640x320",
                        buttons=[{ 'type' : "element_share" }],
                        quick_replies=build_quick_replies(sender_id)
                    )

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


    elif payload == "WELCOME_NO":
        send_text(sender_id, "Ok, you can always tap Get {bot_title} in the main menu to learn more!".format(bot_title=bot_title_type(bot_id)), build_quick_replies(sender_id))

    elif payload == "ZIPCODE":
        set_zipcode(sender_id, "_{PENDING}_")
        send_text(sender_id, "Please enter your Zip Code to receive updates on daily happy hours in your area.", [build_cancel_button()])

    elif payload == "MAIN_MENU":
        send_default_carousel(sender_id)

    elif payload == "FLIP":
        send_flip(sender_id, 1)

    elif payload == "NEXT_VIDEO":
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('SELECT `id` FROM `cards` WHERE `bot_id` = %s ORDER BY RAND() LIMIT 1;', (bot_id,))
                row = cur.fetchone()
                if row is not None:
                    send_item_card(sender_id, row['id'])
                else:
                    send_card(
                        recipient_id=sender_id,
                        title="Video Placeholder",
                        image_url="http://via.placeholder.com/640x320",
                        buttons=[{ 'type' : "element_share" }],
                        quick_replies=build_quick_replies(sender_id)
                    )

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


    elif payload == "WEBSITE":
        if bot_id == Const.BOT_TYPE_HAPPYHOUR:
            title = "happyhour.bot"
            card_url = "http://www.happyhour.bot"
            image_url = "https://scontent-sjc2-1.xx.fbcdn.net/v/t1.0-9/20294516_106493256703647_5694536636197485639_n.png?oh=dc6ae511db1644ca247b30f5d16be5a6&oe=5A378726"
        elif bot_id == Const.BOT_TYPE_TOPSTYLE:
            title = "foxandjanesalon.com"
            card_url = "http://www.foxandjanesalon.com"
            image_url = "https://scontent-sjc2-1.xx.fbcdn.net/v/t1.0-9/20294515_254659165032297_7229853044888461966_n.png?oh=2b270114e028ff27a733d85e58a01c53&oe=5A07B2EE"
        else:
            title = "example.com"
            card_url = "http://www.example.com"
            image_url = "https://scontent-sjc2-1.xx.fbcdn.net/v/t1.0-9/20294515_254659165032297_7229853044888461966_n.png?oh=2b270114e028ff27a733d85e58a01c53&oe=5A07B2EE"

        send_card(
            recipient_id=sender_id,
            title=title,
            image_url=image_url,
            card_url=card_url,
            quick_replies=build_quick_replies(sender_id)
        )

    elif payload == "EMAIL":
        set_email(sender_id, "_{PENDING}_")
        send_text(sender_id, "Enter your Email Address now for more information on how to protect your Facebook Account. ", build_quick_replies(sender_id))

    elif payload == "LANDING_URL":
        if bot_id == 12 or bot_id == 13 or bot_id == 15:
            send_card(
                recipient_id=sender_id,
                title="Fingerprint Login",
                image_url="http://192.241.197.211/bots/image.png",
                subtitle="PassKey Password & App Keyboard",
                buttons=[{
                    'type'                : "web_url",
                    'url'                 : "https://taps.io/Bw_GA",
                    'title'               : "Open PassKey",
                    'webview_height_ratio': "full"
                }],
                quick_replies=build_quick_replies(sender_id)
            )
        else:
            rating, previews = app_store(bot_id)

            if rating != 0:
                send_text(sender_id, "Ok, Great! {bot_title} is a {rating:.1f} ⭐️ app!".format(bot_title=bot_title_type(bot_id), rating=rating))

            if previews is not None:
                send_image(sender_id, random.choice(previews))

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('SELECT `id` FROM `cards` WHERE `bot_id` = %s ORDER BY RAND() LIMIT 1;', (bot_id,))
                    row = cur.fetchone()
                    if row is not None:
                        send_item_card(sender_id, row['id'], False)
                    else:
                        send_card(
                            recipient_id=sender_id,
                            title="Video Placeholder",
                            image_url="http://via.placeholder.com/640x320",
                            buttons=[{ 'type' : "element_share" }],
                            quick_replies=build_quick_replies(sender_id)
                        )

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

    elif payload == "APP_SCREENSHOTS":
        rating, previews = app_store(bot_id)

        if previews is not None:
            for preview in previews:
                send_image(sender_id, preview)

    elif payload == "SUPPORT":
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('UPDATE `users` SET `support`= 1 WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
                conn.commit()

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(sender_id, "Please describe your issue to support…", build_quick_replies(sender_id))

    elif re.search(r'^VIEW\-(\d+)$', payload):
        if bot_id != Const.BOT_TYPE_TOPSTYLE:
            send_item_card(sender_id, re.match(r'^VIEW\-(?P<item_id>\d+)$', payload).group('item_id'))

        else:
            send_text(sender_id, "Content not available in demo.", build_quick_replies(sender_id))

    elif re.search(r'^FLIP\-(\d+)$', payload):
        send_flip(sender_id, re.match(r'^FLIP\-(?P<item_id>\d+)$', payload).group('item_id'))

    elif re.search(r'^PLAY_VIDEO\-(\d+)$', payload):
        card_id = re.match(r'^PLAY_VIDEO\-(?P<card_id>\d+)$', payload).group('card_id')
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('INSERT INTO `clicks` (`id`, `user_id`, `card_id`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());', (get_user_id(sender_id), card_id))
                conn.commit()
                cur.execute('SELECT `id`, `title`, `subtitle`, `image_url`, `card_url`, `media_url` FROM `cards` WHERE `id` = %s AND `enabled` = 1 LIMIT 1;', (card_id,))
                row = cur.fetchone()
                if row is not None:
                    send_video(sender_id, row['media_url'])

                else:
                    send_card(
                        recipient_id=sender_id,
                        title="Video Placeholder",
                        image_url="http://via.placeholder.com/640x320",
                        buttons=[{ 'type' : "element_share" }],
                        quick_replies=build_quick_replies(sender_id)
                    )

                cur.execute('SELECT `tag_line` FROM `bots` WHERE `id` = %s LIMIT 1;', (bot_id,))
                row = cur.fetchone()
                if row is not None:
                    send_text(sender_id, row['tag_line'], build_quick_replies(sender_id))

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

    elif payload == "CANCEL":
        set_email(sender_id)
        set_zipcode(sender_id)
        send_default_carousel(sender_id)

    elif payload == "BROADCAST_YES":
        send_text(sender_id, "Awesome! Have you connected Facebook to PassKey yet?", build_quick_replies(sender_id))

    return "OK", 200


def handle_text_reply(sender_id, message_text):
    logger.info("handle_text_reply(sender_id=%s, message_text=%s)" % (sender_id, message_text))

    support = False
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `users` WHERE `fb_psid` = %s AND `support` = 1 LIMIT 1;', (sender_id,))
            row = cur.fetchone()
            if row is not None:
                support = True

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    bot_id = get_user_bot_id(sender_id)
    if message_text.lower() in Const.RESERVED_ALERT_REPLIES.split("|"):
        send_text(sender_id, "It's 4pm. Time to Get Happy!", build_quick_replies(sender_id))

    elif message_text.lower() in Const.RESERVED_SUPPORT_REPLIES.split("|"):
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('UPDATE `users` SET `support`= 1 WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
                conn.commit()

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(sender_id, "Enter your Twitter username now.", build_quick_replies(sender_id))

    elif message_text.lower() in Const.RESERVED_OPTOUT_REPLIES.split("|"):
        set_optout(sender_id)
        send_text(sender_id, "You have opted out.")

    elif get_email(sender_id) == "_{PENDING}_":
        if re.search(r'^.+\@.+\..*$', message_text) is not None:
            set_flipped(sender_id)
            set_email(sender_id, message_text)
            send_text(sender_id, "Your Email Address has been received and we will message you details shortly.", build_quick_replies(sender_id))

        else:
            send_text(sender_id, "Invalid email", [build_cancel_button()])

    elif get_zipcode(sender_id) == "_{PENDING}_":
        if re.search(r'^\d+$', message_text) is not None:
            set_zipcode(sender_id, message_text)
            send_text(sender_id, "{zipcode} saved".format(zipcode=message_text), build_quick_replies(sender_id))

        else:
            send_text(sender_id, "Invalid zipcode", [build_cancel_button()])

    elif support is True:
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('SELECT `title`, `avatar_url` FROM `bots` WHERE `id` = %s LIMIT 1', (bot_id,))
                row = cur.fetchone()
                if row is not None:
                    payload = {
                        'channel'  : "#outro-support",
                        'username ': row['title'] or "",
                        'icon_url' : row['avatar_url'] or "",
                        'text'     : "*Support Request*\n _{fb_psid}_ says:\n{message_text}".format(fb_psid=sender_id, message_text=message_text)
                    }
                    response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})
                    #send_text(sender_id, "Your message has been sent to support.", build_quick_replies(sender_id))
                    send_text(sender_id, "Your Twitter username has been submitted.", build_quick_replies(sender_id))

                cur.execute('UPDATE `users` SET `support` = 0 WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
                conn.commit()

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


    else:
        send_default_carousel(sender_id)

    return "OK", 200


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

    send_message(get_user_bot_id(recipient_id), json.dumps(data))
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

    send_message(get_user_bot_id(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_typing_indicator(recipient_id, is_typing):
    data = {
        'recipient'    : {
            'id': recipient_id
        },
        'sender_action': "typing_on" if is_typing else "typing_off"
    }

    send_message(get_user_bot_id(recipient_id), json.dumps(data))


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

    send_message(get_user_bot_id(recipient_id), json.dumps(data))
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

    send_message(get_user_bot_id(recipient_id), json.dumps(data))
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

    send_message(get_user_bot_id(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_message(bot_id, payload):
    logger.info("send_message(bot_id=%s, payload=%s)" % (bot_id, payload))

    response = requests.post(
        url="https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=bot_access_token_type(bot_id)),
        headers={'Content-Type': "application/json"},
        data=payload
    )
    logger.info("SEND MESSAGE (%s) response: %s" % ("https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=bot_access_token_type(bot_id)), response.json()))

    return True



if __name__ == '__main__':
    logger.info("Firin up FbBot using verify token [%s]." % (Const.VERIFY_TOKEN))
    app.run(debug=True)
