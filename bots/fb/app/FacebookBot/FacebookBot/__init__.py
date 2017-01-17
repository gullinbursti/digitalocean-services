#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import cStringIO
import hashlib
import json
import locale
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import urllib

from datetime import datetime

import MySQLdb as mysql
import pycurl
import requests
import urllib2

from dateutil.relativedelta import relativedelta
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy

from constants import Const


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///prebotfb.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

locale.setlocale(locale.LC_ALL, 'en_US.utf8')

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler("/var/log/FacebookBot.log")
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)


#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#

class MessageStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ps_id = db.Column(db.String(100))
    message_id = db.Column(db.String(100))
    delivered = db.Column(db.Boolean)
    read = db.Column(db.Boolean)
    timestamp = db.Column(db.Integer)

    def __init__(self, ps_id, message_id, timestamp):
        self.ps_id = ps_id
        self.message_id = message_id
        self.delivered = 0
        self.read = 0
        self.timestamp = timestamp

    def __repr__(self):
        return  "<MessageStatus id=%d, ps_id=%s, message_id=%s, delivered=%s, read=%s, timestamp=%d>" % (self.id, self.ps_id, self.message_id, self.delivered, self.read, self.timestamp)


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fb_psid = db.Column(db.String(100))
    fb_name = db.Column(db.String(200))
    referrer = db.Column(db.String(200))
    storefront_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, fb_psid, fb_name="", referrer=""):
        self.fb_psid = fb_psid
        self.fb_name = fb_name
        self.referrer = referrer
        self.added = datetime.utcnow()

    def __repr__(self):
        return "<Customer fb_psid=%s, fb_name=%s, referrer=%s>" % (self.fb_psid, self.fb_name, self.referrer)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    storefront_id = db.Column(db.Integer)
    creation_state = db.Column(db.Integer)
    name = db.Column(db.String(80))
    display_name = db.Column(db.String(80))
    description = db.Column(db.String(200))
    image_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    broadcast_message = db.Column(db.String(200))
    attachment_id = db.Column(db.String(100))
    price = db.Column(db.Float)
    prebot_url = db.Column(db.String(128), unique=True)
    release_date = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, storefront_id, creation_state=0):
        self.storefront_id = storefront_id
        self.creation_state = creation_state
        self.description= ""
        self.price = 1.99
        self.attachment_id = ""

    def __repr__(self):
        return "<Product storefront_id=%d, creation_state=%d, display_name=%s, release_date=%s>" % (self.storefront_id, self.creation_state, self.display_name, self.release_date)


class Storefront(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.String(80))
    creation_state = db.Column(db.Integer)
    name = db.Column(db.String(80))
    display_name = db.Column(db.String(80))
    description = db.Column(db.String(200))
    logo_url = db.Column(db.String(500))
    video_url = db.Column(db.String(500))
    prebot_url = db.Column(db.String(128), unique=True)
    added = db.Column(db.Integer)

    def __init__(self, owner_id, creation_state=0):
        self.owner_id = owner_id
        self.creation_state = creation_state

    def __repr__(self):
        return "<Storefront owner_id=%s, creation_state=%d, display_name=%s, logo_url=%s>" % (self.owner_id, self.creation_state, self.display_name, self.logo_url)


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    storefront_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    customer_id = db.Column(db.Integer)
    enabled = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, storefront_id, product_id, customer_id, enabled=1):
        self.storefront_id = storefront_id
        self.product_id = product_id
        self.customer_id = customer_id
        self.enabled = enabled
        self.added = int(time.time())

    def __repr__(self):
        return "<Subscription storefront_id=%d, product_id=%d, customer_id=%d, enabled=%d>" % (self.storefront_id, self.product_id, self.customer_id, self.enabled)


class VideoImageRenderer(threading.Thread):
    def __init__(self, src_url, out_img, at_sec=3):
        self.stdout = None
        self.stderr = None
        threading.Thread.__init__(self)

        self.src_url = src_url
        self.out_img = out_img
        self.at_time = time.strftime("%H:%M:%S", time.gmtime(at_sec))

    def run(self):
        p = subprocess.Popen(
            ('/usr/bin/ffmpeg -ss %s -i %s -frames:v 1 %s' % (self.at_time, self.src_url, self.out_img)).split(),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        self.stdout, self.stderr = p.communicate()


class VideoMetaData(threading.Thread):
    def __init__(self, src_url):
        threading.Thread.__init__(self)

        self.src_url = src_url
        self.info = None

    def run(self):
        p = subprocess.Popen(
            ('/usr/bin/ffprobe %s' % (self.src_url)).split(),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = p.communicate()

        list = stderr.split("\n")
        dur = re.sub(r'\s{2,}', "", [s for s in list if "Duration:" in s][0]).split()[1][:-1]
        duration = (float(dur.split(":")[0]) * 3600) + (float(dur.split(":")[1]) * 60) + float(dur.split(":")[2])
        size = [s for s in list if "Stream" in s][0].split(", ")[2].split()[0]
        frmt = [s for s in list if "Stream" in s][0].split(", ")[0].split()[3]

        self.info = {
            'duration' : duration,
            'size'     : (int(size.split("x")[0]), int(size.split("x")[1])),
            'format'   : frmt
        }


#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#
#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


def drop_sqlite(flag=15):
    #logger.info("drop_sql(flag={flag)".format(flag=flag))

    if flag & 1:
        try:
            total = db.session.query(Product).delete()
            db.session.commit()
        except:
            db.session.rollback()

    if flag & 2:
        try:
            total = db.session.query(Storefront).delete()
            db.session.commit()
        except:
            db.session.rollback()

    if flag & 4:
        try:
            total = db.session.query(Customer).delete()
            db.session.commit()
        except:
            db.session.rollback()

    if flag & 8:
        try:
            total = db.session.query(Subscription).delete()
            db.session.commit()
        except:
            db.session.rollback()

def add_column(table_name, column_name, data_type):
    logger.info("add_column(table_name={table_name}, column_name={column_name}, data_type={data_type})".format(table_name=table_name, column_name=column_name, data_type=data_type))

    connection = sqlite3.connect("{file_path}/prebotfb.db".format(file_path=os.path.dirname(os.path.realpath(__file__))))
    cursor = connection.cursor()

    if data_type == "Integer":
        data_type_formatted = "INTEGER"

    elif data_type == "String":
        data_type_formatted = "VARCHAR(100)"


    sql_command = "ALTER TABLE '{table_name}' ADD column '{column_name}' '{data_type}'".format(table_name=table_name, column_name=column_name, data_type=data_type_formatted)

    cursor.execute(sql_command)
    connection.commit()
    connection.close()

    return "OK", 200


def copy_remote_asset(src_url, local_file):
    logger.info("copy_remote_asset(src_url={src_url}, local_file={local_file})".format(src_url=src_url, local_file=local_file))

    with open(local_file, 'wb') as handle:
        response = requests.get(src_url, stream=True)
        if response.status_code == 200:
            for block in response.iter_content(1024):
                handle.write(block)
        else:
            logger.info("DOWNLOAD FAILED!!! %s" % (response.text))
        del response



def send_tracker(category, action, label, value=""):
    logger.info("send_tracker(category={category}, action={action}, label={label})".format(category=category, action=action, label=label))

    # "http://beta.modd.live/api/user_tracking.php?username={username}&chat_id={chat_id}".format(username=label, chat_id=action),
    # "http://beta.modd.live/api/bot_tracker.php?src=facebook&category={category}&action={action}&label={label}&value={value}&cid={cid}".format(category=category, action=category, label=action, value=value, cid=hashlib.md5(label.encode()).hexdigest()),
    # "http://beta.modd.live/api/bot_tracker.php?src=facebook&category=user-message&action=user-message&label={label}&value={value}&cid={cid}".format(label=action, value=value, cid=hashlib.md5(label.encode()).hexdigest())

    t1 = threading.Thread(
        target=async_tracker,
        name="user_tracking",
        kwargs={
            'url'     : "http://beta.modd.live/api/user_tracking.php",
            'payload' : {
                'username' : label,
                'chat_id'  : action
            }
        }
    )

    t2 = threading.Thread(
        target=async_tracker,
        name="bot_tracker-1",
        kwargs={
            'url'     : "http://beta.modd.live/api/bot_tracker.php",
            'payload' : {
                'src'      : "prebot",
                'category' : category,
                'action'   : category,
                'label'    : action,
                'value'    : "",
                'cid'      : hashlib.md5(label.encode()).hexdigest()
            }
        }
    )

    t3 = threading.Thread(
        target=async_tracker,
        name="bot_tracker-2",
        kwargs={
            'url'     : "http://beta.modd.live/api/bot_tracker.php",
            'payload' : {
                'src'      : "prebot",
                'category' : "user-message",
                'action'   : "user-message",
                'label'    : action,
                'value'    : "",
                'cid'      : hashlib.md5(label.encode()).hexdigest()
            }
        }
    )

    t1.start()
    t2.start()
    t3.start()

    return True

def async_tracker(url, payload):
    #logger.info("async_tracker(url={url}, payload={payload}".format(url=url, payload=payload))

    response = requests.get(url, params=payload)
    if response.status_code != 200:
        logger.info("TRACKER ERROR:%s" % (response.text))


def add_new_user(recipient_id, deeplink):
    logger.info("add_new_user(recipient_id={recipient_id}, deeplink={deeplink})".format(recipient_id=recipient_id, deeplink=deeplink))

    try:
        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            #-- check db for existing user
            cur.execute('SELECT `id` FROM `users` WHERE `fb_psid` = "{fb_psid}" LIMIT 1;'.format(fb_psid=recipient_id))
            row = cur.fetchone()

            #-- go ahead n' add 'em
            if row is None:
                cur.execute('INSERT IGNORE INTO `users` (`id`, `fb_psid`, `referrer`, `added`) VALUES (NULL, "{fb_psid}", "{referrer}", UTC_TIMESTAMP());'.format(fb_psid=recipient_id, referrer=deeplink))
                conn.commit()

                #-- no update sqlite w/ the new guy
                users_query = Customer.query.filter(Customer.fb_psid == recipient_id)
                logger.info("USERS -->%s" % (Customer.query.filter(Customer.fb_psid == recipient_id).all()))
                if users_query.count() == 0:
                    db.session.add(Customer(fb_psid=recipient_id, fb_name="", referrer=recipient_id))

                else:
                    customer = users_query.fetchone()
                    customer.id = row['id']

                db.session.commit()


    except mysql.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()




def write_message_log(sender_id, message_id, message_txt):
    logger.info("write_message_log(sender_id={sender_id}, message_id={message_id}, message_txt={message_txt})".format(sender_id=sender_id, message_id=message_id, message_txt=message_txt))

    try:
        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('INSERT IGNORE INTO `chat_logs` (`id`, `fbps_id`, `message_id`, `body`, `added`) VALUES (NULL, "{fbps_id}", "{message_id}", "{body}", UTC_TIMESTAMP())'.format(fbps_id=sender_id, message_id=message_id, body=message_txt))
            conn.commit()

    except mysql.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()



def build_button(btn_type, caption="", url="", payload=""):
    logger.info("build_button(btn_type={btn_type}, caption={caption}, payload={payload})".format(btn_type=btn_type, caption=caption, payload=payload))

    if btn_type == Const.CARD_BTN_POSTBACK:
        button = {
            'type'    : Const.CARD_BTN_POSTBACK,
            'payload' : payload,
            'title'   : caption
        }

    elif btn_type == Const.CARD_BTN_URL:
        button = {
            'type'  : Const.CARD_BTN_URL,
            'url'   : url,
            'title' : caption
        }

    elif btn_type == Const.CARD_BTN_INVITE:
        button = {
            'type' : "element_share"
        }

    elif btn_type == Const.KWIK_BTN_TEXT:
        button = {
            'content_type' : Const.KWIK_BTN_TEXT,
            'title'        : caption,
            'payload'      : payload
        }

    return button


def build_quick_reply(btn_type, caption, payload, image_url=""):
    logger.info("build_quick_reply(btn_type={btn_type}, caption={caption}, payload={payload})".format(btn_type=btn_type, caption=caption, payload=payload))

    if btn_type == Const.KWIK_BTN_TEXT:
        button = {
            'content_type' : Const.KWIK_BTN_TEXT,
            'title'        : caption,
            'payload'      : payload
        }

    elif btn_type == Const.KWIK_BTN_IMAGE:
        button = {
            'type'      : Const.KWIK_BTN_TEXT,
            'title'     : caption,
            'image_url' : image_url,
            'payload'   : payload
        }

    elif btn_type == Const.KWIK_BTN_LOCATION:
        button = {
            'type'      : Const.KWIK_BTN_LOCATION,
            'title'     : caption,
            'image_url' : image_url,
            'payload'   : payload
        }

    else:
        button = {
            'type'    : Const.KWIK_BTN_TEXT,
            'title'   : caption,
            'payload' : payload
        }

    return button


def build_card_element(title, subtitle, image_url, item_url, buttons=None):
    logger.info("build_card_element(title={title}, subtitle={subtitle}, image_url={image_url}, item_url={item_url}, buttons={buttons})".format(title=title, subtitle=subtitle, image_url=image_url, item_url=item_url, buttons=buttons))

    element = {
        'title'     : title,
        'subtitle'  : subtitle,
        'image_url' : image_url,
        'item_url'  : item_url
    }

    if buttons is not None:
        element['buttons'] = buttons

    return element


def build_content_card(recipient_id, title, subtitle, image_url, item_url, buttons=None, quick_replies=None):
    logger.info("build_content_card(recipient_id={recipient_id}, title={title}, subtitle={subtitle}, image_url={image_url}, item_url={item_url}, buttons={buttons}, quick_replies={quick_replies})".format(recipient_id=recipient_id, title=title, subtitle=subtitle, image_url=image_url, item_url=item_url, buttons=buttons, quick_replies=quick_replies))

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type' : "template",
                'payload' : {
                    'template_type' : "generic",
                    'elements' : [
                        build_card_element(
                            title = title,
                            subtitle = subtitle,
                            image_url = image_url,
                            item_url = item_url,
                            buttons = buttons
                        )
                    ]
                }
            }
        }
    }

    if buttons is not None:
        data['message']['attachment']['payload']['elements'][0]['buttons'] = buttons

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    return data


def build_carousel(recipient_id, cards, quick_replies=None):
    logger.info("build_carousel(recipient_id={recipient_id}, cards={cards}, quick_replies={quick_replies})".format(recipient_id=recipient_id, cards=cards, quick_replies=quick_replies))

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type' : "template",
                'payload' : {
                    'template_type' : "generic",
                    'elements'      : cards
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    return data


def welcome_message(recipient_id, entry_type, deeplink=""):
    logger.info("welcome_message(recipient_id={recipient_id}, entry_type={entry_type}, deeplink={deeplink})".format(recipient_id=recipient_id, entry_type=entry_type, deeplink=deeplink))


    if entry_type == Const.MARKETPLACE_GREETING:
        send_text(recipient_id, Const.ORTHODOX_GREETING)
        send_admin_carousel(recipient_id)

    elif entry_type == Const.STOREFRONT_ADMIN:
        send_text(recipient_id, Const.ORTHODOX_GREETING)
        send_admin_carousel(recipient_id)

    elif entry_type == Const.CUSTOMER_EMPTY:
        send_text(recipient_id, Const.ORTHODOX_GREETING)
        send_admin_carousel(recipient_id)

    elif entry_type == Const.CUSTOMER_REFERRAL:
        storefront = None
        product = None

        product_query = Product.query.filter(Product.name == deeplink.split("/")[-1])
        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).scalar()
            storefront_query = Storefront.query.filter(Storefront.id == product.storefront_id)
            if storefront_query.count() > 0:
                storefront = storefront_query.first()

            customer_query = Customer.query.filter(Customer.fb_psid == recipient_id)
            if customer_query.count() > 0:
                customer = customer_query.first()
                customer.storefront_id = storefront.id
                customer.product_id = product.id
                db.session.commit()

                subscription_query = Subscription.query.filter(Subscription.product_id == product.id).filter(Subscription.customer_id == customer.id)

                if subscription_query.count() == 0:
                    subscription = Subscription(storefront.id, product.id, customer.id)
                    db.session.add(subscription)
                    db.session.commit()

                    send_tracker("user-subscribe", recipient_id, storefront.display_name)
                    try:
                        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('INSERT IGNORE INTO `subscriptions` (`id`, `user_id`, `storefront_id`, `product_id`, `deeplink`, `added`) VALUES (NULL, "{user_id}", "{storefront_id}", "{product_id}", "{deeplink}", UTC_TIMESTAMP())'.format(user_id=customer.id, storefront_id=storefront.id, product_id=product.id, deeplink=("/%s" % (deeplink))))
                            conn.commit()
                            subscription.id = cur.lastrowid
                            db.session.commit()

                    except mysql.Error, e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()

                    payload = {
                        'channel' : "#pre",
                        'username' : "fbprebot",
                        'icon_url' : "https://scontent.fsnc1-4.fna.fbcdn.net/t39.2081-0/p128x128/15728018_267940103621073_6998097150915641344_n.png",
                        'text' : "*{sender_id}* just subscribed to _{product_name}_ from a shop named _{storefront_name}_.\n{video_url}".format(sender_id=recipient_id, product_name=product.display_name, storefront_name=storefront.display_name, video_url=product.video_url),
                        'attachments' : [{
                            'image_url' : product.image_url
                        }]
                    }
                    response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })

            send_text(recipient_id, "Welcome to {storefront_name}'s Shop Bot on Pre. You have been subscribed to {storefront_name} updates.".format(storefront_name=storefront.display_name))
            send_storefront_carousel(recipient_id, product.storefront_id)
            return


        storefront_query = Storefront.query.filter(Storefront.name == deeplink.split("/")[0])
        if storefront_query.count() > 0:
            storefront = storefront_query.first()
            product_query = Product.query.filter(Product.storefront_id == storefront.id)
            if product_query.count() > 0:
                product = product_query.order_by(Product.added.desc()).scalar()


            customer_query = Customer.query.filter(Customer.fb_psid == recipient_id)
            if customer_query.count() > 0:
                customer = customer_query.first()
                customer.storefront_id = storefront.id
                customer.product_id = product.id
                db.session.commit()

                subscription_query = Subscription.query.filter(Subscription.storefront_id == storefront.id).filter(Subscription.product_id == product.id).filter(Subscription.customer_id == customer.id)

                if subscription_query.count() == 0:
                    subscription = Subscription(storefront.id, product.id, customer.id)
                    db.session.add(subscription)
                    db.session.commit()

                    try:
                        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('INSERT IGNORE INTO `subscriptions` (`id`, `user_id`, `storefront_id`, `product_id`, `deeplink`, `added`) VALUES (NULL, "{user_id}", "{storefront_id}", "{product_id}", "{deeplink}", UTC_TIMESTAMP())'.format(user_id=customer.id, storefront_id=storefront.id, product_id=product.id, deeplink=("/%s" % (deeplink))))
                            conn.commit()
                            subscription.id = cur.lastrowid
                            db.session.commit()

                    except mysql.Error, e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()

                    payload = {
                        'channel' : "#pre",
                        'username' : "fbprebot",
                        'icon_url' : "https://scontent.fsnc1-4.fna.fbcdn.net/t39.2081-0/p128x128/15728018_267940103621073_6998097150915641344_n.png",
                        'text' : "*{sender_id}* just subscribed to _{product_name}_ from a shop named _{storefront_name}_.\n{video_url}".format(sender_id=recipient_id, product_name=product.display_name, storefront_name=storefront.display_name, video_url=product.video_url),
                        'attachments' : [{
                            'image_url' : product.image_url
                        }]
                    }
                    response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })

            send_text(recipient_id, "Welcome to {storefront_name}'s Shop Bot on Pre. You have been subscribed to {storefront_name} updates.".format(storefront_name=storefront.display_name))
            send_storefront_carousel(recipient_id, storefront.id)
            return


    send_text(recipient_id, Const.ORTHODOX_GREETING)
    send_admin_carousel(recipient_id)


def send_admin_carousel(recipient_id):
    logger.info("send_admin_carousel(recipient_id={recipient_id})".format(recipient_id=recipient_id))

    #-- look for created storefront
    storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id)
    cards = []

    if storefront_query.count() == 0:
        cards.append(
            build_card_element(
                title = "Create Shop",
                subtitle = "Tap here now",
                image_url = Const.IMAGE_URL_CREATE_STOREFRONT,
                item_url = None,
                buttons = [
                    build_button(Const.CARD_BTN_POSTBACK, caption="Create Shop", payload=Const.PB_PAYLOAD_CREATE_STOREFRONT)
                ]
            )
        )

    else:
        storefront = storefront_query.first()

        if storefront.display_name is None:
            storefront.display_name = "[NAME NOT SET]"

        if storefront.description is None:
            storefront.description = ""

        if storefront.logo_url is None:
            storefront.logo_url = Const.IMAGE_URL_ADD_PRODUCT

        if storefront.prebot_url is None:
            storefront.prebot_url = "http://prebot.me/{storefront_name}".format(storefront_name=storefront.name)


        product_query = Product.query.filter(Product.storefront_id == storefront.id)
        if product_query.count() == 0:
            cards.append(
                build_card_element(
                    title = "Add Video",
                    subtitle = "Tap here now",
                    image_url = Const.IMAGE_URL_ADD_PRODUCT,
                    item_url = None,
                    buttons = [
                        build_button(Const.CARD_BTN_POSTBACK, caption="Add Video", payload=Const.PB_PAYLOAD_ADD_PRODUCT)
                    ]
                )
            )

            cards.append(
                build_card_element(
                    title = "Share Shop",
                    subtitle = "",
                    image_url = Const.IMAGE_URL_SHARE_STOREFRONT,
                    item_url = None,
                    buttons = [
                        build_button(Const.CARD_BTN_POSTBACK, caption="Share Shop", payload=Const.PB_PAYLOAD_SHARE_STOREFRONT)
                    ]
                )
            )

        else:
            product = product_query.order_by(Product.added.desc()).scalar()

            if product.prebot_url is None:
                product.prebot_url = "http://prebot.me/{product_name}".format(product_name=product.name)

            if product.display_name is None:
                product.display_name = "[NAME NOT SET]"

            if product.video_url is None:
                product.image_url = Const.IMAGE_URL_ADD_PRODUCT
                product.video_url = None

            subscriber_query = Subscription.query.filter(Subscription.product_id == product.id).filter(Subscription.enabled == 1)
            if subscriber_query.count() == 1:
                cards.append(
                    build_card_element(
                        title = "Message Customers",
                        subtitle =  "Notify your 1 subscriber",
                        image_url = Const.IMAGE_URL_NOTIFY_SUBSCRIBERS,
                        item_url = None,
                        buttons = [
                            build_button(Const.CARD_BTN_POSTBACK, caption="Message Customers", payload=Const.PB_PAYLOAD_NOTIFY_SUBSCRIBERS)
                        ]
                    )
                )

            elif subscriber_query.count() > 1:
                cards.append(
                    build_card_element(
                        title = "Message Customers",
                        subtitle =  "Notify your {total} subscribers.".format(total=subscriber_query.count()),
                        image_url = Const.IMAGE_URL_NOTIFY_SUBSCRIBERS,
                        item_url = None,
                        buttons = [
                            build_button(Const.CARD_BTN_POSTBACK, caption="Message Customers", payload=Const.PB_PAYLOAD_NOTIFY_SUBSCRIBERS)
                        ]
                    )
)

            cards.append(
                build_card_element(
                    title = product.display_name,
                    subtitle = product.description,
                    image_url = product.image_url,
                    item_url = product.video_url,
                    buttons = [
                        build_button(Const.CARD_BTN_POSTBACK, caption="Replace Item", payload=Const.PB_PAYLOAD_DELETE_PRODUCT)
                    ]
                )
            )

            cards.append(
                build_card_element(
                    title = "Share Shop",
                    subtitle = "",
                    image_url = Const.IMAGE_URL_SHARE_STOREFRONT,
                    item_url = None,
                    buttons = [
                        build_button(Const.CARD_BTN_POSTBACK, caption="Share Shop", payload=Const.PB_PAYLOAD_SHARE_PRODUCT)
                    ]
                )
            )

    cards.append(
        build_card_element(
            title = "View Shops",
            subtitle = "",
            image_url = Const.IMAGE_URL_MARKETPLACE,
            item_url = "http://prebot.me/shops",
            buttons = [
                build_button(Const.CARD_BTN_URL, caption="View Shops", url="http://prebot.me/shops")
            ]
        )
    )

    cards.append(
        build_card_element(
            title = "Support",
            subtitle = "",
            image_url = Const.IMAGE_URL_SUPPORT,
            item_url = "http://prebot.me/support",
            buttons = [
                build_button(Const.CARD_BTN_URL, caption="Get Support", url="http://prebot.me/support")
            ]
        )
    )

    if storefront_query.count() > 0:
        storefront = storefront_query.first()
        cards.append(
            build_card_element(
                title = storefront.display_name,
                subtitle = storefront.description,
                image_url = Const.IMAGE_URL_REMOVE_STOREFRONT,
                item_url = None,
                buttons = [
                    build_button(Const.CARD_BTN_POSTBACK, caption="Remove Shop", payload=Const.PB_PAYLOAD_DELETE_STOREFRONT)
                ]
            )
        )

    data = build_carousel(
        recipient_id = recipient_id,
        cards = cards
    )

    send_message(json.dumps(data))


def send_storefront_carousel(recipient_id, storefront_id):
    logger.info("send_storefront_carousel(recipient_id={recipient_id}, storefront_id={storefront_id})".format(recipient_id=recipient_id, storefront_id=storefront_id))

    query = Storefront.query.filter(Storefront.id == storefront_id)
    if query.count() > 0:
        storefront = query.first()

        try:
            conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('UPDATE `storefronts` SET `views` = `views` + 1 WHERE `id` = {storefront_id} LIMIT 1;'.format(storefront_id=storefront.id))
                conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

        finally:
            if conn:
                conn.close()

        query = Product.query.filter(Product.storefront_id == storefront.id)
        if query.count() > 0:
            product = query.order_by(Product.added.desc()).scalar()

            data = build_carousel(
                recipient_id = recipient_id,
                cards = [
                    build_card_element(
                        title = product.display_name,
                        subtitle = product.description,
                        image_url = product.image_url,
                        item_url = None,
                        buttons = [
                            build_button(Const.CARD_BTN_URL, caption="Pre-Order", url="https://prebot.chat/reserve/{product_id}/{recipient_id}".format(product_id=product.id, recipient_id=recipient_id))
                        ]
                    ),
                    build_card_element(
                        title = product.display_name,
                        subtitle = "View Shopbot",
                        image_url = product.image_url,
                        item_url = product.prebot_url,
                        buttons = [
                            build_button(Const.CARD_BTN_INVITE)
                        ]
                    ),
                    build_card_element(
                        title = "View Video",
                        subtitle = "",
                        image_url = product.image_url,
                        item_url = None,
                        buttons = [
                            build_button(Const.CARD_BTN_POSTBACK, caption="View Video", payload=Const.PB_PAYLOAD_PRODUCT_VIDEO)
                        ]
                    ),
                    build_card_element(
                        title = "Support",
                        subtitle = "",
                        image_url = Const.IMAGE_URL_SUPPORT,
                        item_url = "http://prebot.me/support",
                        buttons = [
                            build_button(Const.CARD_BTN_URL, caption="Get Support", url="http://prebot.me/support")
                        ]
                    )
                ]
            )

            send_message(json.dumps(data))


def send_storefront_card(recipient_id, storefront_id, card_type=Const.CARD_TYPE_STOREFRONT):
    logger.info("send_storefront_card(recipient_id={recipient_id}, storefront_id={storefront_id}, card_type={card_type})".format(recipient_id=recipient_id, storefront_id=storefront_id, card_type=card_type))

    query = Storefront.query.filter(Storefront.id == storefront_id)
    if query.count() > 0:
        storefront = query.first()

        if card_type == Const.CARD_TYPE_STOREFRONT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = storefront.display_name,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.prebot_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="View Shopbot", url=storefront.prebot_url),
                    build_button(Const.CARD_BTN_INVITE)
                ]
            )

        elif card_type == Const.CARD_TYPE_PREVIEW_STOREFRONT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = storefront.display_name,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = None,
                quick_replies = [
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Submit", Const.PB_PAYLOAD_SUBMIT_STOREFRONT),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Re-Do", Const.PB_PAYLOAD_REDO_STOREFRONT),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Cancel", Const.PB_PAYLOAD_CANCEL_STOREFRONT)
                ]
            )

        elif card_type == Const.CARD_TYPE_SHARE_STOREFRONT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = storefront.display_name,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.prebot_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="View Shopbot", url=storefront.prebot_url),
                    build_button(Const.CARD_BTN_INVITE)
                ]
            )

        else:
            data = build_content_card(
                recipient_id = recipient_id,
                title = storefront.display_name,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.prebot_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="View Shopbot", url=storefront.prebot_url),
                    build_button(Const.CARD_BTN_INVITE)
                ]
            )

        send_message(json.dumps(data))


def send_product_card(recipient_id, product_id, card_type=Const.CARD_TYPE_PRODUCT):
    logger.info("send_product_card(recipient_id={recipient_id}, product_id={product_id}, card_type={card_type})".format(recipient_id=recipient_id, product_id=product_id, card_type=card_type))

    query = Product.query.filter(Product.id == product_id)
    if query.count() > 0:
        product = query.order_by(Product.added.desc()).scalar()

        if product.image_url is None:
            product.image_url = Const.IMAGE_URL_ADD_PRODUCT

        if card_type == Const.CARD_TYPE_PRODUCT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
                subtitle = product.description,
                image_url = product.image_url,
                item_url = None,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="Tap to Reserve", url="http://prebot.me/reserve/{product_id}/{recipient_id}".format(product_id=product_id, recipient_id=recipient_id))
                ]
            )

        elif card_type == Const.CARD_TYPE_PREVIEW_PRODUCT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
                subtitle = product.description,
                image_url = product.image_url,
                item_url = product.video_url,
                quick_replies = [
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Submit", Const.PB_PAYLOAD_SUBMIT_PRODUCT),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Re-Do", Const.PB_PAYLOAD_REDO_PRODUCT),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Cancel", Const.PB_PAYLOAD_CANCEL_PRODUCT)
                ]
            )

        elif card_type == Const.CARD_TYPE_SHARE_PRODUCT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
                subtitle = "View Shopbot",
                image_url = product.image_url,
                item_url = product.prebot_url,
                buttons = [
                    #build_button(Const.CARD_BTN_URL, caption="View Shopbot", url=product.prebot_url),
                    build_button(Const.CARD_BTN_INVITE)
                ]
            )

        else:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
                subtitle = product.description,
                image_url = product.image_url,
                item_url = None,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="Tap to Reserve", url="http://prebot.me/reserve/{product_id}/{recipient_id}".format(product_id=product_id, recipient_id=recipient_id))
                ]
            )

        send_message(json.dumps(data))


#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


def received_quick_reply(recipient_id, quick_reply):
    logger.info("received_quick_reply(recipient_id={recipient_id}, quick_reply={quick_reply})".format(recipient_id=recipient_id, quick_reply=quick_reply))

    if quick_reply == Const.PB_PAYLOAD_SUBMIT_STOREFRONT:
        send_tracker("button-submit-store", recipient_id, "")

        users_query = Customer.query.filter(Customer.fb_psid == recipient_id)
        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 3)
        if storefront_query.count() > 0:
            storefront = storefront_query.first()
            storefront.creation_state = 4
            storefront.added = datetime.utcnow()
            db.session.commit()

            try:
                conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('INSERT IGNORE INTO `storefronts` (`id`, `owner_id`, `name`, `display_name`, `description`, `logo_url`, `prebot_url`, `added`) VALUES (NULL, {owner_id}, "{name}", "{display_name}", "{description}", "{logo_url}", "{prebot_url}", UTC_TIMESTAMP())'.format(owner_id=users_query.first().id, name=storefront.name, display_name=storefront.display_name, description=storefront.description, logo_url=storefront.logo_url, prebot_url=storefront.prebot_url))
                    conn.commit()
                    storefront.id = cur.lastrowid
                    db.session.commit()

            except mysql.Error, e:
                logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

            finally:
                if conn:
                    conn.close()


            send_text(recipient_id, "Great! Now add a video about what you are pre-selling.")
            send_admin_carousel(recipient_id)

            send_tracker("shop-sign-up", recipient_id, "")
            payload = {
                'channel' : "#pre",
                'username' : "fbprebot",
                'icon_url' : "https://scontent.fsnc1-4.fna.fbcdn.net/t39.2081-0/p128x128/15728018_267940103621073_6998097150915641344_n.png",
                'text' : "*{sender_id}* just created a shop named _{storefront_name}_.".format(sender_id=recipient_id, storefront_name=storefront.display_name),
                'attachments' : [{
                    'image_url' : storefront.logo_url
                }]
            }
            response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })


    elif quick_reply == Const.PB_PAYLOAD_REDO_STOREFRONT:
        send_tracker("button-redo-store", recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 3)
        if storefront_query.count() > 0:
            Storefront.query.filter(Storefront.owner_id == recipient_id).delete()
            db.session.commit()

        db.session.add(Storefront(recipient_id))
        db.session.commit()

        send_text(recipient_id, "Give your Pre Shop Bot a name.")

    elif quick_reply == Const.PB_PAYLOAD_CANCEL_STOREFRONT:
        send_tracker("button-cancel-store", recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 3)
        if storefront_query.count() > 0:
            storefront = storefront_query.first()
            send_text(recipient_id, "Canceling your {storefront_name} shop creation...".format(storefront_name=storefront.display_name))
            Storefront.query.filter(Storefront.owner_id == recipient_id).delete()
            db.session.commit()

        send_admin_carousel(recipient_id)

    elif re.search('PRODUCT_RELEASE_(\d+)_DAYS', quick_reply) is not None:
        match = re.match(r'PRODUCT_RELEASE_(\d+)_DAYS', quick_reply)
        send_tracker("button-product-release-{days}-days-store".format(days=match.group(1)), recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)
        product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 2)
        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).scalar()
            product.release_date = (datetime.utcnow() + relativedelta(months=int(int(match.group(1)) / 30))).replace(hour=0, minute=0, second=0, microsecond=0)
            product.description = "Pre-release ends {release_date}".format(release_date=product.release_date.strftime('%a, %b %-d'))
            product.creation_state = 3
            db.session.commit()

            send_text(recipient_id, "Here's what your product will look like:")
            send_product_card(recipient_id, product.id, Const.CARD_TYPE_PREVIEW_PRODUCT)

    elif quick_reply == Const.PB_PAYLOAD_SUBMIT_PRODUCT:
        send_tracker("button-submit-product", recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)
        product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 3)
        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).scalar()
            product.creation_state = 4
            product.added = datetime.utcnow()
            db.session.commit()

            try:
                conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('INSERT IGNORE INTO `products` (`id`, `storefront_id`, `name`, `display_name`, `description`, `image_url`, `video_url`, `attachment_id`, `price`, `prebot_url`, `release_date`, `added`) VALUES (NULL, {storefront_id}, "{name}", "{display_name}", "{description}", "{image_url}", "{video_url}", "{attachment_id}", {price}, "{prebot_url}", "{release_date}", UTC_TIMESTAMP())'.format(storefront_id=product.storefront_id, name=product.name, display_name=product.display_name, description=product.description, image_url=product.image_url, video_url=product.video_url, attachment_id=product.attachment_id, price=product.price, prebot_url=product.prebot_url, release_date=product.release_date))
                    conn.commit()
                    product.id = cur.lastrowid
                    db.session.commit()

            except mysql.Error, e:
                logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

            finally:
                if conn:
                    conn.close()


            storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
            send_text(recipient_id, "You have successfully added {product_name} to {storefront_name}.\n\nShare {product_name}'s card with your customers now.\n{product_url}".format(product_name=product.display_name, storefront_name=storefront.display_name, product_url=re.sub(r'https?:\/\/', '', product.prebot_url)))
            send_product_card(recipient_id, product.id, Const.CARD_TYPE_SHARE_PRODUCT)

            payload = {
                'channel' : "#pre",
                'username' : "fbprebot",
                'icon_url' : "https://scontent.fsnc1-4.fna.fbcdn.net/t39.2081-0/p128x128/15728018_267940103621073_6998097150915641344_n.png",
                'text' : "*{sender_id}* just created a product named _{product_name}_ for the shop _{storefront_name}_.\n<{video_url}>".format(sender_id=recipient_id, product_name=product.display_name, storefront_name=storefront_query.first().display_name, video_url=product.video_url),
                'attachments' : [{
                    'image_url' : product.image_url
                }]
            }
            response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })

    elif quick_reply == Const.PB_PAYLOAD_REDO_PRODUCT:
        send_tracker("button-redo-product", recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)
        product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id)
        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).scalar()
            Product.query.filter(Product.storefront_id == storefront_query.first().id).delete()

        db.session.add(Product(storefront_query.first().id))
        db.session.commit()

        send_text(recipient_id, "Give your product a name.")

    elif quick_reply == Const.PB_PAYLOAD_CANCEL_PRODUCT:
        send_tracker("button-undo-product", recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)
        product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id)
        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).scalar()
            send_text(recipient_id, "Canceling your {product_name} product creation...".format(product_name=product.display_name))

            Product.query.filter(Product.storefront_id == storefront_query.first().id).delete()
            db.session.commit()

        send_admin_carousel(recipient_id)


def received_payload_button(recipient_id, payload):
    logger.info("received_payload_button(recipient_id={recipient_id}, payload={payload})".format(recipient_id=recipient_id, payload=payload))

    storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)

    if payload == Const.PB_PAYLOAD_GREETING:
        logger.info("----------=BOT GREETING @({timestamp})=----------".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
        send_tracker("signup-fb-pre", recipient_id, "")

        welcome_message(recipient_id, Const.MARKETPLACE_GREETING)

    elif payload == Const.PB_PAYLOAD_CREATE_STOREFRONT:
        send_tracker("button-create-shop", recipient_id, "")

        query = Storefront.query.filter(Storefront.owner_id == recipient_id)
        if query.count() > 0:
            try:
                deleted_rows = db.session.query(Storefront).delete()
                db.session.commit()
            except:
                db.session.rollback()


        db.session.add(Storefront(recipient_id))
        db.session.commit()

        send_text(recipient_id, "Give your Shopbot a name.")


    elif payload == Const.PB_PAYLOAD_DELETE_STOREFRONT:
        send_tracker("button-delete-shop", recipient_id, "")

        for storefront in Storefront.query.filter(Storefront.owner_id == recipient_id):
            send_text(recipient_id, "{storefront_name} has been removed.".format(storefront_name=storefront.display_name))
            Product.query.filter(Product.storefront_id == storefront.id).delete()

        Storefront.query.filter(Storefront.owner_id == recipient_id).delete()
        db.session.commit()

        try:
            conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('UPDATE `storefronts` SET `enabled` = 0 WHERE `id` = {storefront_id};'.format(storefront_id=storefront.id))
                cur.execute('UPDATE `products` SET `enabled` = 0 WHERE `storefront_id` = {storefront_id};'.format(storefront_id=storefront.id))
                cur.execute('UPDATE `subscriptions` SET `enabled` = 0 WHERE `storefront_id` = {storefront_id};'.format(storefront_id=storefront.id))
                conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

        finally:
            if conn:
                conn.close()


        send_admin_carousel(recipient_id)


    elif payload == Const.PB_PAYLOAD_ADD_PRODUCT:
        send_tracker("button-add-item", recipient_id, "")

        try:
            conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `id` FROM `storefronts` WHERE `name` = "{storefront_name}" LIMIT 1;'.format(storefront_name=storefront_query.first().name))
                row = cur.fetchone()
                logger.info("AD PRODUCT TO STORE: %s" % (row))
                if row is not None:
                    db.session.add(Product(row['id']))

                else:
                    db.session.add(Product(storefront_query.first().id))
                db.session.commit()

        except mysql.Error, e:
            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(recipient_id, "Give your pre-sale product a name.")


    elif payload == Const.PB_PAYLOAD_DELETE_PRODUCT:
        send_tracker("button-delete-item", recipient_id, "")

        storefront = storefront_query.first()
        for product in Product.query.filter(Product.storefront_id == storefront.id):
            send_text(recipient_id, "Removing your existing product \"{product_name}\"...".format(product_name=product.display_name))
            Subscription.query.filter(Subscription.product_id == product.id)
            Product.query.filter(Product.storefront_id == storefront.id).delete()
        db.session.commit()

        try:
            conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('UPDATE `products` SET `enabled` = 0 WHERE `storefront_id` = {storefront_id};'.format(storefront_id=storefront.id))
                cur.execute('UPDATE `subscriptions` SET `enabled` = 0 WHERE `storefront_id` = {storefront_id};'.format(storefront_id=storefront.id))
                conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

        finally:
            if conn:
                conn.close()

        db.session.add(Product(storefront.id))
        db.session.commit()

        send_text(recipient_id, "Give your product a name.")

    elif payload == Const.PB_PAYLOAD_SHARE_STOREFRONT:
        send_tracker("button-share", recipient_id, "")
        send_text(recipient_id, "Share your Shopbot on Instagram, Facebook, Twitter, and Snapchat.")
        send_storefront_card(recipient_id, storefront_query.first().id, Const.CARD_TYPE_SHARE_STOREFRONT)

    elif payload == Const.PB_PAYLOAD_SHARE_PRODUCT:
        send_tracker("button-share", recipient_id, "")
        send_text(recipient_id, "Share your Shopbot on Instagram, Facebook, Twitter, and Snapchat.")

        query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 4)
        if query.count() > 0:
            product = query.first()
            send_product_card(recipient_id, product.id, Const.CARD_TYPE_SHARE_PRODUCT)
        else:
            send_storefront_card(recipient_id, storefront_query.first().id, Const.CARD_TYPE_SHARE_STOREFRONT)

    elif payload == Const.PB_PAYLOAD_SUPPORT:
        send_tracker("button-support", recipient_id, "")
        send_text(recipient_id, "Support for Prebot:\nprebot.me/support")

    elif payload == Const.PB_PAYLOAD_RESERVE_PRODUCT:
        send_tracker("button-reserve", recipient_id, "")

    elif payload == Const.PB_PAYLOAD_PRODUCT_VIDEO:
        send_tracker("button-view-video", recipient_id, "")

        customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
        product_query = Product.query.filter(Product.id == customer.product_id)

        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).scalar()
            send_video(recipient_id, product.video_url)

    elif payload == Const.PB_PAYLOAD_NOTIFY_SUBSCRIBERS:
        if storefront_query.count() > 0:
            storefront = storefront_query.first()
            send_tracker("shop-send-message", recipient_id, storefront.display_name)

            product_query = Product.query.filter(Product.storefront_id == storefront.id)
            if product_query.count() > 0:
                product = product_query.order_by(Product.added.desc()).scalar()
                product.broadcast_message = "_{PENDING}_"
                db.session.commit()

                send_text(recipient_id, "Send a message or video to your Pre subscribers.")

    else:
        send_tracker("unknown-button", recipient_id, "")
        send_text(recipient_id, "Button not recognized!")


def recieved_attachment(recipient_id, attachment_type, payload):
    logger.info("recieved_attachment(recipient_id={recipient_id}, attachment_type={attachment_type}, payload={payload})".format(recipient_id=recipient_id, attachment_type=attachment_type, payload=payload))

    #------- IMAGE MESSAGE
    if attachment_type == "image":
        logger.info("IMAGE: %s" % (payload))
        query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 2)

        if query.count() > 0:
            storefront = query.first()
            storefront.creation_state = 3
            storefront.logo_url = payload['url']
            db.session.commit()

            send_text(recipient_id, "Here's what your Shopbot will look like:")
            send_storefront_card(recipient_id, storefront.id, Const.CARD_TYPE_PREVIEW_STOREFRONT)

    #------- VIDEO MESSAGE
    elif attachment_type == "video":
        logger.info("VIDEO: %s" % (payload['url']))

        #return "OK", 200
        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)
        if storefront_query.count() > 0:
            query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 1)

            if query.count() > 0:
                timestamp = ("%.03f" % (time.time())).replace(".", "_")
                image_file = "/var/www/html/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
                video_file = "/var/www/html/videos/{timestamp}.mp4".format(timestamp=timestamp)

                video_metadata = VideoMetaData(payload['url'])
                video_metadata.start()
                video_metadata.join()

                image_renderer = VideoImageRenderer(payload['url'], image_file, int(video_metadata.info['duration'] * 0.5))
                image_renderer.start()
                image_renderer.join()

                copy_thread = threading.Thread(
                    target=copy_remote_asset,
                    name="video_copy",
                    kwargs={
                        'src_url'    : payload['url'],
                        'local_file' : video_file
                    }
                )
                copy_thread.start()

                product = query.order_by(Product.added.desc()).scalar()
                product.creation_state = 2
                product.image_url = "http://prebot.me/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
                product.video_url = "http://prebot.me/videos/{timestamp}.mp4".format(timestamp=timestamp)
                db.session.commit()

                send_text(
                    recipient_id = recipient_id,
                    message_text = "Select the date range the product will be exclusively available to your Pre customers.",
                    quick_replies = [
                        build_quick_reply(Const.KWIK_BTN_TEXT, "Right Now", Const.PB_PAYLOAD_PRODUCT_RELEASE_NOW),
                        build_quick_reply(Const.KWIK_BTN_TEXT, "Next Month", Const.PB_PAYLOAD_PRODUCT_RELEASE_30_DAYS),
                        build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=2)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_60_DAYS),
                        build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=3)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_90_DAYS),
                        build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=4)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_120_DAYS)
                    ]
                )

                return "OK", 200

            query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.broadcast_message == "_{PENDING}_")
            if query.count() > 0:
                product = query.first()

                timestamp = ("%.03f" % (time.time())).replace(".", "_")
                image_file = "/var/www/html/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
                video_file = "/var/www/html/videos/{timestamp}.mp4".format(timestamp=timestamp)

                video_metadata = VideoMetaData(payload['url'])
                video_metadata.start()
                video_metadata.join()

                image_renderer = VideoImageRenderer(payload['url'], image_file, int(video_metadata.info['duration'] * 0.5))
                image_renderer.start()
                image_renderer.join()

                copy_thread = threading.Thread(
                    target=copy_remote_asset,
                    name="video_copy",
                    kwargs={
                        'src_url'    : payload['url'],
                        'local_file' : video_file
                    }
                )
                copy_thread.start()

                product.broadcast_message = "http://prebot.me/videos/{timestamp}.mp4".format(timestamp=timestamp)
                db.session.commit()

                try:
                    conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('UPDATE `products` SET `broadcast_message` = "{broadcast_message}" WHERE `storefront_id` = {storefront_id} AND `enabled` = 1;'.format(broadcast_message=product.broadcast_message, storefront_id=storefront_query.first().id))
                        cur.execute('UPDATE `subscriptions` SET `broadcast` = 1 WHERE `storefront_id` = {storefront_id} AND `product_id` = {product_id};'.format(storefront_id=storefront_query.first().id, product_id=product.id))
                        conn.commit()

                except mysql.Error, e:
                    logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                finally:
                    if conn:
                        conn.close()

                send_text(recipient_id, "Your message will be broadcasted as soon as resources allow.")
                send_admin_carousel(recipient_id)


def received_text_response(recipient_id, message_text):
    logger.info("received_text_response(recipient_id={recipient_id}, message_text={message_text})".format(recipient_id=recipient_id, message_text=message_text))
    storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)

    #-- purge sqlite db
    if message_text == "/:flush_sqlite:/":
        drop_sqlite()
        send_text(recipient_id, "Purged sqlite db")
        send_admin_carousel(recipient_id)

    elif message_text.startswith("/:db_addcol"):
        comp = message_text.split(" ")

        if len(comp) == 4:
            add_column(comp[1], comp[2], comp[3])


    #-- force referral
    elif message_text.startswith("/"):
        welcome_message(recipient_id, Const.CUSTOMER_REFERRAL, message_text[1:])


    #-- return home
    elif message_text.lower() in Const.RESERVED_MENU_REPLIES:
        if storefront_query.count() > 0:
            product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4)
            if product_query.count() > 0:
                Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4).delete()

        Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state < 4).delete()
        db.session.commit()

        send_admin_carousel(recipient_id)


    #-- quit message
    elif message_text.lower() in Const.RESERVED_STOP_REPLIES:
        if storefront_query.count() > 0:
            product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4)
            if product_query.count() > 0:
                Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4).delete()

        Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state < 4).delete()
        db.session.commit()

        send_text(recipient_id, Const.GOODBYE_MESSAGE)

    else:
        #-- has active storefront
        if storefront_query.count() > 0:
            #-- look for in-progress product creation
            product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4)
            if product_query.count() > 0:
                product = product_query.order_by(Product.added.desc()).scalar()

                #-- name submitted
                if product.creation_state == 0:
                    product.creation_state = 1
                    product.display_name = message_text
                    product.name = re.sub(r'[\'\"\ \:\/\?\#\&\=\\]', "", message_text)
                    product.prebot_url = "http://prebot.me/{product_name}".format(product_name=product.name)
                    db.session.commit()

                    send_text(recipient_id, "Great! Now add a video about what you are pre-selling.")

                return "OK", 200

            else:
                product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.broadcast_message == "_{PENDING}_")
                if product_query.count() > 0:
                    product = product_query.first()
                    product.broadcast_message = message_text
                    db.session.commit()

                    try:
                        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('UPDATE `products` SET `broadcast_message` = "{broadcast_message}" WHERE `storefront_id` = {storefront_id};'.format(broadcast_message=product.broadcast_message, storefront_id=storefront_query.first().id))
                            cur.execute('UPDATE `subscriptions` SET `broadcast` = 1 WHERE `storefront_id` = {storefront_id};'.format(storefront_id=storefront_query.first().id))
                            conn.commit()

                    except mysql.Error, e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()

                    send_text(recipient_id, "Your message will be broadcasted as soon as resources allow.")
                    send_admin_carousel(recipient_id)

                else:
                    welcome_message(recipient_id, Const.CUSTOMER_REFERRAL, message_text)

        else:
            #-- look for in-progress storefront creation
            query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state < 4)
            if query.count() > 0:
                storefront = query.first()

                #-- name submitted
                if storefront.creation_state == 0:
                    storefront.creation_state = 1
                    storefront.display_name = message_text
                    storefront.name = re.sub(r'[\'\"\ \:\/\?\#\&\=\\]', "", message_text)
                    storefront.prebot_url = "http://prebot.me/{storefront_name}".format(storefront_name=storefront.name)
                    db.session.commit()

                    send_text(recipient_id, "Explain what you are making and what your Pre subscribers will receive.")

                #-- description entered
                elif storefront.creation_state == 1:
                    storefront.creation_state = 2
                    storefront.description = message_text
                    db.session.commit()

                    send_text(recipient_id, "Upload a Shopbot profile image.")

                return "OK", 200

            else:
                welcome_message(recipient_id, Const.CUSTOMER_REFERRAL, message_text)




#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#

@app.route('/', methods=['POST'])
def webook():

    if 'is_echo' in request.data:
        return "OK", 200

    #if 'delivery' in request.data or 'read' in request.data or 'optin' in request.data:
    #    return "OK", 200

    data = request.get_json()

    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    logger.info("[=-=-=-=-=-=-=-[POST DATA]-=-=-=-=-=-=-=-=]")
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    logger.info(data)
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")

    #drop_sqlite()
    #return "OK", 200

    if data['object'] == "page":
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                sender_id = messaging_event['sender']['id']
                recipient_id = messaging_event['recipient']['id']  # the recipient's ID, which should be your page's facebook ID
                timestamp = messaging_event['timestamp']

                message_id = None
                message_text = None
                quick_reply = None

                if sender_id == "177712676037903":
                    logger.info("-=- MESSAGE-ECHO -=-")
                    return "OK", 200

                if 'delivery' in messaging_event:  # delivery confirmation
                    logger.info("-=- DELIVERY-CONFIRM -=-")
                    return "OK", 200

                if 'read' in messaging_event:  # read confirmation
                    logger.info("-=- READ-CONFIRM -=- %s" % (recipient_id))
                    send_tracker("read-receipt", sender_id, "")
                    return "OK", 200

                if 'optin' in messaging_event:  # optin confirmation
                    logger.info("-=- OPT-IN -=-")
                    return "OK", 200


                #-- check mysql for user
                try:
                    conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('SELECT `id` FROM `users` WHERE `fb_psid` = "{fb_psid}" LIMIT 1;'.format(fb_psid=sender_id))
                        row = cur.fetchone()

                        if row is None:
                            send_tracker("sign-up", sender_id, "")

                            referral = "/"
                            if 'referral' in messaging_event:
                                referral = messaging_event['referral']['ref']

                            add_new_user(sender_id, referral)
                            send_video(sender_id, "http://{ip_addr}/videos/intro_all.mp4".format(ip_addr=Const.WEB_SERVER_IP), "179590205850150")

                except mysql.Error, e:
                    logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                finally:
                    if conn:
                        conn.close()



                #-- entered via url referral
                if 'referral' in messaging_event:
                    welcome_message(sender_id, Const.CUSTOMER_REFERRAL, messaging_event['referral']['ref'][1:])
                    return "OK", 200


                #-- look for created storefront
                storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 4)
                logger.info("STOREFRONTS -->%s" % (Storefront.query.filter(Storefront.owner_id == sender_id).all()))

                if storefront_query.count() > 0:
                    logger.info("PRODUCTS -->%s" % (Product.query.filter(Product.storefront_id == storefront_query.first().id).all()))
                    logger.info("SUBSCRIPTIONS -->%s" % (Subscription.query.filter(Subscription.storefront_id == storefront_query.first().id).all()))


                #-- postback response w/ payload
                if 'postback' in messaging_event:  # user clicked/tapped "postback" button in earlier message
                    payload = messaging_event['postback']['payload']
                    logger.info("-=- POSTBACK RESPONSE -=- (%s)" % (payload))
                    received_payload_button(sender_id, payload)
                    return "OK", 200


                #-- actual message
                if 'message' in messaging_event:
                    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECEIVED ->{message}".format(message=messaging_event['sender']))

                    message = messaging_event['message']
                    message_id = message['mid']
                    message_text = ""

                    #-- insert to log
                    write_message_log(sender_id, message_id, message)

                    if 'attachments' in message:
                        for attachment in message['attachments']:
                            recieved_attachment(sender_id, attachment['type'], attachment['payload'])
                        return "OK", 200


                    if 'quick_reply' in message:
                        quick_reply = message['quick_reply']['payload'].encode('utf-8')
                        logger.info("QR --> {quick_replies}".format(quick_replies=message['quick_reply']['payload'].encode('utf-8')))
                        received_quick_reply(sender_id, quick_reply)
                        return "OK", 200


                    if 'text' in message:
                        received_text_response(sender_id, message['text'])
                        return "OK", 200

                else:
                    send_text(sender_id, Const.UNKNOWN_MESSAGE)

    return "OK", 200


#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


@app.route('/', methods=['GET'])
def verify():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= GET --   ({hub_mode})->{request}".format(hub_mode=request.args.get('hub.mode'), request=request.args))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == Const.VERIFY_TOKEN:
            logger.info("TOKEN MISMATCH! [%s] != [%s]" % (request.args.get('hub.verify_token'), Const.VERIFY_TOKEN))
            return "Verification token mismatch", 403
        return request.args['hub.challenge'], 200

    return "OK", 200

#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#

def send_typing_indicator(recipient_id, is_typing):

    if is_typing:
        sender_action = "typing_on"

    else:
        sender_action = "typing_off"

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'sender_action' : sender_action
    }

    send_message(json.dumps(data))


def send_text(recipient_id, message_text, quick_replies=None):
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'text' : message_text
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_image(recipient_id, url, quick_replies=None):
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type' : "image",
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


def send_video(recipient_id, url, attachment_id=None, quick_replies=None):
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            "id" : recipient_id
        },
        'message' : {
            'attachment' : {
                'type' : "video",
                'payload' : {
                    'url' : url,
                    'is_reusable' : True
                }
            }
        }
    }

    if attachment_id is None:
        data['message']['attachment']['payload'] = {
            'url' : url,
            'is_reusable' : True
        }

    else:
        data['message']['attachment']['payload'] = { 'attachment_id' : attachment_id }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_message(payload):
    logger.info("send_message(payload={payload})".format(payload=payload))

    response = requests.post(
        url = "https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN),
        headers = { 'Content-Type' : "application/json" },
        data = payload
    )
    logger.info("SEND MESSAGE response: {response}".format(response=response.json()))

    # buf = cStringIO.StringIO()
    #
    # c = pycurl.Curl()
    # c.setopt(c.HTTPHEADER, ["Content-Type: application/json"])
    # c.setopt(c.URL, "https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN))
    # c.setopt(c.POST, 1)
    # c.setopt(c.POSTFIELDS, payload)
    # c.setopt(c.CONNECTTIMEOUT, 300)
    # c.setopt(c.TIMEOUT, 60)
    # c.setopt(c.FAILONERROR, True)
    #
    # try:
    #     c.perform()
    #     logger.info("SEND MESSAGE response code: {code}".format(code=c.getinfo(c.RESPONSE_CODE)))
    #     c.close()
    #
    # except pycurl.error, error:
    #     errno, errstr = error
    #     logger.info("SEND MESSAGE Error: -({errno})- {errstr}".format(errno=errno, errstr=errstr))
    #
    # finally:
    #     buf.close()

    return True


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


if __name__ == '__main__':
    from gevent import monkey
    monkey.patch_all()

    logger.info("Firin up FbBot using verify token [{verify_token}].".format(verify_token=Const.VERIFY_TOKEN))
    app.run(debug=True)
