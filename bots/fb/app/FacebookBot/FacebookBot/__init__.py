#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import cStringIO
import hashlib
import json
import locale
import logging
import os
import re
import subprocess
import threading
import time

from datetime import datetime

import MySQLdb as mysql
import pycurl
import requests

from dateutil.relativedelta import relativedelta
from flask import Flask, escape, request
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
    added = db.Column(db.DateTime)

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
    attachment_id = db.Column(db.String(100))
    price = db.Column(db.Float)
    prebot_url = db.Column(db.String(128), unique=True)
    release_date = db.Column(db.DateTime)
    added = db.Column(db.DateTime)

    def __init__(self, storefront_id, creation_state=0):
        self.storefront_id = storefront_id
        self.creation_state = creation_state
        self.description= ""
        self.price = 0.0
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
    prebot_url = db.Column(db.String(128), unique=True)
    added = db.Column(db.DateTime)

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
    added = db.Column(db.DateTime)

    def __init__(self, storefront_id, product_id, customer_id, enabled=1):
        self.storefront_id = storefront_id
        self.product_id = product_id
        self.customer_id = customer_id
        self.enabled = enabled
        self.added = datetime.utcnow()

    def __repr__(self):
        return "<Subscription storefront_id=%d, product_id=%d, customer_id=%d, enabled=%d>" % (self.storefront_id, self.product_id, self.customer_id, self.enabled)



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



def async_send_evt_tracker(urls):
    logger.info("send_evt_tracker(len(urls)=%d)" % (len(urls)))

    #responses = (grequests.get(u) for u in urls)
    #grequests.map(responses)



def send_tracker(category, action, label):
    logger.info("send_tracker(category={category}, action={action}, label={label})".format(category=category, action=action, label=label))

    client_id = hashlib.md5(label.encode()).hexdigest()
    src_app = "facebook"
    username = ""
    chat_id = category
    value = ""

    urls = [
        "http://beta.modd.live/api/user_tracking.php?username={username}&chat_id={chat_id}".format(username=label, chat_id=action),
        "http://beta.modd.live/api/bot_tracker.php?src=facebook&category={category}&action={action}&label={label}&value={value}&cid={cid}".format(category=category, action=category, label=action, value=value, cid=hashlib.md5(label.encode()).hexdigest()),
        "http://beta.modd.live/api/bot_tracker.php?src=facebook&category=user-message&action=user-message&label={label}&value={value}&cid={cid}".format(label=action, value=value, cid=hashlib.md5(label.encode()).hexdigest())
    ]

    #responses = (grequests.get(u) for u in urls)
    #grequests.map(responses)

    return True


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
            'type' : Const.CARD_BTN_POSTBACK,
            'payload' : payload,
            'title' : caption
        }

    elif btn_type == Const.CARD_BTN_URL:
        button = {
            'type' : Const.CARD_BTN_URL,
            'url' : url,
            'title' : caption
        }

    elif btn_type == Const.CARD_BTN_INVITE:
        button = {
            'type' : "element_share"
        }

    elif btn_type == Const.KWIK_BTN_TEXT:
        button = {
            'content_type' : Const.KWIK_BTN_TEXT,
            'title' : caption,
            'payload' : payload
        }

    return button


def build_quick_reply(btn_type, caption, payload, image_url=""):
    logger.info("build_quick_reply(btn_type={btn_type}, caption={caption}, payload={payload})".format(btn_type=btn_type, caption=caption, payload=payload))

    if btn_type == Const.KWIK_BTN_TEXT:
        button = {
            'content_type' : Const.KWIK_BTN_TEXT,
            'title' : caption,
            'payload' : payload
        }

    elif btn_type == Const.KWIK_BTN_IMAGE:
        button = {
            'type' : Const.KWIK_BTN_TEXT,
            'title' : caption,
            'image_url' : image_url,
            'payload' : payload
        }

    elif btn_type == Const.KWIK_BTN_LOCATION:
        button = {
            'type' : Const.KWIK_BTN_LOCATION,
            'title' : caption,
            'image_url' : image_url,
            'payload' : payload
        }

    else:
        button = {
            'type' : Const.KWIK_BTN_TEXT,
            'title' : caption,
            'payload' : payload
        }

    return button


def build_survey_message(recipient_id, question, options=None):
    logger.info("build_survey_message(recipient_id={recipient_id}, question={question}, options={options})".format(recipient_id=recipient_id, question=question, options=options))

    if options is None:
        options = ["Close"]

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type' : "survey",
                'question' : question,
                'msgid' : time.time(),
                'options' : options
            }
        }
    }

    return data


    # data =  {
    #     "type": "survey",
    #     "question": "What would you like to do?",
    #     "msgid": "3er45",
    #     "options": [
    #         "Eat",
    #         "Drink",
    #         {
    #             "type": "url",
    #             "title": "View website",
    #             "url": "www.gupshup.io"
    #         }
    #     ]
    # }


def build_card_element(index, title, subtitle, image_url, item_url, buttons=None):
    logger.info("build_card_element(index={index}, title={title}, subtitle={subtitle}, image_url={image_url}, item_url={item_url}, buttons={buttons})".format(index=index, title=title, subtitle=subtitle, image_url=image_url, item_url=item_url, buttons=buttons))

    element = {
        'title' : title,
        'subtitle' : subtitle,
        'image_url' : image_url,
        'item_url' : item_url
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
                            index = 0,
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
                    'elements' : cards
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    return data


def welcome_message(recipient_id, entry_type, deeplink=""):
    logger.info("welcome_message(recipient_id={recipient_id}, entry_type={entry_type}, deeplink={deeplink})".format(recipient_id=recipient_id, entry_type=entry_type, deeplink=deeplink))

    send_video(recipient_id, "http://{ip_addr}/videos/intro_all.mp4".format(ip_addr=Const.WEB_SERVER_IP), "179590205850150")
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
                subscription_query = Subscription.query.filter(Subscription.product_id == product.id).filter(Subscription.customer_id == customer.id)

                if subscription_query.count() == 0:
                    db.session.add(Subscription(storefront.id, product.id, customer.id))
                    db.session.commit()

                    try:
                        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('INSERT IGNORE INTO `subscriptions` (`id`, `user_id`, `storefront_id`, `product_id`, `added`) VALUES (NULL, "{user_id}", "{storefront_id}", "{product_id}", UTC_TIMESTAMP())'.format(user_id=customer.id, storefront_id=storefront.id, product_id=product.id))
                            conn.commit()

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
                subscription_query = Subscription.query.filter(Subscription.storefront_id == storefront.id).filter(Subscription.product_id == product.id).filter(Subscription.customer_id == customer.id)

                if subscription_query.count() == 0:
                    db.session.add(Subscription(storefront.id, product.id, customer.id))
                    db.session.commit()

                    try:
                        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('INSERT IGNORE INTO `subscriptions` (`id`, `user_id`, `storefront_id`, `product_id`, `added`) VALUES (NULL, "{user_id}", "{storefront_id}", "{product_id}", UTC_TIMESTAMP())'.format(user_id=customer.id, storefront_id=storefront.id, product_id=product.id))
                            conn.commit()

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
                index = 0,
                title = "Create Shop",
                subtitle = "",
                image_url = Const.IMAGE_URL_CREATE_SHOP,
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
            storefront.prebot_url = "http://prebot.me/shop/{storefront_id}".format(storefront_id=storefront.id)


        product_query = Product.query.filter(Product.storefront_id == storefront.id)
        if product_query.count() == 0:
            cards.append(
                build_card_element(
                    index = 1,
                    title = "Add Item",
                    subtitle = "",
                    image_url = Const.IMAGE_URL_ADD_PRODUCT,
                    item_url = None,
                    buttons = [
                        build_button(Const.CARD_BTN_POSTBACK, caption="Add Item", payload=Const.PB_PAYLOAD_ADD_PRODUCT)
                    ]
                )
            )

        else:
            product = product_query.order_by(Product.added.desc()).scalar()

            if product.prebot_url is None:
                product.prebot_url = "http://prebot.me/reserve/{product_id}".format(product_id=product.id)

            if product.display_name is None:
                product.display_name = "[NAME NOT SET]"

            if product.video_url is None:
                product.image_url = Const.IMAGE_URL_ADD_PRODUCT
                product.video_url = None

            subscriber_query = Subscription.query.filter(Subscription.product_id == product.id).filter(Subscription.enabled == 1)
            if subscriber_query.count() == 1:
                cards.append(
                    build_card_element(
                        index = 1,
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
                        index = 1,
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
                    index = 1,
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
                index = 2,
                title = "Share Shop",
                subtitle = "",
                image_url = Const.IMAGE_URL_SHARE_STOREFRONT,
                item_url = "http://prebot.me/shop/{storefront_id}".format(storefront_id=storefront.id),
                buttons = [
                    build_button(Const.CARD_BTN_POSTBACK, caption="Share Shop", payload=Const.PB_PAYLOAD_SHARE_STOREFRONT)
                ]
            )
        )

    cards.append(
        build_card_element(
            index = 3,
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
            index = 3,
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
                index = 0,
                title = storefront.display_name,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.prebot_url,
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
                        index = 0,
                        title = product.display_name,
                        subtitle = product.description,
                        image_url = product.image_url,
                        item_url = product.prebot_url,
                        buttons = [
                            build_button(Const.CARD_BTN_URL, caption="Tap to Reserve", url="https://prebot.chat/reserve/{product_id}".format(product_id=product.id)),
                            build_button(Const.CARD_BTN_INVITE)
                        ]
                    ),
                    build_card_element(
                        index = 1,
                        title = storefront.display_name,
                        subtitle = storefront.description,
                        image_url = storefront.logo_url,
                        item_url = storefront.prebot_url,
                        buttons = [
                            build_button(Const.CARD_BTN_INVITE)
                        ]
                    ),
                    build_card_element(
                        index = 3,
                        title = "View Shops",
                        subtitle = "",
                        image_url = Const.IMAGE_URL_MARKETPLACE,
                        item_url = "http://prebot.me/shops",
                        buttons = [
                            build_button(Const.CARD_BTN_URL, caption="View Shops", url="http://prebot.me/shops")
                        ]
                    ),
                    build_card_element(
                        index = 2,
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
                    build_button(Const.CARD_BTN_INVITE)
                ]
            )

        elif card_type == Const.CARD_TYPE_PREVIEW_STOREFRONT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = storefront.display_name,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.prebot_url,
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
                subtitle = "",
                image_url = storefront.logo_url,
                item_url = storefront.prebot_url,
                buttons = [
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
                item_url = product.video_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="Tap to Reserve", url="https://prebot.chat/reserve/{product_id}".format(product_id=product_id))
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
                subtitle = product.description,
                image_url = product.image_url,
                item_url = product.video_url,
                buttons = [
                    build_button(Const.CARD_BTN_INVITE)
                ]
            )

        else:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
                subtitle = product.description,
                image_url = product.image_url,
                item_url = product.video_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="Tap to Reserve", url="http://prebot.me/reserve/{product_id}".format(product_id=product_id))
                ]
            )

        send_message(json.dumps(data))



class VideoImageRenderer(threading.Thread):
    def __init__(self, src_url, out_img, at_time=0.33):
        self.stdout = None
        self.stderr = None
        threading.Thread.__init__(self)

        self.src_url = src_url
        self.out_img = out_img
        self.at_time = at_time

    def run(self):
        p = subprocess.Popen(
            ('/usr/bin/ffmpeg -ss 00:00:03 -i %s -frames:v 1 %s' % (self.src_url, self.out_img)).split(),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        self.stdout, self.stderr = p.communicate()




class ScreenShotRender(object):
    def thread_loader(self, args):
        logger.info("RUNNING THREAD -- <%s>" % (args))

        # run = subprocess.Popen(subprocess.list2cmdline(ffmpeg_args), shell=True)
        # run.communicate()

        p = subprocess.Popen(args, shell=True, stdout=subprocess.PIPE)
        p.stdout.close()
        p.wait()


        thread_name = threading.current_thread().name
        logger.info("Finished loading {name}".format(name=thread_name))

    def clean_up(self):
        logger.info("Cleaning up thread...")


@app.route('/', methods=['POST'])
def webook():

    if 'is_echo' in request.data:
        return "OK", 200

    #if 'delivery' in request.data or 'read' in request.data or 'optin' in request.data:
    #    return "OK", 200

    data = request.get_json()

    logger.info("\n\n[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    logger.info("[=-=-=-=-=-=-=-[POST DATA]-=-=-=-=-=-=-=-=]")
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    logger.info(data)
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")

    # return "OK", 200

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


                #-- drop sqlite data
                #drop_sqlite()



                #-- look for created storefront
                storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 4)
                logger.info("STOREFRONTS -->%s" % (Storefront.query.filter(Storefront.owner_id == sender_id).all()))

                if storefront_query.count() > 0:
                    logger.info("PRODUCTS -->%s" % (Product.query.filter(Product.storefront_id == storefront_query.first().id).all()))
                    logger.info("SUBSCRIPTIONS -->%s" % (Subscription.query.filter(Subscription.storefront_id == storefront_query.first().id).all()))

                #-- entered via url referral
                referral = ""
                if 'referral' in messaging_event:
                    referral = messaging_event['referral']['ref']
                    welcome_message(sender_id, Const.CUSTOMER_REFERRAL, referral[1:])
                    return "OK", 200


                #-- check sqlite for user
                users_query = Customer.query.filter(Customer.fb_psid == sender_id)
                logger.info("USERS -->%s" % (Customer.query.filter(Customer.fb_psid == sender_id).all()))
                if users_query.count() == 0:
                    db.session.add(Customer(fb_psid=sender_id, fb_name="", referrer=referral))
                    db.session.commit()

                    try:
                        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('INSERT IGNORE INTO `users` (`id`, `fb_psid`, `referrer`, `added`) VALUES (NULL, "{fbps_id}", "{referrer}", UTC_TIMESTAMP())'.format(fbps_id=sender_id, referrer=referral))
                            conn.commit()

                    except mysql.Error, e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()


                #-- postback response w/ payload
                if 'postback' in messaging_event:  # user clicked/tapped "postback" button in earlier message
                    payload = messaging_event['postback']['payload']
                    logger.info("-=- POSTBACK RESPONSE -=- (%s)" % (payload))

                    if payload == Const.PB_PAYLOAD_GREETING:
                        logger.info("----------=BOT GREETING @({timestamp})=----------".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
                        send_tracker("signup-fb-pre", sender_id, "")
                        welcome_message(sender_id, Const.MARKETPLACE_GREETING)

                    elif payload == Const.PB_PAYLOAD_CREATE_STOREFRONT:
                        send_tracker("button-create-shop", sender_id, "")

                        query = Storefront.query.filter(Storefront.owner_id == sender_id)
                        if query.count() > 0:
                            try:
                                deleted_rows = db.session.query(Storefront).delete()
                                db.session.commit()
                            except:
                                db.session.rollback()


                        db.session.add(Storefront(sender_id))
                        db.session.commit()

                        send_text(sender_id, "Give your Pre Shop Bot a name.")


                    elif payload == Const.PB_PAYLOAD_DELETE_STOREFRONT:
                        send_tracker("button-delete-shop", sender_id, "")

                        for storefront in Storefront.query.filter(Storefront.owner_id == sender_id):
                            send_text(sender_id, "{storefront_name} has been removed.".format(storefront_name=storefront.display_name))
                            Product.query.filter(Product.storefront_id == storefront.id).delete()

                        Storefront.query.filter(Storefront.owner_id == sender_id).delete()
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


                        send_admin_carousel(sender_id)


                    elif payload == Const.PB_PAYLOAD_ADD_PRODUCT:
                        send_tracker("button-add-item", sender_id, "")

                        # storefront = storefront_query.first()
                        # for product in Product.query.filter(Product.storefront_id == storefront.id):
                        #     Product.query.filter(Product.storefront_id == storefront.id).delete()

                        db.session.add(Product(storefront_query.first().id))
                        db.session.commit()

                        send_text(sender_id, "Give your pre-sale product or item a name.")


                    elif payload == Const.PB_PAYLOAD_DELETE_PRODUCT:
                        send_tracker("button-delete-item", sender_id, "")

                        storefront = storefront_query.first()
                        for product in Product.query.filter(Product.storefront_id == storefront.id):
                            send_text(sender_id, "Removing your existing product \"{product_name}\"...".format(product_name=product.display_name))
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


                        send_admin_carousel(sender_id)


                    elif payload == Const.PB_PAYLOAD_SHARE_STOREFRONT:
                        send_tracker("button-share", sender_id, "")
                        send_storefront_card(sender_id, storefront_query.first().id, Const.CARD_TYPE_SHARE_STOREFRONT)
                        send_admin_carousel(sender_id)


                    elif payload == Const.PB_PAYLOAD_SUPPORT:
                        send_tracker("button-support", sender_id, "")
                        send_text(sender_id, "Support for Prebot:\nprebot.me/support")


                    elif payload == Const.PB_PAYLOAD_RESERVE_PRODUCT:
                        send_tracker("button-reserve", sender_id, "")


                    else:
                        send_tracker("unknown-button", sender_id, "")
                        send_text(sender_id, "Button not recognized!")

                    return "OK", 200


                #-- actual message
                if 'message' in messaging_event:#.get('message'):
                    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECEIVED ->{message}".format(message=messaging_event['sender']))
                    message = messaging_event['message']
                    message_id = message['mid']
                    message_text = ""

                    #-- insert to log
                    write_message_log(sender_id, message_id, message)

                    if 'attachments' in message:
                        for attachment in message['attachments']:

                            #------- IMAGE MESSAGE
                            if attachment['type'] == "image":
                                logger.info("IMAGE: %s" % (attachment['payload']['url']))
                                query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 2)

                                if query.count() > 0:
                                    storefront = query.first()
                                    storefront.creation_state = 3
                                    storefront.logo_url = attachment['payload']['url']
                                    db.session.commit()

                                    send_text(sender_id, "Here's what your shop will look like:")
                                    send_storefront_card(sender_id, storefront.id, Const.CARD_TYPE_PREVIEW_STOREFRONT)

                            #------- VIDEO MESSAGE
                            elif attachment['type'] == "video":
                                logger.info("VIDEO: %s" % (attachment['payload']['url']))

                                #return "OK", 200

                                query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 1)

                                if query.count() > 0:
                                    file_path = os.path.dirname(os.path.realpath(__file__))
                                    timestamp = int(time.time())
                                    image_file = "/var/www/html/thumbs/{timestamp}.jpg".format(file_path=os.path.dirname(os.path.realpath(__file__)), timestamp=int(time.time()))

                                    image_renderer = VideoImageRenderer(attachment['payload']['url'], image_file)
                                    image_renderer.start()
                                    image_renderer.join()
                                    logger.info("FFMPEG RESULT:: %s" % (image_renderer.stdout))




                                    # ffmpeg_args = (
                                    #     "/usr/bin/ffmpeg",
                                    #     "-ss",
                                    #     "00:00:03",
                                    #     "-i",
                                    #     "{url}".format(url=attachment['payload']['url']),
                                    #     "-frames:v",
                                    #     "1",
                                    #     "{image_file}".format(image_file=image_file),
                                    # )
                                    #
                                    # ffmpeg_cmd = "/usr/bin/ffmpeg -ss 00:00:03 -i %s -frames:v 1 %s" % (attachment['payload']['url'], image_file)
                                    #cmd = "/usr/bin/ffmpeg -ss %s -i %s -frames:v %d %s" % ("00:00:03", attachment['payload']['url'], 1, image_file)

                                    # ss_renderer = ScreenShotRender()
                                    # thread = threading.Thread(target=ss_renderer.thread_loader, args=ffmpeg_cmd)
                                    # thread.start()
                                    # thread.join()


                                    #subprocess.call(ffmpeg_cmd)



                                    # subprocess.call("/usr/bin/ffmpeg -ss 00:00:03 -i {url} -frames:v 1 {image_file}".format(url=attachment['payload']['url'], image_file=image_file), shell=True)
                                    # subprocess.call(['/usr/bin/ffmpeg', '-ss', '00:00:03', '-i', '{url}'.format(url=attachment['payload']['url']), '-frames:v', '1', '{image_file}'.format(image_file=image_file)])


                                    # p = subprocess.Popen("/usr/bin/ffmpeg -ss 00:00:03 -i {url} -frames:v 1 {image_file}".format(url=attachment['payload']['url'], image_file=image_file), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                    # output = p.communicate()[0]
                                    # logger.info("::::: subprocess.Popen --> %s" % (output))


                                    #local_file = "{file_path}/videos/{timestamp}.mp4".format(file_path=file_path, timestamp=timestamp)
                                    #call(["ffmpeg", "-ss", "00:00:03", "-i", "https://video.xx.fbcdn.net/v/t42.3356-2/15930703_10154939964852244_8434126089172811776_n.mp4/video-1483809489.mp4?vabr=307778&oh=ddf77ffdf5239548a4d14edcf5334cb8&oe=58730491"])
                                    # f = open(local_file, 'wb')
                                    # f.write(urllib.urlopen(attachment['payload']['url']).read())
                                    # f.close()
                                    #
                                    # container = av.open(local_file)
                                    # video = next(s for s in container.streams if s.type == b'video')
                                    # for packet in container.demux(video):
                                    #     for frame in packet.decode():
                                    #         if frame.index == 20:
                                    #             frame.to_image().save("/var/www/html/thumbs/{timestamp}.jpg".format(file_path=file_path, timestamp=timestamp))
                                    #             break
                                    #
                                    # os.remove(local_file)
                                    product = query.order_by(Product.added.desc()).scalar()
                                    product.creation_state = 2
                                    product.image_url = "http://{ip_addr}/thumbs/{timestamp}.jpg".format(ip_addr=Const.WEB_SERVER_IP, timestamp=timestamp)
                                    product.video_url = attachment['payload']['url']
                                    db.session.commit()

                                    send_text(
                                        recipient_id = sender_id,
                                        message_text = "Select the date range your product will be exclusively available.",
                                        quick_replies = [
                                            build_quick_reply(Const.KWIK_BTN_TEXT, "Right Now", Const.PB_PAYLOAD_PRODUCT_RELEASE_NOW),
                                            build_quick_reply(Const.KWIK_BTN_TEXT, "Next Month", Const.PB_PAYLOAD_PRODUCT_RELEASE_30_DAYS),
                                            build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=2)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_60_DAYS),
                                            build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=3)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_90_DAYS),
                                            build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=4)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_120_DAYS)
                                        ]
                                    )

                        return "OK", 200

                    else:
                        if 'quick_reply' in message:
                            quick_reply = message['quick_reply']['payload'].encode('utf-8')
                            logger.info("QR --> {quick_replies}".format(quick_replies=message['quick_reply']['payload'].encode('utf-8')))

                            if quick_reply == Const.PB_PAYLOAD_SUBMIT_STOREFRONT:
                                send_tracker("button-submit-store", sender_id, "")

                                storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 3)
                                if storefront_query.count() > 0:
                                    storefront = storefront_query.first();
                                    storefront.creation_state = 4
                                    storefront.added = datetime.utcnow()
                                    db.session.commit()

                                    try:
                                        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                                        with conn:
                                            cur = conn.cursor(mysql.cursors.DictCursor)
                                            cur.execute('INSERT IGNORE INTO `storefronts` (`id`, `owner_id`, `name`, `display_name`, `description`, `logo_url`, `prebot_url`, `added`) VALUES (NULL, {owner_id}, "{name}", "{display_name}", "{description}", "{logo_url}", "{prebot_url}", UTC_TIMESTAMP())'.format(owner_id=users_query.first().id, name=storefront.name, display_name=storefront.display_name, description=storefront.description, logo_url=storefront.logo_url, prebot_url=storefront.prebot_url))
                                            conn.commit()

                                    except mysql.Error, e:
                                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                                    finally:
                                        if conn:
                                            conn.close()


                                    send_text(sender_id, "{storefront_name} has been successful created..\n{storefront_url}".format(storefront_name=storefront.display_name, storefront_url=re.sub(r'https?:\/\/', '', storefront.prebot_url)))
                                    send_admin_carousel(sender_id)

                                    payload = {
                                        'channel' : "#pre",
                                        'username' : "fbprebot",
                                        'icon_url' : "https://scontent.fsnc1-4.fna.fbcdn.net/t39.2081-0/p128x128/15728018_267940103621073_6998097150915641344_n.png",
                                        'text' : "*{sender_id}* just created a shop named _{storefront_name}_.".format(sender_id=sender_id, storefront_name=storefront.display_name),
                                        'attachments' : [{
                                            'image_url' : storefront.logo_url
                                        }]
                                    }
                                    response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })


                            elif quick_reply == Const.PB_PAYLOAD_REDO_STOREFRONT:
                                send_tracker("button-redo-store", sender_id, "")

                                storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 3)
                                if storefront_query.count() > 0:
                                    Storefront.query.filter(Storefront.owner_id == sender_id).delete()
                                    db.session.commit()

                                db.session.add(Storefront(sender_id))
                                db.session.commit()

                                send_text(sender_id, "Give your Pre Shop Bot a name.")

                            elif quick_reply == Const.PB_PAYLOAD_CANCEL_STOREFRONT:
                                send_tracker("button-cancel-store", sender_id, "")

                                storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 3)
                                if storefront_query.count() > 0:
                                    storefront = storefront_query.first()
                                    send_text(sender_id, "Canceling your {storefront_name} shop creation...".format(storefront_name=storefront.display_name))
                                    Storefront.query.filter(Storefront.owner_id == sender_id).delete()
                                    db.session.commit()

                                send_admin_carousel(sender_id)

                            elif re.search('PRODUCT_RELEASE_(\d+)_DAYS', quick_reply) is not None:
                                match = re.match(r'PRODUCT_RELEASE_(\d+)_DAYS', quick_reply)
                                send_tracker("button-product-release-{days}-days-store".format(days=match.group(1)), sender_id, "")

                                product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 2)
                                if product_query.count() > 0:
                                    product = product_query.order_by(Product.added.desc()).scalar()
                                    product.release_date = (datetime.utcnow() + relativedelta(months=int(int(match.group(1)) / 30))).replace(hour=0, minute=0, second=0, microsecond=0)
                                    product.description = "Pre-release ends {release_date}".format(release_date=product.release_date.strftime('%a, %b %-d'))
                                    product.creation_state = 3
                                    db.session.commit()

                                    send_text(sender_id, "Here's what your product will look like:")
                                    send_product_card(sender_id, product.id, Const.CARD_TYPE_PREVIEW_PRODUCT)

                            elif quick_reply == Const.PB_PAYLOAD_SUBMIT_PRODUCT:
                                send_tracker("button-submit-product", sender_id, "")

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

                                    except mysql.Error, e:
                                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                                    finally:
                                        if conn:
                                            conn.close()


                                    send_text(sender_id, "Success! You have added {product_name}.\n{product_url}".format(product_name=product.display_name, product_url=re.sub(r'https?:\/\/', '', product.prebot_url)))
                                    send_product_card(sender_id, product.id, Const.CARD_TYPE_SHARE_PRODUCT)

                                    payload = {
                                        'channel' : "#pre",
                                        'username' : "fbprebot",
                                        'icon_url' : "https://scontent.fsnc1-4.fna.fbcdn.net/t39.2081-0/p128x128/15728018_267940103621073_6998097150915641344_n.png",
                                        'text' : "*{sender_id}* just created a product named _{product_name}_ for the shop _{storefront_name}_.\n<{video_url}>".format(sender_id=sender_id, product_name=product.display_name, storefront_name=storefront_query.first().display_name, video_url=product.video_url),
                                        'attachments' : [{
                                            'image_url' : product.image_url
                                        }]
                                    }
                                    response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })

                                send_admin_carousel(sender_id)

                            elif quick_reply == Const.PB_PAYLOAD_REDO_PRODUCT:
                                send_tracker("button-redo-product", sender_id, "")

                                product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id)
                                if product_query.count() > 0:
                                    product = product_query.order_by(Product.added.desc()).scalar()
                                    Product.query.filter(Product.storefront_id == storefront_query.first().id).delete()

                                db.session.add(Product(storefront_query.first().id))
                                db.session.commit()

                                send_text(sender_id, "Give your product a name.")

                            elif quick_reply == Const.PB_PAYLOAD_CANCEL_PRODUCT:
                                send_tracker("button-undo-product", sender_id, "")

                                product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id)
                                if product_query.count() > 0:
                                    product = product_query.order_by(Product.added.desc()).scalar()
                                    send_text(sender_id, "Canceling your {product_name} product creation...".format(product_name=product.display_name))

                                    Product.query.filter(Product.storefront_id == storefront_query.first().id).delete()
                                    db.session.commit()

                                send_admin_carousel(sender_id)



                        #-- text entry
                        else:
                            message_text = ""
                            if 'text' in message:
                                message_text = message['text']  # the message's text

                                if message_text == "/:flush_sqlite:/":
                                    drop_sqlite()
                                    send_text(sender_id, "Purged sqlite db")
                                    send_admin_carousel(recipient_id)
                                    return "OK", 200


                                #-- force referral
                                if message_text.startswith("/"):
                                    welcome_message(sender_id, Const.CUSTOMER_REFERRAL, message_text[1:])
                                    return "OK", 200


                                #-- return home
                                if message_text.lower() in Const.RESERVED_MENU_REPLIES:
                                    if storefront_query.count() > 0:
                                        product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4)
                                        if product_query.count() > 0:
                                            Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4).delete()

                                    Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state < 4).delete()
                                    db.session.commit()

                                    send_admin_carousel(sender_id)
                                    return "OK", 200

                                #-- quit message
                                if message_text.lower() in Const.RESERVED_STOP_REPLIES:
                                    if storefront_query.count() > 0:
                                        product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4)
                                        if product_query.count() > 0:
                                            Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4).delete()

                                    Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state < 4).delete()
                                    db.session.commit()

                                    send_text(sender_id, Const.GOODBYE_MESSAGE)
                                    return "OK", 200

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
                                            product.name = message_text.replace(" ", "_")
                                            product.prebot_url = "http://prebot.me/reserve/{storefront_id}".format(storefront_id=storefront_query.first().id)
                                            db.session.commit()

                                            send_text(sender_id, "Upload a product video under 30 seconds.")

                                        return "OK", 200

                                    else:
                                        welcome_message(sender_id, Const.CUSTOMER_REFERRAL, message_text)

                                else:
                                    #-- look for in-progress storefront creation
                                    query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state < 4)
                                    if query.count() > 0:
                                        storefront = query.first()

                                        #-- name submitted
                                        if storefront.creation_state == 0:
                                            storefront.creation_state = 1
                                            storefront.display_name = message_text
                                            storefront.name = message_text.replace(" ", "_")
                                            storefront.prebot_url = "http://prebot.me/shop/{storefront_id}".format(storefront_id=storefront.id)
                                            db.session.commit()

                                            send_text(sender_id, "Give {storefront_name} a description.".format(storefront_name=storefront.display_name))

                                        #-- description entered
                                        elif storefront.creation_state == 1:
                                            storefront.creation_state = 2
                                            storefront.description = message_text
                                            db.session.commit()

                                            send_text(sender_id, "Upload an avatar image for {storefront_name}".format(storefront_name=storefront.display_name))

                                    else:
                                        welcome_message(sender_id, Const.CUSTOMER_REFERRAL, message_text)

                else:
                    send_text(sender_id, Const.UNKNOWN_MESSAGE)

    return "OK", 200



#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#
#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#



@app.route('/', methods=['GET'])
def verify():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= GET --   ({hub_mode})->{request}".format(hub_mode=request.args.get('hub.mode'), request=request.args))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == Const.VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args['hub.challenge'], 200

    return "OK", 200

#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#
#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#

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
    logger.info("\nsend_message(payload={payload})".format(payload=payload))

    timestamp = int(time.time() * 1000)
    buf = cStringIO.StringIO()

    c = pycurl.Curl()
    c.setopt(c.HTTPHEADER, ["Content-Type: application/json"])
    c.setopt(c.URL, "https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN))
    c.setopt(c.POST, 1)
    c.setopt(c.POSTFIELDS, payload)
    c.setopt(c.CONNECTTIMEOUT, 300)
    c.setopt(c.TIMEOUT, 60)
    c.setopt(c.FAILONERROR, True)

    try:
        c.perform()
        logger.info("SEND MESSAGE response code: {code}".format(code=c.getinfo(c.RESPONSE_CODE)))
        c.close()

    except pycurl.error, error:
        errno, errstr = error
        logger.info("SEND MESSAGE Error: -({errno})- {errstr}".format(errno=errno, errstr=errstr))

    finally:
        #logger.info("SEND MESSAGE body: {body}".format(body=buf.getvalue()))
        buf.close()

    return True


if __name__ == '__main__':
    from gevent import monkey
    monkey.patch_all()

    logger.info("Firin up FbBot using verify token [{verify_token}].".format(verify_token=Const.VERIFY_TOKEN))
    app.run(debug=True)
