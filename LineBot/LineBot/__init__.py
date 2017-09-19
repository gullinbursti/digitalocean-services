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
import subprocess
import sys
import threading
import time

from datetime import datetime
from StringIO import StringIO
from urllib import urlencode

import MySQLdb as mdb
import pycurl
import requests
import speech_recognition as sr
import urllib

from flask import Flask, escape, request, session
from flask_cors import CORS, cross_origin
from wit import Wit

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

wit_client = Wit(access_token=Const.WIT_ACCESS_TOKEN)


# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


class VideoAudioRenderer(threading.Thread):
    def __init__(self, src_url, out_mp3):
        threading.Thread.__init__(self)
        self.src_url = src_url
        self.out_mp3 = out_mp3

    def run(self):
        p = subprocess.Popen(
            # ('/usr/bin/ffmpeg -i %s -q:a 0 -map a %s' % (self.src_url, self.out_mp3)).split(),
            ('/usr/bin/ffmpeg -i %s -vn -acodec pcm_s16le -ar 44100 -ac 1 %s' % (self.src_url, self.out_mp3)).split(),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = p.communicate()


class VideoMetaData(threading.Thread):
    def __init__(self, src_url):
        threading.Thread.__init__(self)
        self.src_url = src_url
        self.info = None

    def run(self):
        p = stdout, stderr = subprocess.Popen(
            ('/usr/bin/ffprobe %s' % (self.src_url)).split(),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        ).communicate()

        list = stderr.split("\n")
        dur = re.sub(r'\s{2,}', "", [s for s in list if "Duration:" in s][0]).split()[1][:-1]
        duration = (float(dur.split(":")[0]) * 3600) + (float(dur.split(":")[1]) * 60) + float(dur.split(":")[2])
        size = [s for s in list if "Stream" in s][0].split(", ")[2].split()[0]
        frmt = [s for s in list if "Stream" in s][0].split(", ")[0].split()[3]

        self.info = {
            'duration': duration,
            'size'    : (int(size.split("x")[0]), int(size.split("x")[1])),
            'format'  : frmt
        }


# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#
# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#

def copy_remote_asset(src_url, local_file):
    logger.info("copy_remote_asset(src_url=%s, local_file=%s)" % (src_url, local_file))

    with open(local_file, 'wb') as handle:
        response = requests.get(src_url, stream=True)
        if response.status_code == 200:
            for block in response.iter_content(1024):
                handle.write(block)
        else:
            logger.info("DOWNLOAD FAILED!!! %s" % (response.text))
        del response



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


def app_title_type(bot_id):
    logger.info("app_title_type(bot_id=%s)" % (bot_id,))

    title = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `app_title` FROM `bots` WHERE `id` = %s LIMIT 1;', (bot_id,))
            row = cur.fetchone()
            if row is not None:
                title = row['app_title']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return title


def bot_modules(bot_id):
    logger.info("bot_modules(bot_id=%s)" % (bot_id))

    modules = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `modules` FROM `bots` WHERE `id` = %s LIMIT 1;', (bot_id,))
            row = cur.fetchone()
            if row is not None:
                modules = row['modules']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return modules



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
                cur.execute('INSERT INTO  `users` (`id`, `bot_id`, `fb_psid`, `first_name`, `last_name`, `gender`, `locale`, `timezone`, `image_url`, `last_active`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(), UTC_TIMESTAMP());', (bot_id, sender_id, "" if 'first_name' not in graph else graph['first_name'], "" if 'last_name' not in graph else graph['last_name'], "N" if 'gender' not in graph else graph['gender'][0].upper(), "" if 'locale' not in graph else graph['locale'], "" if 'timezone' not in graph else graph['timezone'], "" if 'profile_pic' not in graph else graph['profile_pic']))
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


def get_user_sentiment(sender_id):
    logger.info("get_user_sentiment(sender_id=%s)" % (sender_id,))

    sentiment = 0
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `sentiment` FROM `users` WHERE `fb_psid` = %s LIMIT 1;', (sender_id,))
            row = cur.fetchone()
            logger.info("row=%s" % (row,))
            if row is not None and row['sentiment'] is not None:
                sentiment = row['sentiment']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return sentiment


def set_user_sentiment(sender_id, value):
    logger.info("set_user_sentiment(sender_id=%s, value=%s)" % (sender_id, value))

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('UPDATE `users` SET `sentiment` = %s WHERE `fb_psid` = %s LIMIT 1;', (value, sender_id,))
            conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


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
    logger.info("set_optout(sender_id=%s, optout=%s)" % (sender_id, optout))

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

    quick_replies = [{
        'content_type': "text",
        'title'       : "Get {app_title}".format(app_title="App" if app_title_type(bot_id) == "" else app_title_type(bot_id)),
        'payload'     : "LANDING_URL"
    }]

    if bot_modules(bot_id) == 0:
        quick_replies.append({
            'content_type': "text",
            'title'       : "Next Video",
            'payload'     : "NEXT_VIDEO"
        })

    elif bot_modules(bot_id) == 1:
        quick_replies.append({
            'content_type': "text",
            'title'       : "Next Question",
            'payload'     : "NEXT_SURVEY"
        })

    elif bot_modules(bot_id) == 2:
        quick_replies.append({
            'content_type': "text",
            'title'       : "Next",
            'payload'     : "NEXT_LIST"
        })

    elif bot_modules(bot_id) == 4:
        quick_replies.append({
            'content_type': "text",
            'title'       : "A/B Test",
            'payload'     : "AB_TEST"
        })

    elif bot_modules(bot_id) == 8:
        quick_replies.append({
            'content_type': "text",
            'title'       : "Next",
            'payload'     : "NEXT_RATING"
        })

    # quick_replies.append({
    #     'content_type': "text",
    #     'title'       : "Screenshots",
    #     'payload'     : "APP_SCREENSHOTS"
    # })

    quick_replies.append({
        'content_type': "text",
        'title'       : "Video Upload",
        'payload'     : "SEND_VIDEO"
    })

    return quick_replies


def build_card_element(title, subtitle=None, image_url=None, item_url=None, buttons=None):
    logger.info("build_card_element(title=%s, subtitle=%s, image_url=%s, item_url=%s, buttons=%s)" % (title, subtitle, image_url, item_url, buttons))

    element = {
        'title'    : title,
        'subtitle' : subtitle or "",
        'image_url': image_url,
        'item_url' : item_url
    }

    if buttons is not None:
        element['buttons'] = buttons

    return element


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

    # f_name, l_name = get_user_name(sender_id)
    # send_text(sender_id, "Welcome to {bot_title}. You can opt out anytime by texting Optout.".format(bot_title=bot_title_type(get_user_bot_id(sender_id))))
    send_text(sender_id, "Welcome to {app_title}. You can opt out anytime by texting Optout.".format(app_title=app_title_type(get_user_bot_id(sender_id))))

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `welcome_msg` FROM `bots` WHERE `id` = %s LIMIT 1;', (bot_id,))
            row = cur.fetchone()
            if row is not None and row['welcome_msg'] != "":
                send_text(
                    recipient_id=sender_id,
                    message_text=row['welcome_msg'],
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

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


    modules = bot_modules(bot_id)
    if modules == 1:
        survey = []
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('SELECT `id`, `video_url`, `topic`, `answer_1`, `answer_2`, `answer_3`  FROM `surveys` WHERE `bot_id` = %s ORDER BY `sort`;', (bot_id,))
                for row in cur.fetchall():
                    logger.info("MODULES[%s] : %s" % (bot_id, modules))
                    survey.append({
                        'id'        : row['id'],
                        'topic'     : row['topic'],
                        'video_url' : row['video_url'],
                        'answers'   : [
                            row['answer_1'],
                            row['answer_2'],
                            row['answer_3']
                        ]
                    })

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        if len(survey) > 0:
            send_video(sender_id, survey[0]['video_url'])
            send_text(
                recipient_id=sender_id,
                message_text="{topic}".format(topic=survey[0]['topic']),
                quick_replies=[
                    {
                        'content_type': "text",
                        'title'       : survey[0]['answers'][0],
                        'payload'     : "SURVEY-{survey_id}-0".format(survey_id=survey[0]['id'])
                    }, {
                        'content_type': "text",
                        'title'       : survey[0]['answers'][1],
                        'payload'     : "SURVEY-{survey_id}-1".format(survey_id=survey[0]['id'])
                    }, {
                        'content_type': "text",
                        'title'       : survey[0]['answers'][2],
                        'payload'     : "SURVEY-{survey_id}-2".format(survey_id=survey[0]['id'])
                    }, {
                        'content_type': "text",
                        'title'       : "Get {app_title}".format(app_title=app_title_type(bot_id)),
                        'payload'     : "LANDING_URL"
                    }
                ]
            )

    elif modules == 2:
        send_default_carousel(sender_id)

    elif modules == 4:
        send_default_carousel(sender_id)

    elif modules == 8:
        send_default_carousel(sender_id)


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
            send_text(sender_id, "You Won! A 1 month Subscription to Passkey.", [build_cancel_button()])

        else:
            send_text(sender_id, "You Lost.", build_quick_replies(sender_id))


def send_video_card(sender_id, item_id, tagline=True):
    logger.info("send_video_card(sender_id=%s, item_id=%s, tagline=%s)" % (sender_id, item_id, tagline))

    bot_id = get_user_bot_id(sender_id)
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `title`, `subtitle`, `image_url`, `card_url`, `media_url` FROM `cards` WHERE `id` = %s AND `enabled` = 1 LIMIT 1;', (item_id,))
            row = cur.fetchone()
            if row is not None:
                send_card(
                    recipient_id=sender_id,
                    title=row['title'],
                    subtitle=row['subtitle'],
                    image_url="{image_url}?r={rand}".format(image_url=row['image_url'], rand=random.uniform(0, 1)),
                    card_url=None if len(row['media_url']) == 0 else "http://outro.chat/landing/{user_id}/{card_id}".format(user_id=get_user_id(sender_id), card_id=item_id),
                    buttons=None if len(row['media_url']) == 0 else [{
                        'type'                : "web_url",
                        'url'                 : "http://outro.chat/landing/{user_id}/{card_id}".format(user_id=get_user_id(sender_id), card_id=item_id),
                        'title'               : "Play Now",
                        'webview_height_ratio': "compact"
                    }, {
                        'type': "element_share"
                    }],
                    quick_replies=build_quick_replies(sender_id)
                )

            else:
                send_card(
                    recipient_id=sender_id,
                    title="Video Placeholder",
                    image_url="http://via.placeholder.com/640x320",
                    buttons=[{ 'type' : "element_share" }],
                    quick_replies=build_quick_replies(sender_id)
                )

            if tagline is True:
                cur.execute('SELECT `tag_line` FROM `bots` WHERE `id` = %s LIMIT 1;', (bot_id,))
                row = cur.fetchone()
                if row is not None:
                    send_text(sender_id, row['tag_line'], build_quick_replies(sender_id))

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    send_text(sender_id, "You can also send a text response or video for more content", build_quick_replies(sender_id))


def send_survey_card(sender_id, card=False):
    logger.info("send_survey_card(sender_id=%s, card=%s)" % (sender_id, card))

    bot_id = get_user_bot_id(sender_id)
    if bot_modules(bot_id) == 1:
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                if card is True:
                    cur.execute('SELECT `survey_id` FROM `survey_responses` WHERE `user_id` = %s ORDER BY `added` DESC LIMIT 1;', (get_user_id(sender_id),))
                    row = cur.fetchone()
                    if row is not None:
                        cur.execute('SELECT `id`, `topic`, `title`, `subtitle`, `image_url` FROM `surveys` WHERE `bot_id` = %s AND `id` = %s ORDER BY `sort` LIMIT 1;', (bot_id, row['survey_id']))
                        row = cur.fetchone()
                        if row is not None:
                            send_card(
                                recipient_id=sender_id,
                                title=row['title'],
                                image_url=row['image_url'],
                                subtitle=row['subtitle'],
                                buttons=[{
                                    'type'                : "web_url",
                                    'url'                 : "http://outro.chat/survey/{user_id}/{survey_id}".format(user_id=get_user_id(sender_id), survey_id=row['id']),
                                    'title'               : "Get {app_name}".format(app_name=app_title_type(bot_id)),
                                    'webview_height_ratio': "compact"
                                }, {
                                    'type': "element_share"
                                }],
                                quick_replies=build_quick_replies(sender_id)
                            )

                        else:
                            cur.execute('SELECT `id`, `topic`, `title`, `subtitle`, `image_url` FROM `surveys` WHERE `bot_id` = %s ORDER BY `sort` LIMIT 1;', (bot_id,))
                            row = cur.fetchone()
                            if row is not None:
                                send_card(
                                    recipient_id=sender_id,
                                    title=row['title'],
                                    image_url=row['image_url'],
                                    subtitle=row['subtitle'],
                                    buttons=[{
                                        'type'                : "web_url",
                                        'url'                 : "http://outro.chat/survey/{user_id}/{survey_id}".format(user_id=get_user_id(sender_id), survey_id=row['id']),
                                        'title'               : "Get {app_name}".format(app_name=app_title_type(bot_id)),
                                        'webview_height_ratio': "compact"
                                    }, {
                                        'type': "element_share"
                                    }],
                                    quick_replies=build_quick_replies(sender_id)
                                )

                            else:
                                send_card(
                                    recipient_id=sender_id,
                                    title="Survey Placeholder",
                                    image_url="http://via.placeholder.com/640x320",
                                    subtitle="Subtitle",
                                    buttons=[{
                                        'type'                : "web_url",
                                        'url'                 : "http://outro.chat/survey/{user_id}/{survey_id}".format(user_id=get_user_id(sender_id), survey_id=0),
                                        'title'               : "Get {app_name}".format(app_name=app_title_type(bot_id)),
                                        'webview_height_ratio': "compact"
                                    }, {
                                        'type': "element_share"
                                    }],
                                    quick_replies=build_quick_replies(sender_id)
                                )

                    else:
                        send_card(
                            recipient_id=sender_id,
                            title="Survey Placeholder",
                            image_url="http://via.placeholder.com/640x320",
                            subtitle="Subtitle",
                            buttons=[{
                                'type'                : "web_url",
                                'url'                 : "http://outro.chat/survey/{user_id}/{survey_id}".format(user_id=get_user_id(sender_id), survey_id=0),
                                'title'               : "Get {app_name}".format(app_name=app_title_type(bot_id)),
                                'webview_height_ratio': "compact"
                            }, {
                                'type': "element_share"
                            }],
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


def send_item_card(sender_id, list_id=0, item_id=0):
    logger.info("send_item_card(sender_id=%s, list_id=%s, item_id=%s)" % (sender_id, list_id, item_id))

    bot_id = get_user_bot_id(sender_id)
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `title`, `subtitle`, `image_url`, `button_url` FROM `list_items` WHERE `list_id` = %s AND `enabled` = 1 LIMIT 1;', (item_id,))
            row = cur.fetchone()
            if row is not None:
                send_card(
                    recipient_id=sender_id,
                    title=row['title'],
                    subtitle=row['subtitle'],
                    image_url="{image_url}?r={rand}".format(image_url=row['image_url'], rand=random.uniform(0, 1)),
                    card_url=None if len(row['button_url']) == 0 else "http://outro.chat/list/{user_id}/{item_id}".format(user_id=get_user_id(sender_id), item_id=item_id),
                    buttons=None if len(row['button_url']) == 0 else [{
                        'type'                : "web_url",
                        'url'                 : "http://outro.chat/list/{user_id}/{item_id}".format(user_id=get_user_id(sender_id), item_id=item_id),
                        'title'               : "Open Now",
                        'webview_height_ratio': "compact"
                    }, {
                        'type': "element_share"
                    }],
                    quick_replies=build_quick_replies(sender_id)
                )

            else:
                send_card(
                    recipient_id=sender_id,
                    title="Video Placeholder",
                    image_url="http://via.placeholder.com/640x320",
                    buttons=[{'type': "element_share"}],
                    quick_replies=build_quick_replies(sender_id)
                )

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    send_text(sender_id, "You can also send a text response or video for more content", build_quick_replies(sender_id))


def send_list(sender_id, list_id=0):
    logger.info("send_list(sender_id=%s, list_id=%s)" % (sender_id, list_id))

    bot_id = get_user_bot_id(sender_id)
    if bot_modules(bot_id) == 2:
        list_id = 0
        header_element = {}
        body_elements = []
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('SELECT `id`, `title`, `subtitle`, `image_url`, `button_url` FROM `lists` WHERE `bot_id` = %s LIMIT 1;', (bot_id,))
                row = cur.fetchone()
                if row is not None:
                    list_id = row['id']
                    header_element = build_card_element(
                        title=row['title'],
                        subtitle=row['subtitle'],
                        image_url=row['image_url']
                    )

                    cur.execute('SELECT `id`, `title`, `subtitle`, `image_url`, `button_url` FROM `list_items` WHERE `list_id` = %s ORDER BY `sort`;', (list_id,))
                    for row in cur.fetchall():
                        body_elements.append(build_card_element(
                            title=row['title'],
                            subtitle=row['subtitle'],
                            image_url=row['image_url'],
                            buttons=[{
                                'type'   : "postback",
                                'payload': "LIST_ITEM-{list_id}-{item_id}".format(list_id=list_id, item_id=row['id']),
                                'title'  : "Open Now"
                            }]
                        ))

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_list_card(
            recipient_id=sender_id,
            body_elements=body_elements,
            header_element=header_element,
            quick_replies=build_quick_replies(sender_id)
        )

    send_text(sender_id, "You can also send a text response or video for more content", build_quick_replies(sender_id))


def send_ab_test_card(sender_id):
    logger.info("send_ab_test_card(sender_id=%s)" % (sender_id,))

    bot_id = get_user_bot_id(sender_id)
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `title`, `subtitle`, `image_url` FROM `ab_tests` WHERE `bot_id` = %s AND `enabled` = 1 LIMIT 1;', (bot_id,))
            row = cur.fetchone()
            if row is not None:
                send_card(
                    recipient_id=sender_id,
                    title=row['title'],
                    subtitle=row['subtitle'],
                    image_url=row['image_url'],
                    buttons=[{
                        'type'                : "web_url",
                        'url'                 : "http://outro.chat/ab-test/{user_id}/{test_id}".format(user_id=get_user_id(sender_id), test_id=row['id']),
                        'title'               : "Choose Now",
                        'webview_height_ratio': "tall"
                    }, {
                        'type': "element_share"
                    }],
                    quick_replies=build_quick_replies(sender_id)
                )

            else:
                send_card(
                    recipient_id=sender_id,
                    title="A/B Test Placeholder",
                    image_url="http://via.placeholder.com/640x320",
                    buttons=[{'type': "element_share"}],
                    quick_replies=build_quick_replies(sender_id)
                )

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    send_text(sender_id, "You can also send a text response or video for more content", build_quick_replies(sender_id))


def send_rating_card(sender_id, rating_id=0):
    logger.info("send_rating_card(sender_id=%s, rating_id=%s)" % (sender_id, rating_id))

    bot_id = get_user_bot_id(sender_id)
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `title`, `subtitle`, `image_url` FROM `ratings` WHERE `bot_id` = %s AND `enabled` = 1 ORDER BY RAND() LIMIT 1;', (bot_id,))
            row = cur.fetchone()
            if row is not None:
                send_card(
                    recipient_id=sender_id,
                    title=row['title'],
                    subtitle=row['subtitle'],
                    image_url=row['image_url'],
                    buttons=[{
                        'type'   : "postback",
                        'payload': "RATING-{rating_id}-1".format(rating_id=row['id']),
                        'title'  : "⭐"
                    }, {
                        'type'   : "postback",
                        'payload': "RATING-{rating_id}-2".format(rating_id=row['id']),
                        'title'  : "⭐⭐"
                    }, {
                        'type'   : "postback",
                        'payload': "RATING-{rating_id}-3".format(rating_id=row['id']),
                        'title'  : "⭐⭐⭐"
                    }],
                    quick_replies=build_quick_replies(sender_id)
                )

            else:
                send_card(
                    recipient_id=sender_id,
                    title="Rating Placeholder",
                    image_url="http://via.placeholder.com/640x320",
                    buttons=[{
                        'type'   : "postback",
                        'payload': "RATE-0-1".format(rating_id=row['id']),
                        'title'  : "⭐"
                    }, {
                        'type'   : "postback",
                        'payload': "RATE-0-2".format(rating_id=row['id']),
                        'title'  : "⭐⭐"
                    }, {
                        'type'   : "postback",
                        'payload': "RATE-0-3".format(rating_id=row['id']),
                        'title'  : "⭐⭐⭐"
                    }],
                    quick_replies=build_quick_replies(sender_id)
                )

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    send_text(sender_id, "You can also send a text response or video for more content", build_quick_replies(sender_id))


def send_default_carousel(sender_id, amount=3):
    logger.info("send_default_carousel(sender_id=%s, amount=%s)" % (sender_id, amount))

    if bot_modules(get_user_bot_id(sender_id)) == 2:
        send_carousel(
            recipient_id=sender_id,
            elements=build_carousel_elements(sender_id),
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
                    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
                    try:
                        with conn:
                            cur = conn.cursor(mdb.cursors.DictCursor)
                            cur.execute('INSERT INTO `reads` (`id`, `bot_id`, `fb_psid`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());', (bot_id, messaging_event['sender']['id']))
                            conn.commit()

                    except mdb.Error, e:
                        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

                    finally:
                        if conn:
                            conn.close()
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
                    if message is not None and 'text' in message:
                        response = wit_client.message(message['text'])
                        logger.info("WIT SAYS: %s" % (str(response),))
                        if 'sentiment' in response['entities'] and float(response['entities']['sentiment'][0]['confidence']) >= Const.WIT_CONFIDENCE:
                            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
                            try:
                                with conn:
                                    cur.execute('SELECT `survey_id` FROM `survey_responses` WHERE `user_id` = %s ORDER BY `added` DESC LIMIT 1;', (get_user_id(sender_id),))
                                    row = cur.fetchone()
                                    survey_id = 0
                                    if row is not None:
                                        survey_id = row['survey_id']

                                    cur = conn.cursor(mdb.cursors.DictCursor)
                                    cur.execute('INSERT INTO `sentiments` (`id`, `user_id`, `bot_id`, `media_id`, `source`, `entities`, `sentiment`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP()) ;', (get_user_id(sender_id), bot_id, survey_id, "button", json.dumps(response), 1 if response['entities']['sentiment'][0]['value'] == "positive" else -1))
                                    conn.commit()

                            except mdb.Error, e:
                                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

                            finally:
                                if conn:
                                    conn.close()

                    handle_payload(sender_id, bot_id, payload)

                if referral is not None:
                    logger.info("REFERRAL ---> %s", (referral,))
                    handle_referral(sender_id, bot_id, referral)

                if message is not None and 'attachments' in message:
                    for attachment in message['attachments']:
                        if attachment['type'] == "fallback" and 'text' in message:
                            handle_text_reply(sender_id, message['text'])

                        else:
                            handle_attachment(sender_id, attachment['type'], attachment['payload'])

                if payload is None and referral is None:
                    # ------- TYPED TEXT MESSAGE
                    if message is not None and 'text' in message:
                        if get_user_bot_id(sender_id) is None or get_user_bot_id(sender_id) == 0:
                            send_welcome(sender_id, bot_id)

                        response = wit_client.message(message['text'])
                        logger.info("WIT SAYS: %s" % (str(response),))
                        if 'sentiment' in response['entities'] and float(response['entities']['sentiment'][0]['confidence']) >= Const.WIT_CONFIDENCE:
                            pass
                            # conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
                            # try:
                            #     with conn:
                            #         cur = conn.cursor(mdb.cursors.DictCursor)
                            #         cur.execute('INSERT INTO `sentiments` (`id`, `user_id`, `bot_id`, `source`, `entities`, `sentiment`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, UTC_TIMESTAMP()) ;', (get_user_id(sender_id), bot_id, "text", json.dumps(response), 1 if response['entities']['sentiment'][0]['value'] == "positive" else -1))
                            #         conn.commit()
                            #
                            # except mdb.Error, e:
                            #     logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
                            #
                            # finally:
                            #     if conn:
                            #         conn.close()
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


@app.route('/ab-test/', methods=['POST'])
def ab_test():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/ab-test/'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.AB_TOKEN:
        logger.info("TOKEN VALID!")

        if 'user_id' in request.form and 'test_id' in request.form and 'item_id' in request.form:
            user_id = request.form['user_id']
            test_id = request.form['test_id']
            item_id = request.form['item_id']
            logger.info("user_id=%s, test_id=%s, item_id=%s" % (user_id, test_id, item_id))

            fb_psid = get_user_fb_psid(user_id)
            bot_id = get_user_bot_id(fb_psid)

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('INSERT INTO `ab_test_responses` (`id`, `user_id`, `test_id`, `item_id`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (user_id, test_id, item_id))
                    conn.commit()

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

    return "OK", 200



# =- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


def handle_referral(sender_id, bot_id, deeplink=None):
    logger.info("handle_referral(sender_id=%s, bot_id=%s, deeplink=%s)" % (sender_id, bot_id, deeplink))

    tracking_id = re.match(r'^(?P<tracking_id>.+)$', deeplink).group('tracking_id')
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
        if bot_modules(bot_id) == 2:
            send_list(sender_id)

        elif bot_modules(bot_id) == 4:
            send_ab_test_card(sender_id)

        elif bot_modules(bot_id) == 8:
            send_default_carousel(sender_id)

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
                        send_video_card(sender_id, row['id'], False)
                    else:
                        send_card(
                            recipient_id=sender_id,
                            title="Video Placeholder",
                            image_url="http://via.placeholder.com/640x320",
                            buttons=[{'type': "element_share"}],
                            quick_replies=build_quick_replies(sender_id)
                        )

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()


    elif payload == "WELCOME_NO":
        send_text(sender_id, "Ok, you can always tap Get {bot_title} in the main menu to learn more!".format(bot_title=bot_title_type(bot_id)), build_quick_replies(sender_id))

        if bot_modules(bot_id) == 2:
            send_list(sender_id)

        elif bot_modules(bot_id) == 4:
            send_ab_test_card(sender_id)

        elif bot_modules(bot_id) == 8:
            send_default_carousel(sender_id)

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
                    send_video_card(sender_id, row['id'])
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

    elif payload == "LANDING_URL":
        if bot_modules(bot_id) == 1:
            send_survey_card(sender_id, True)

    elif payload == "APP_SCREENSHOTS":
        rating, previews = app_store(bot_id)

        if previews is not None:
            for preview in previews:
                send_image(sender_id, preview)

        if bot_modules(bot_id) == 1:
            send_survey_card(sender_id)

        elif bot_modules(bot_id) == 2:
            send_list(sender_id)

        elif bot_modules(bot_id) == 4:
            send_ab_test_card(sender_id)

        elif bot_modules(bot_id) == 8:
            send_rating_card(sender_id)

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
            send_video_card(sender_id, re.match(r'^VIEW\-(?P<item_id>\d+)$', payload).group('item_id'))

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
        send_default_carousel(sender_id)

    elif re.search(r'^SURVEY\-(\d+)\-(\d+)$', payload):
        survey_id = re.match(r'^SURVEY\-(?P<survey_id>\d+)\-(\d+)$', payload).group('survey_id')
        answer_id = int(re.match(r'^SURVEY\-(\d+)\-(?P<answer_id>\d+)$', payload).group('answer_id'))

        logger.info("survey_id=%s, answer_id=%s" % (survey_id, answer_id))

        topic = ""
        answer = ""
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('SELECT `topic`, `answer_1`, `answer_2`, `answer_3` FROM `surveys` WHERE `id` = %s LIMIT 1;', (survey_id,))
                row = cur.fetchone()
                if row is not None:
                    topic = row['topic']
                    answer = row['answer_1'] if answer_id == 0 else row['answer_2'] if answer_id == 1 else row['answer_3']

                cur.execute('INSERT INTO `survey_responses` (`id`, `user_id`, `survey_id`, `answer`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (get_user_id(sender_id), survey_id, answer))
                conn.commit()

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        f_name, l_name = get_user_name(sender_id)
        payload = {
            'channel'  : "#outro-reports",
            'username ': "Survey - {bot_title}".format(bot_title=bot_title_type(bot_id)),
            'icon_url' : "",
            'text'     : "*{f_name} {l_name} ({fb_psid})* responsed to *{bot_title}'s* survey \"{topic}\" with _{answer}_".format(f_name=f_name, l_name=l_name, fb_psid=sender_id, bot_title=bot_title_type(bot_id), topic=topic, answer=answer)
        }
        response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})
        send_survey_card(sender_id, survey_id)

    elif payload == "NEXT_SURVEY" or payload == "NEXT_SURVEY-0":
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('SELECT `survey_id` FROM `survey_responses` WHERE `user_id` = %s ORDER BY `added` DESC LIMIT 1;', (get_user_id(sender_id),))
                row = cur.fetchone()
                if row is not None:
                    cur.execute('SELECT `id`, `video_url`, `topic`, `title`, `subtitle`, `image_url`, `answer_1`, `answer_2`, `answer_3` FROM `surveys` WHERE `bot_id` = %s AND `id` > %s ORDER BY `sort` LIMIT 1;', (bot_id, row['survey_id']))
                    row = cur.fetchone()
                    if row is not None:
                        send_video(sender_id, row['video_url'])
                        send_text(
                            recipient_id=sender_id,
                            message_text=row['topic'],
                            quick_replies=[
                                {
                                    'content_type': "text",
                                    'title'       : row['answer_1'],
                                    'payload'     : "SURVEY-{survey_id}-0".format(survey_id=row['id'])
                                }, {
                                    'content_type': "text",
                                    'title'       : row['answer_2'],
                                    'payload'     : "SURVEY-{survey_id}-1".format(survey_id=row['id'])
                                }, {
                                    'content_type': "text",
                                    'title'       : row['answer_3'],
                                    'payload'     : "SURVEY-{survey_id}-2".format(survey_id=row['id'])
                                }, {
                                    'content_type': "text",
                                    'title'       : "Get {app_title}".format(app_title=app_title_type(bot_id)),
                                    'payload'     : "LANDING_URL"
                                }
                            ]
                        )

                    else:
                        cur.execute('SELECT `id`, `video_url`, `topic`, `title`, `subtitle`, `image_url`, `answer_1`, `answer_2`, `answer_3` FROM `surveys` WHERE `bot_id` = %s ORDER BY `sort` LIMIT 1;', (bot_id,))
                        row = cur.fetchone()
                        if row is not None:
                            send_video(sender_id, row['video_url'])
                            send_text(
                                recipient_id=sender_id,
                                message_text=row['topic'],
                                quick_replies=[
                                    {
                                        'content_type': "text",
                                        'title'       : row['answer_1'],
                                        'payload'     : "SURVEY-{survey_id}-0".format(survey_id=row['id'])
                                    }, {
                                        'content_type': "text",
                                        'title'       : row['answer_2'],
                                        'payload'     : "SURVEY-{survey_id}-1".format(survey_id=row['id'])
                                    }, {
                                        'content_type': "text",
                                        'title'       : row['answer_3'],
                                        'payload'     : "SURVEY-{survey_id}-2".format(survey_id=row['id'])
                                    }, {
                                        'content_type': "text",
                                        'title'       : "Get {app_title}".format(app_title=app_title_type(bot_id)),
                                        'payload'     : "LANDING_URL"
                                    }
                                ]
                            )

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

    elif payload == "SEND_VIDEO":
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('SELECT `tag_line` FROM `bots` WHERE `id` = %s LIMIT 1;', (bot_id,))
                row = cur.fetchone()
                if row is not None:
                    send_text(sender_id, row['tag_line'], build_quick_replies(sender_id))

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

    elif payload == "NEXT_LIST":
        send_list(sender_id)

    elif payload == "AB_TEST":
        send_ab_test_card(sender_id)

    elif payload == "NEXT_RATING":
        send_rating_card(sender_id)

    elif re.search(r'^LIST_ITEM-(\d+)-(\d+)$', payload):
        list_id = re.match(r'^LIST_ITEM\-(?P<list_id>\d+)\-(\d+)$', payload).group('list_id')
        item_id = int(re.match(r'^LIST_ITEM\-(\d+)\-(?P<item_id>\d+)$', payload).group('item_id'))

        send_item_card(sender_id, list_id, item_id)

    elif re.search(r'^RATING-(\d+)-(\d+)$', payload):
        rating_id = re.match(r'^RATING\-(?P<rating_id>\d+)\-(\d+)$', payload).group('rating_id')
        score = int(re.match(r'^RATING\-(\d+)\-(?P<score>\d+)$', payload).group('score'))

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('INSERT INTO `rating_responses` (`id`, `user_id`, `rating_id`, `score`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (get_user_id(sender_id), rating_id, score))
                conn.commit()

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(sender_id, "Rating saved", build_quick_replies(sender_id))

    return "OK", 200


def handle_attachment(sender_id, attachment_type, payload):
    logger.info("handle_attachment(sender_id=%s, attachment_type=%s, payload=%s)" % (sender_id, attachment_type, payload))

    # return "OK", 200

    bot_id = get_user_bot_id(sender_id)
    if attachment_type == "video":
        logger.info("VIDEO: %s" % (payload['url']))
        send_text(sender_id, "Processing video…", build_quick_replies(sender_id))


        timestamp = ("%.03f" % (time.time())).replace(".", "_")
        audio_file = "/var/www/html/bots/{timestamp}.wav".format(timestamp=timestamp)
        video_file = "/var/www/html/bots/{timestamp}.mp4".format(timestamp=timestamp)

        copy_thread = threading.Thread(
            target=copy_remote_asset,
            name="video_copy",
            kwargs={
                'src_url'   : payload['url'],
                'local_file': video_file
            }
        )
        copy_thread.start()
        copy_thread.join()

        # video_metadata = VideoMetaData(payload['url'])
        # video_metadata.start()
        # video_metadata.join()

        audio_renderer = VideoAudioRenderer(video_file, audio_file)
        audio_renderer.start()
        audio_renderer.join()

        r = sr.Recognizer()
        with sr.AudioFile(audio_file) as source:
            audio = r.record(source)

        transcript = None
        try:
            transcript = r.recognize_sphinx(audio)

        except sr.UnknownValueError:
            pass

        except sr.RequestError as e:
            pass

        if transcript is not None:
            response = wit_client.message(transcript)
            logger.info("WIT SAYS: %s" % (str(response),))

            if 'sentiment' in response['entities'] and float(response['entities']['sentiment'][0]['confidence']) >= Const.WIT_CONFIDENCE:
                entities = response['entities']
                conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
                try:
                    with conn:
                        cur = conn.cursor(mdb.cursors.DictCursor)
                        cur.execute('SELECT COUNT(DISTINCT `user_id`) AS `total` FROM `sentiments` WHERE `source` = "video" AND `bot_id` = %s;', (get_user_bot_id(sender_id),))
                        row = cur.fetchone()
                        total = row['total']

                        survey = "N/A"
                        survey_id = 0
                        cur.execute('SELECT `survey_id` FROM `survey_responses` WHERE `user_id` = %s ORDER BY `added` DESC LIMIT 1;', (get_user_id(sender_id),))
                        row = cur.fetchone()
                        if row is not None:
                            survey_id = row['survey_id']
                            cur.execute('SELECT `topic` FROM `surveys` WHERE `bot_id` = %s AND `id` = %s ORDER BY `sort` LIMIT 1;', (bot_id, survey_id))
                            row = cur.fetchone()
                            if row is None:
                                cur.execute('SELECT `id`, `topic` FROM `surveys` WHERE `bot_id` = %s ORDER BY `sort` LIMIT 1;', (bot_id))
                                row = cur.fetchone()
                                survey_id = row['id']

                            survey = row['topic']

                        cur.execute('INSERT INTO `sentiments` (`id`, `user_id`, `bot_id`, `media_id`, `source`, `content`, `entities`, `sentiment`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP());', (get_user_id(sender_id), bot_id, survey_id, "video", "http://192.241.197.211/bots/{timestamp}.mp4".format(timestamp=timestamp), json.dumps(response), 1 if entities['sentiment'][0]['value'] == "positive" else -1))
                        conn.commit()

                        cur.execute('SELECT `channel_name`, `webhook` FROM `slack_auths` WHERE `client_id` IN (SELECT `client_id` FROM `bots` WHERE `id` = %s) LIMIT 1;', (bot_id,))
                        row = cur.fetchone()
                        if row is not None:
                            payload = {
                                'channel'  : row['channel_name'],
                                'username ': "",
                                'icon_url' : "",
                                'text'     : "A *{sentiment}* \"{transcript}\" video response was submitted for the question _{survey}_\nYou should consider upgrading to a paid account to continue.".format(sentiment=entities['sentiment'][0]['value'], transcript=transcript, survey=survey)
                            }
                            # response = requests.post(row['webhook'], data={'payload': json.dumps(payload)})

                            if total >= 10:
                                payload = {
                                    'channel'  : row['channel_name'],
                                    'username ': "",
                                    'icon_url' : "",
                                    'text'     : "You have exceeded your video review alottment for free accounts, please purchase an Outro package now."
                                }
                                response = requests.post(row['webhook'], data={'payload': json.dumps(payload)})

                        cur.execute('SELECT COUNT(*) AS `total` FROM `sentiments` WHERE `user_id` = %s;', (get_user_id(sender_id),))
                        if cur.fetchone()['total'] == 0:
                            cur.execute('SELECT `sentiment` FROM `sentiments` WHERE `bot_id` = %s AND `source` = "video";', (bot_id,))
                            pos_total = 0
                            neg_total = 0
                            all_total = 0
                            for row in cur.fetchall():
                                all_total += 1
                                if row['sentiment'] == 1:
                                    pos_total += 1

                                else:
                                    neg_total += 1

                            send_text(sender_id, "Looks like you are not alone. Over {percent}% of people also had a {sentiment} reaction to this video.".format(percent=int((pos_total / float(all_total)) * 100) if pos_total > neg_total else int((neg_total / float(all_total)) * 100), sentiment="positive" if pos_total > neg_total else "negative"), build_quick_replies(sender_id))

                except mdb.Error, e:
                    logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

                finally:
                    if conn:
                        conn.close()

                send_text(sender_id, "Your video upload has been processed. Tap Send Message to upload a video.", build_quick_replies(sender_id))

            else:
                send_text(sender_id, "Video has not been processed. Try uploading another video and be specific with your feedback. If the problem continues you can alternatvely, text your response.".format(app_title=app_title_type(bot_id)), build_quick_replies(sender_id))

        else:
            send_text(sender_id, "Video has not been processed. Try uploading another video and be specific with your feedback. If the problem continues you can alternatvely, text your response.".format(app_title=app_title_type(bot_id)), build_quick_replies(sender_id))

    return "OK", 200


def handle_text_reply(sender_id, message_text):
    logger.info("handle_text_reply(sender_id=%s, message_text=%s)" % (sender_id, message_text))

    bot_id = get_user_bot_id(sender_id)

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

    if message_text.lower() in Const.RESERVED_SUPPORT_REPLIES.split("|"):
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

    elif re.search(r'^wit (.+)$', message_text):
        query = re.match(r'^wit (?P<query>.+)$', message_text).group('query')

    else:
        response = wit_client.message(message_text)
        logger.info("WIT SAYS: %s" % (str(response),))

        if 'sentiment' in response['entities'] and float(response['entities']['sentiment'][0]['confidence']) >= Const.WIT_CONFIDENCE:
            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('INSERT INTO `sentiments` (`id`, `user_id`, `bot_id`, `media_id`, `source`, `content`, `entities`, `sentiment`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP());', (get_user_id(sender_id), bot_id, 0, "text", message_text, json.dumps(response), 1 if response['entities']['sentiment'][0]['value'] == "positive" else -1))
                    conn.commit()

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

            send_text(sender_id, "Your text has been processed. Tap Send Message to upload a video.", build_quick_replies(sender_id))

        else:
            send_text(sender_id, "Couldn't process reply, please and be more specific with your feedback.".format(sentiment=response), build_quick_replies(sender_id))

        # modules = bot_modules(bot_id)
        # if modules == 1:
        #     send_survey_card(sender_id, True)
        #
        # else:
        #     send_default_carousel(sender_id)

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
                    'image_aspect_ratio': "square",
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



def send_list_card(recipient_id, body_elements, header_element=None, buttons=None, quick_replies=None):
    logger.info("send_list_card(recipient_id=%s, body_elements=%s, header_element=%s, buttons=%s, quick_replies=%s)" % (recipient_id, body_elements, header_element, buttons, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient': {
            'id': recipient_id
        },
        'message'  : {
            'attachment': {
                'type'   : "template",
                'payload': {
                    'template_type'    : "list",
                    'top_element_style': "compact" if header_element is None else "large",
                    'elements'         : body_elements if header_element is None else [header_element] + body_elements
                }
            }
        }
    }

    if buttons is not None:
        data['message']['attachment']['payload']['buttons'] = buttons

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
                    'template_type'      : "generic",
                     'image_aspect_ratio': "square",
                    'elements'           : elements
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
