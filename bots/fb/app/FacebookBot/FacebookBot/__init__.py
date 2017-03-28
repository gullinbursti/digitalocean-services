#!/usr/bin/env python
# encoding=utf8

import calendar
import hashlib
import json
import locale
import logging
import math
import os
import random
import re
import subprocess
import sys
import threading
import time

from datetime import datetime

import emoji
import MySQLdb as mysql
import pytz
import qrtools
import requests
import stripe

from dateutil.tz import tzoffset
from dateutil.relativedelta import relativedelta
from flask import Flask, abort, flash, redirect, request
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeSerializer, BadSignature
from PIL import Image
from stripe import CardError


from constants import Const


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data/sqlite3/prebotfb.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

locale.setlocale(locale.LC_ALL, 'en_US.utf8')

reload(sys)
sys.setdefaultencoding('utf-8')

db = SQLAlchemy(app)

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler("/var/log/FacebookBot.log")
formatter = logging.Formatter('%(asctime)s - %(message)s', '%d-%b-%Y %H:%M:%S')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)


stripe.api_key = Const.STRIPE_DEV_API_KEY


#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#



class CoerceUTF8(db.TypeDecorator):
    """Safely coerce Python bytestrings to Unicode
    before passing off to the database."""

    impl = db.Unicode

    def process_bind_param(self, value, dialect):
        if isinstance(value, str):
            value = value.decode('utf-8')
        return value



class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    fb_psid = db.Column(db.String(255))
    fb_name = db.Column(CoerceUTF8)
    email = db.Column(db.String(255))
    referrer = db.Column(db.String(255))
    paypal_name = db.Column(db.String(255))
    paypal_email = db.Column(db.String(255))
    bitcoin_addr = db.Column(db.String(255))
    stripe_id = db.Column(db.String(255))
    card_id = db.Column(db.String(255))
    bitcoin_id = db.Column(db.String(255))
    storefront_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    purchase_id = db.Column(db.Integer)
    points = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, fb_psid, referrer="/"):
        self.fb_psid = fb_psid
        self.referrer = referrer
        self.points = 0
        self.added = int(time.time())

    def __repr__(self):
        return "<Customer id=%s, fb_psid=%s, fb_name=%s, email=%s, bitcoin_addr=%s, referrer=%s, paypal_name=%s, paypal_email=%s, storefront_id=%s, product_id=%s, purchase_id=%s, points=%s, added=%s>" % (self.id, self.fb_psid, self.fb_name, self.email, self.bitcoin_addr, self.referrer, self.paypal_name, self.paypal_email, self.storefront_id, self.product_id, self.purchase_id, self.points, self.added)


class FBUser(db.Model):
    __tablename__ = "fb_users"

    id = db.Column(db.Integer, primary_key=True)
    fb_psid = db.Column(db.String(255))
    first_name = db.Column(CoerceUTF8)
    last_name = db.Column(CoerceUTF8)
    profile_pic_url = db.Column(db.String(255))
    locale = db.Column(db.String(255))
    timezone = db.Column(db.Integer)
    gender = db.Column(db.String(255))
    payments_enabled = db.Column(db.Boolean)
    added = db.Column(db.Integer)


    @property
    def first_name_utf8(self):
        return self.first_name.encode('utf-8')

    @property
    def last_name_utf8(self):
        return self.last_name.encode('utf-8')

    @property
    def full_name_utf8(self):
        return "%s %s" % (self.first_name_utf8, self.last_name_utf8)

    @property
    def local_dt(self):
        return datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.FixedOffset((self.timezone or 0) * 60))

    @property
    def profile_image(self):
        try:
            return Image.open(requests.get(self.profile_pic_url, stream=True).raw)
        except IOError:
            return None


    def __init__(self, fb_psid, graph):
        self.fb_psid = fb_psid
        self.first_name = graph['first_name'].encode('utf-8') if 'first_name' in graph else None
        self.last_name = graph['last_name'].encode('utf-8') if 'last_name' in graph else None
        self.profile_pic_url = graph['profile_pic'] if 'profile_pic' in graph else None
        self.locale = graph['locale'] if 'locale' in graph else None
        self.timezone = graph['timezone'] if 'timezone' in graph else None
        self.gender = graph['gender'] if 'gender' in graph else None
        self.payments_enabled = graph['is_payment_enabled'] if 'is_payment_enabled' in graph else False
        self.added = int(time.time())

    def __repr__(self):
        return "<FBUser id=%s, fb_psid=%s, first_name=%s, last_name=%s, profile_pic_url=%s, locale=%s, timezone=%s, gender=%s, payments_enabled=%s, added=%s, [full_name_utf8=%s, local_dt=%s, profile_image=%s]>" % (self.id, self.fb_psid, self.first_name, self.last_name, self.profile_pic_url, self.locale, self.timezone, self.gender, self.payments_enabled, self.added, self.full_name_utf8, self.local_dt, self.profile_image)


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    fb_psid = db.Column(db.String(255))
    source = db.Column(db.String(255))
    email = db.Column(db.String(255))
    full_name = db.Column(db.String(255))
    acct_number = db.Column(db.String(255))
    expiration = db.Column(db.DateTime)
    cvc = db.Column(db.String(255))
    creation_state = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, fb_psid, source):
        self.fb_psid = fb_psid
        self.source = source
        self.creation_state = 0
        self.added = int(time.time())

    def __repr__(self):
        return "<Payment id=%s, fb_psid=%s, source=%s, email=%s, full_name=%s, acct_number=%s, expiration=%s, cvc=%s, creation_state=%s, added=%s" % (self.id, self.fb_psid, self.source, self.email, self.full_name, self.acct_number, self.expiration, self.cvc, self.creation_state, self.added)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    fb_psid = db.Column(db.String(255))
    storefront_id = db.Column(db.Integer)
    type_id = db.Column(db.Integer)
    creation_state = db.Column(db.Integer)
    name = db.Column(db.String(255))
    display_name = db.Column(CoerceUTF8)
    description = db.Column(CoerceUTF8)
    tags = db.Column(CoerceUTF8)
    image_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    broadcast_message = db.Column(db.String(255))
    attachment_id = db.Column(db.String(255))
    price = db.Column(db.Float)
    prebot_url = db.Column(db.String(255))
    views = db.Column(db.String(255))
    avg_rating = db.Column(db.Float)
    physical_url = db.Column(db.String(255))
    release_date = db.Column(db.Integer)
    added = db.Column(db.Integer)


    @property
    def display_name_utf8(self):
        return self.display_name.encode('utf-8') if self.display_name is not None else None

    @property
    def description_utf8(self):
        return self.description.encode('utf-8') if self.description is not None else None

    @property
    def tags_list(self):
        return [] if self.tags is None else [tag.encode('utf-8') for tag in self.tags.replace(",", " ").split(" ")]

    @property
    def messenger_url(self):
        return re.sub(r'^.*\/(.*)$', r'm.me/lmon8?ref=/\1', self.prebot_url) if self.prebot_url is not None else None

    @property
    def thumb_image_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-256.\2', self.image_url) if self.image_url is not None else None

    @property
    def landscape_image_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-400.\2', self.image_url) if self.image_url is not None else None

    @property
    def widescreen_image_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-1280.\2', self.image_url) if self.image_url is not None else None

    @property
    def portrait_image_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-480.\2', self.image_url) if self.image_url is not None else None


    def __init__(self, fb_psid, storefront_id):
        self.fb_psid = fb_psid
        self.storefront_id = storefront_id
        self.creation_state = 0
        self.price = 1.99
        self.views = 0
        self.avg_rating = 0.0
        self.added = int(time.time())



    def __repr__(self):
        return "<Product id=%s, fb_psid=%s, storefront_id=%s, type_id=%s, creation_state=%s, name=%s, display_name=%s, description=%s, tags=%s, image_url=%s, video_url=%s, prebot_url=%s, views=%s, avg_rating=%.2f, physical_url=%s, release_date=%s, added=%s>" % (self.id, self.fb_psid, self.storefront_id, self.type_id, self.creation_state, self.name, self.display_name_utf8, self.description_utf8, self.tags_list, self.image_url, self.video_url, self.prebot_url, self.views, self.avg_rating, self.physical_url, self.release_date, self.added)


class Purchase(db.Model):
    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer)
    storefront_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    type = db.Column(db.Integer)
    charge_id = db.Column(db.String(255))
    claim_state = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, customer_id, storefront_id, product_id, type, charge_id=None):
        self.customer_id = customer_id
        self.storefront_id = storefront_id
        self.product_id = product_id
        self.type = type
        self.charge_id = charge_id
        self.claim_state = 0
        self.added = int(time.time())

    def __repr__(self):
        return "<Purchase id=%s, customer_id=%s, storefront_id=%s, product_id=%s, type=%s, charge_id=%s, claim_state=%s, added=%s>" % (self.id, self.customer_id, self.storefront_id, self.product_id, self.type, self.charge_id, self.claim_state, self.added)


class Rating(db.Model):
    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer)
    fb_psid = db.Column(db.String(255))
    stars = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, product_id, fb_psid, stars):
        self.product_id = product_id
        self.fb_psid = fb_psid
        self.stars = int(stars)
        self.added = int(time.time())

    def __repr__(self):
        return "<Rating id=%s, product_id=%s, fb_psid=%s, stars=%s, added=%s>" % (self.id, self.product_id, self.fb_psid, self.stars, self.added)


class Storefront(db.Model):
    __tablename__ = "storefronts"

    id = db.Column(db.Integer, primary_key=True)
    fb_psid = db.Column(db.String(255))
    creation_state = db.Column(db.Integer)
    type_id = db.Column(db.Integer)
    name = db.Column(db.String(255))
    display_name = db.Column(CoerceUTF8)
    description = db.Column(CoerceUTF8)
    logo_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    prebot_url = db.Column(db.String(255))
    giveaway = db.Column(db.Integer)
    views = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, fb_psid, type_id=1):
        self.fb_psid = fb_psid
        self.creation_state = 0
        self.type_id = type_id
        self.giveaway = 0
        self.views = 0
        self.added = int(time.time())

    @property
    def display_name_utf8(self):
        return self.display_name.encode('utf-8') if self.display_name is not None else None

    @property
    def description_utf8(self):
        return self.description.encode('utf-8') if self.description is not None else None

    @property
    def messenger_url(self):
        return re.sub(r'^.*\/(.*)$', r'm.me/lmon8?ref=/\1', self.prebot_url) if self.prebot_url is not None else None

    @property
    def thumb_logo_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-256.\2', self.logo_url) if self.logo_url is not None else None

    @property
    def landscape_logo_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-400.\2', self.logo_url) if self.logo_url is not None else None

    @property
    def widescreen_logo_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-1280.\2', self.logo_url) if self.logo_url is not None else None

    @property
    def protrait_logo_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-480.\2', self.image_url) if self.logo_url is not None else None


    def __repr__(self):
        return "<Storefront id=%s, type_id=%s, fb_psid=%s, creation_state=%s, name=%s, display_name=%s, description=%s, logo_url=%s, video_url=%s, prebot_url=%s, giveaway=%s, added=%s>" % (self.id, self.type_id, self.fb_psid, self.creation_state, self.name, self.display_name_utf8, self.description_utf8, self.logo_url, self.video_url, self.prebot_url, self.giveaway, self.added)


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    storefront_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    customer_id = db.Column(db.Integer)
    enabled = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, customer_id, storefront_id, product_id):
        self.customer_id = customer_id
        self.storefront_id = storefront_id
        self.product_id = product_id
        self.enabled = 1
        self.added = int(time.time())

    def __repr__(self):
        return "<Subscription id=%s, customer_id=%s, storefront_id=%s, product_id=%s, enabled=%s, added=%s>" % (self.id, self.storefront_id, self.product_id, self.customer_id, self.enabled, self.added)


class ImageSizer(threading.Thread):
    def __init__(self, in_file, out_file=None, canvas_size=(256, 256)):
        if out_file is None:
            out_file = in_file

        threading.Thread.__init__(self)
        self.in_file = in_file
        self.out_file = out_file
        self.canvas_size = canvas_size

    def run(self):
        os.chdir(os.path.dirname(self.in_file))
        with Image.open(self.in_file.split("/")[-1]) as src_image:
            scale_factor = max((src_image.size[0] / float(self.canvas_size[0]), src_image.size[1] / float(self.canvas_size[1])))
            scale_size = ((
                int(round(src_image.size[0] / float(scale_factor))),
                int(round(src_image.size[1] / float(scale_factor)))
            ))

            padding = (
                int((self.canvas_size[0] - scale_size[0]) * 0.5),
                int((self.canvas_size[1] - scale_size[1]) * 0.5)
            )

            area = (
                -padding[0],
                -padding[1],
                self.canvas_size[0] - padding[0],
                self.canvas_size[1] - padding[1]
            )

            # logger.info("[::|::|::|::] CROP ->org=%s, scale_factor=%f, scale_size=%s, padding=%s, area=%s" % (src_image.size, scale_factor, scale_size, padding, area))

            out_image = src_image.resize(scale_size, Image.ANTIALIAS).crop(area)
            os.chdir(os.path.dirname(self.out_file))
            out_image.save("{out_file}".format(out_file=("-{sq}.".format(sq=self.canvas_size[0])).join(self.out_file.split("/")[-1].split("."))))


class VideoImageRenderer(threading.Thread):
    def __init__(self, src_url, out_img, at_sec=3):
        threading.Thread.__init__(self)
        self.src_url = src_url
        self.out_img = out_img
        self.at_time = time.strftime('%H:%M:%S', time.gmtime(at_sec))

    def run(self):
        p = subprocess.Popen(
            ('/usr/bin/ffmpeg -ss %s -i %s -frames:v 1 %s' % (self.at_time, self.src_url, self.out_img)).split(),
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
            'duration' : duration,
            'size'     : (int(size.split("x")[0]), int(size.split("x")[1])),
            'format'   : frmt
        }


#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#
#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


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



def send_tracker(fb_psid, category, action=None, label=None, value=None):
    logger.info("send_tracker(fb_psid=%s, category=%s, action=%s, label=%s, value=%s)" % (fb_psid, category, action, label, value))

    # "http://beta.modd.live/api/user_tracking.php?username={username}&chat_id={chat_id}".format(username=label, chat_id=action),
    # "http://beta.modd.live/api/bot_tracker.php?src=facebook&category={category}&action={action}&label={label}&value={value}&cid={cid}".format(category=category, action=category, label=action, value, cid=hashlib.md5(label.encode()).hexdigest()),
    # "http://beta.modd.live/api/bot_tracker.php?src=facebook&category=user-message&action=user-message&label={label}&value={value}&cid={cid}".format(label=action, value, cid=hashlib.md5(label.encode()).hexdigest())

    action = action or category
    label = label or fb_psid
    value = value or "0"

    t1 = threading.Thread(
        target=async_tracker,
        name="ga-tracker",
        kwargs={
            'payload': {
                'v'   : 1,
                't'   : "event",
                'tid' : Const.GA_TRACKING_ID,
                'cid' : hashlib.md5(fb_psid.encode()).hexdigest(),
                'ec'  : category,
                'ea'  : action,
                'el'  : label,
                'ev'  : value
            }
        }
    )
    t1.start()

    return True


def async_tracker(payload):
    # logger.info("async_tracker(payload=%s" % (payload,))

    response = requests.post(Const.GA_TRACKING_URL, data=payload, headers={ 'User-Agent' : "Lemonade-Tracker-v1" })
    if response.status_code != 200:
        logger.info("TRACKER ERROR:%s" % (response.text))


def is_vowel(char):
    return char == "a" or char == "e" or char == "i" or char == "o" or char == "u"

def slack_outbound(channel_name, message_text, image_url=None, username=None, webhook=None):
    logger.info("slack_outbound(channel_name=%s, message_text=%s, image_url=%s, username=%s, webhook=%s" % (channel_name, message_text, image_url, username, webhook))

    payload = {
        'channel'    : "#{channel_name}".format(channel_name=channel_name),
        'username'   : username or Const.SLACK_ORTHODOX_HANDLE,
        'icon_url'   : Const.SLACK_ORTHODOX_AVATAR,
        'text'       : message_text
    }

    if image_url is not None:
        payload['attachments'] = [{ 'image_url' : image_url }]

    return  requests.post(webhook or Const.SLACK_ORTHODOX_WEBHOOK, data={ 'payload' : json.dumps(payload) })



def sync_user(recipient_id, deeplink=None):
    logger.info("sync_user(recipient_id=%s, deeplink=%s)" % (recipient_id, deeplink))

    try:
        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
            if customer is None:
                customer = Customer(fb_psid=recipient_id, referrer=deeplink)
                db.session.add(customer)
            db.session.commit()

            #-- check db for existing user
            cur.execute('SELECT `id`, `referrer` FROM `users` WHERE `fb_psid` = %s LIMIT 1;', (recipient_id,))
            row = cur.fetchone()

            if row is None:
                send_tracker(fb_psid=recipient_id, category="sign-up")

                cur.execute('INSERT INTO `users` (`id`, `fb_psid`, `referrer`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());', (recipient_id, deeplink or "/"))
                conn.commit()
                cur.execute('SELECT @@IDENTITY AS `id` FROM `users`;')
                customer.id = cur.fetchone()['id']

            else:
                customer.id = row['id']
            db.session.commit()

            if deeplink is not None:
                cur.execute('UPDATE `users` SET `referrer` = %s WHERE `id` = %s AND `referrer` != %s LIMIT 1;', (deeplink or "/", customer.id, deeplink or "/"))
                conn.commit()


            #-- check fb graph data
            fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
            if fb_user is None and fb_graph_user(recipient_id) is not None:
                fb_user = FBUser(recipient_id, fb_graph_user(recipient_id))
                db.session.add(fb_user)
                db.session.commit()

            if fb_user is not None:
                cur.execute('SELECT `id` FROM `fb_users` WHERE `fb_psid` = %s LIMIT 1;', (recipient_id,))
                row = cur.fetchone()

                if row is None:
                    cur.execute('INSERT INTO `fb_users` (`id`, `user_id`, `fb_psid`, `first_name`, `last_name`, `profile_pic_url`, `locale`, `timezone`, `gender`, `payments_enabled`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, recipient_id or "", fb_user.first_name.decode('utf-8') or "", fb_user.last_name.decode('utf-8') or "", fb_user.profile_pic_url or "", fb_user.locale or "", fb_user.timezone or 666, fb_user.gender or "", int(fb_user.payments_enabled)))
                    conn.commit()
                    cur.execute('SELECT @@IDENTITY AS `id` FROM `fb_users`;')
                    fb_user.id = cur.fetchone()['id']

                else:
                    fb_user.id = row['id']
                db.session.commit()

    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return customer


def add_subscription(recipient_id, storefront_id, product_id=0, deeplink=None):
    logger.info("add_subscription(recipient_id=%s, storefront_id=%s, product_id=%s, deeplink=%s)" % (recipient_id, storefront_id, product_id, deeplink))

    is_new = False
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront = Storefront.query.filter(Storefront.id == storefront_id).first()
    product = Product.query.filter(Product.id == product_id).first()

    if customer is not None and storefront is not None and product is not None:
        subscription = Subscription.query.filter(Subscription.customer_id == customer.id).filter(Subscription.product_id == product.id).first()
        if subscription is None:
            subscription = Subscription(customer.id, storefront.id, product.id)
            db.session.add(subscription)
        db.session.commit()

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `id` FROM `subscriptions` WHERE `user_id` = %s AND `storefront_id` = %s AND `product_id` = %s LIMIT 1;', (customer.id, storefront.id, product.id))
                row = cur.fetchone()
                is_new = (row is None)

                if row is None:
                    # send_tracker(fb_psid=recipient_id, category="user-subscribe", label=storefront.display_name_utf8)

                    cur.execute('INSERT INTO `subscriptions` (`id`, `user_id`, `storefront_id`, `product_id`, `deeplink`, `added`) VALUES (NULL, %s, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, storefront.id, product.id, deeplink or "/"))
                    conn.commit()
                    cur.execute('SELECT @@IDENTITY AS `id` FROM `subscriptions`;')
                    subscription.id = cur.fetchone()['id']

                else:
                    subscription.id = row['id']
                db.session.commit()

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

    return is_new



def increment_shop_views(recipient_id, product_id, storefront_id=None):
    logger.info("increment_shop_views(recipient_id=%s, product_id=%s, storefront_id=%s)" % (recipient_id, product_id, storefront_id))

    product = Product.query.filter(Product.id == product_id).filter(Product.creation_state == 7).first()
    storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
    if product is not None and storefront is not None:
        product.views += 1
        storefront.views += 1
        db.session.commit()

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('UPDATE `products` SET `views` = `views` + 1 WHERE `id` = %s LIMIT 1;', (product.id,))
                cur.execute('UPDATE `storefronts` SET `views` = `views` + 1 WHERE `id` = %s LIMIT 1;', (storefront.id,))
                conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


def add_points(recipient_id, amount=0):
    logger.info("add_points(recipient_id=%s, amount=%s)" % (recipient_id, amount))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    if customer is not None:
        customer.points += Const.POINT_AMOUNT_VIEW_PRODUCT
        db.session.commit()

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('UPDATE `users` SET `points` = %s WHERE `id` = %s LIMIT 1;', (customer.points, customer.id))
                conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()



def add_cc_payment(recipient_id):
    logger.info("add_cc_payment(recipient_id=%s)" % (recipient_id,))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

    payment = Payment.query.filter(Payment.fb_psid == recipient_id).filter(Payment.source == Const.PAYMENT_SOURCE_CREDIT_CARD).first()
    if payment is None:
        payment = Payment(fb_psid=recipient_id, source=Const.PAYMENT_SOURCE_CREDIT_CARD)
        if customer.email is not None:
            payment.creation_state = 1

        db.session.add(payment)
        db.session.commit()

    logger.info("[:::|:::] CC PAYMENT:\n%s" % (payment,))
    if payment.creation_state == 0:
        send_text(recipient_id, "Enter your email address", cancel_payment_quick_reply())

    if payment.creation_state == 1:
        send_text(recipient_id, "Enter the card holder's name", cancel_payment_quick_reply())

    elif payment.creation_state == 2:
        send_text(recipient_id, "Enter the card's account number", cancel_payment_quick_reply())

    elif payment.creation_state == 3:
        send_text(recipient_id, "Enter the card's expiration date (example MM/YY)", cancel_payment_quick_reply())

    elif payment.creation_state == 4:
        send_text(recipient_id, "Enter the CVC or CVV2 code on the card's back", cancel_payment_quick_reply())

    elif payment.creation_state == 5:
        send_text(
            recipient_id = recipient_id,
            message_text= "Are these details correct?\n\nEmail: {email}\n\nName: {full_name}\n\nCard #: {acct_number}\n\nExpiration: {expiration:%m/%Y}\n\nCVC / CVV2: {cvc}".format(email=payment.email, full_name=payment.full_name, acct_number=(re.sub(r'\d', "*", payment.acct_number)[:-4] + payment.acct_number[-4:]), expiration=payment.expiration, cvc=payment.cvc),
            quick_replies = [
                build_quick_reply(Const.KWIK_BTN_TEXT, "Yes", Const.PB_PAYLOAD_PAYMENT_YES),
                build_quick_reply(Const.KWIK_BTN_TEXT, "No", Const.PB_PAYLOAD_PAYMENT_NO),
                build_quick_reply(Const.KWIK_BTN_TEXT, "Cancel", Const.PB_PAYLOAD_PAYMENT_CANCEL)
            ])

    elif payment.creation_state == 6:
        try:
            stripe_customer = stripe.Customer.create(
                description = "Customer for {fb_psid}".format(fb_psid=recipient_id),
                email = payment.email,
                source = {
                    'object'    : "card",
                    'name'      : payment.full_name,
                    'number'    : payment.acct_number,
                    'exp_month' : payment.expiration.strftime('%m'),
                    'exp_year'  : payment.expiration.strftime('%Y'),
                    'cvc'       : payment.cvc
                }
            )
            logger.info("[:::|:::] STRIPE CUSTOMER RESPONSE [:::|:::]\n%s" % (stripe_customer))

        except stripe.CardError, e:
            send_text(recipient_id, "Payment details are incorrect.\n{message}".format(message=e.message))
            try:
                Payment.query.filter(Payment.fb_psid == recipient_id).delete()
                db.session.commit()
            except:
                db.session.rollback()
            db.session.commit()
            return False

        else:
            customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
            customer.stripe_id = stripe_customer.id
            customer.card_id = stripe_customer['sources']['data'][0]['id']
            try:
                Payment.query.filter(Payment.fb_psid == recipient_id).delete()
                db.session.commit()
            except:
                db.session.rollback()

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('UPDATE `users` SET `email` = %s, `stripe_id` = %s, `card_id` = %s WHERE `id` = %s LIMIT 1;', (customer.email, customer.stripe_id, customer.card_id, customer.id))
                    conn.commit()

            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

            return True
    return False


def view_product(recipient_id, product):
    logger.info("view_product(recipient_id=%s, product=%s)" % (recipient_id, product))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    if product is not None:
        customer.product_id = product.id
        db.session.commit()

        storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
        send_tracker(fb_psid=recipient_id, category="view-shop", label=storefront.display_name_utf8)
        increment_shop_views(recipient_id, product.id)

        add_points(recipient_id, Const.POINT_AMOUNT_VIEW_PRODUCT)

        if product.video_url is not None and product.video_url != "":
            send_video(recipient_id, product.video_url, product.attachment_id)

        else:
            if storefront.logo_url is not None:
                send_image(recipient_id, storefront.logo_url)



        purchase = Purchase.query.filter(Purchase.customer_id == customer.id).filter(Purchase.product_id == product.id).first()
        if purchase is not None:
            customer.purchase_id = purchase.id
            db.session.commit()
            send_customer_carousel(recipient_id, product.id)

        else:
            if add_subscription(recipient_id, storefront.id, product.id, "/{deeplink}".format(deeplink=product.name)):
                send_tracker(fb_psid=recipient_id, category="subscribe", label=storefront.display_name_utf8)
                send_text(
                    recipient_id=recipient_id,
                    message_text="Get a{a_an} {product_name} for ${price:.2f}\n{product_rating} star{plural} | {points} points".format(a_an="n" if is_vowel(product.display_name_utf8[0]) else "", product_name=product.display_name_utf8, price=product.price, product_rating=int(round(product.avg_rating)), plural="" if int(round(product.avg_rating)) == 1 else "s", points=locale.format("%d", customer.points, grouping=True))
                )

                send_image(
                    recipient_id=storefront.fb_psid,
                    url=Const.IMAGE_URL_NEW_SUBSCRIBER,
                    quick_replies=new_sub_quick_replies(recipient_id)
                )
                send_text(storefront.fb_psid, "{fb_psid} just subscribed to your shop!".format(fb_psid=recipient_id[-4:],))

            else:
                send_text(
                    recipient_id=recipient_id,
                    message_text="Get a{a_an} {product_name} for ${price:.2f}\n{product_rating} star{plural} | {points} points".format(a_an="n" if is_vowel(product.display_name_utf8[0]) else "", product_name=product.display_name_utf8, price=product.price, product_rating=int(round(product.avg_rating)), plural="" if int(round(product.avg_rating)) == 1 else "s", points=locale.format("%d", customer.points, grouping=True))
                )

            send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_CHECKOUT)


def purchase_product(recipient_id, source):
    logger.info("purchase_product(recipient_id=%s, source=%s)" % (recipient_id, source))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    if customer is not None:
        product = Product.query.filter(Product.id == customer.product_id).first()
        if product is not None:
            storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
            if storefront is not None:
                if source == Const.PAYMENT_SOURCE_BITCOIN:
                    purchase = Purchase(customer.id, storefront.id, product.id, 2)
                    purchase.claim_state = 1

                    try:
                        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('UPDATE `users` SET `bitcoin_addr` = %s WHERE `id` = %s AND `bitcoin_addr` != %s LIMIT 1;', (customer.bitcoin_addr, customer.id, customer.bitcoin_addr))
                            cur.execute('INSERT INTO `purchases` (`id`, `user_id`, `product_id`, `type`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, product.id, 2))
                            conn.commit()

                            cur.execute('SELECT @@IDENTITY AS `id` FROM `purchases`;')
                            row = cur.fetchone()
                            purchase.id = row['id']
                            customer.purchase_id = row['id']

                    except mysql.Error as e:
                        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                    finally:
                        if conn:
                            conn.close()

                    db.session.add(purchase)
                    db.session.commit()
                    send_tracker(fb_psid=recipient_id, category="purchase-complete-bitcoin")

                    send_text(recipient_id, "Notifying the shop owner for your invoice.", [build_quick_reply(Const.KWIK_BTN_TEXT, caption="OK", payload=Const.PB_PAYLOAD_CANCEL_ENTRY_SEQUENCE)])

                    send_image(storefront.fb_psid, Const.IMAGE_URL_PRODUCT_PURCHASED)
                    route_purchase_dm(recipient_id, purchase, Const.DM_ACTION_PURCHASE, "Purchase complete for {product_name} at {pacific_time}.\nTo complete this order send the customer w/ your bitcoin address {bitcoin_addr}.".format(product_name=product.display_name_utf8, pacific_time=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%I:%M%P %Z').lstrip("0"), bitcoin_addr=customer.bitcoin_addr))
                    return True

                elif source == Const.PAYMENT_SOURCE_CREDIT_CARD:
                    stripe_charge = stripe.Charge.create(
                        amount = int(product.price * 100),
                        currency = "usd",
                        customer = customer.stripe_id,
                        source = customer.card_id,
                        description = "Charge for {fb_psid} - {storefront_name} / {product_name}".format(fb_psid=customer.fb_psid, storefront_name=storefront.display_name_utf8, product_name=product.display_name_utf8)
                    )

                    #logger.info(":::::::::] CHARGE RESPONSE [:::::::::::\n%s" % (stripe_charge))

                    if stripe_charge['status'] == "succeeded":
                        send_tracker(fb_psid=recipient_id, category="purchase-complete-stripe")

                        purchase = Purchase(customer.id, storefront.id, product.id, 1, stripe_charge.id)
                        db.session.add(purchase)
                        db.session.commit()

                        try:
                            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                            with conn:
                                cur = conn.cursor(mysql.cursors.DictCursor)
                                cur.execute('INSERT INTO `purchases` (`id`, `user_id`, `product_id`, `type`, `charge_id`, `transaction_id`, `refund_url`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, product.id, 1, purchase.charge_id, stripe_charge['balance_transaction'], stripe_charge['refunds']['url']))
                                conn.commit()
                                cur.execute('SELECT @@IDENTITY AS `id` FROM `purchases`;')
                                purchase.id = cur.fetchone()['id']
                                customer.purchase_id = purchase.id
                                db.session.commit()

                        except mysql.Error, e:
                            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                        finally:
                            if conn:
                                conn.close()

                        send_image(storefront.fb_psid, Const.IMAGE_URL_PRODUCT_PURCHASED)
                        route_purchase_dm(recipient_id, purchase, Const.DM_ACTION_PURCHASE, "Purchase complete for {product_name} at {pacific_time}.\nTo complete this order send the customer ({customer_email}) a the item now.".format(product_name=product.display_name_utf8, pacific_time=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%I:%M%P %Z').lstrip("0"), customer_email=customer.email))
                        return True

                    else:
                        send_text(recipient_id, "Error making payment:\n{reason}".format(reason=stripe_charge['outcome']['reason']))
                        return False

                elif source == Const.PAYMENT_SOURCE_PAYPAL:
                    purchase = Purchase(customer.id, storefront.id, product.id, 3)
                    purchase.claim_state = 1

                    try:
                        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('UPDATE `users` SET `paypal_email` = %s WHERE `id` = %s AND `paypal_email` != %s LIMIT 1;', (customer.paypal_email, customer.id, customer.paypal_email))
                            cur.execute('INSERT INTO `purchases` (`id`, `user_id`, `product_id`, `type`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, product.id, 3))
                            conn.commit()

                            cur.execute('SELECT @@IDENTITY AS `id` FROM `purchases`;')
                            row = cur.fetchone()
                            purchase.id = row['id']
                            customer.purchase_id = row['id']

                    except mysql.Error as e:
                        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                    finally:
                        if conn:
                            conn.close()

                    db.session.add(purchase)
                    db.session.commit()

                    send_tracker(fb_psid=recipient_id, category="purchase-complete-paypal")

                    storefront_owner = Customer.query.filter(Customer.fb_psid == storefront.fb_psid).first()
                    if storefront_owner is not None:
                        send_image(storefront.fb_psid, Const.IMAGE_URL_PRODUCT_PURCHASED)
                        product = Product.query.filter(Product.id == purchase.product_id).first()
                        send_message(json.dumps(build_standard_card(
                            recipient_id=recipient_id,
                            title=product.display_name_utf8,
                            subtitle="${price:.2f}".format(price=product.price),
                            image_url=product.image_url,
                            buttons=[
                                build_button(Const.CARD_BTN_URL_TALL, caption="${price:.2f} Confirm".format(price=product.price), url="http://lmon.us/paypal/{product_id}/{user_id}".format(product_id=product.id, user_id=customer.id))
                            ],
                            quick_replies=cancel_entry_quick_reply()
                        )))

                        route_purchase_dm(recipient_id, purchase, Const.DM_ACTION_PURCHASE, "Purchase made for {product_name} at {pacific_time}.".format(product_name=product.display_name_utf8, pacific_time=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%I:%M%P %Z').lstrip("0")))

                        return True
    return False

def route_purchase_dm(recipient_id, purchase, dm_action=Const.DM_ACTION_PURCHASE, message_text=None):
    logger.info("route_purchase_dm(recipient_id=%s, purchase=%s, dm_action=%s, message_text=%s)" % (recipient_id, purchase, dm_action, message_text))

    if purchase is not None:
        customer = Customer.query.filter(Customer.id == purchase.customer_id).first()
        storefront = Storefront.query.filter(Storefront.id == purchase.storefront_id).first()
        product = Product.query.filter(Product.id == purchase.product_id).first()

        if recipient_id == customer.fb_psid:
            customer.purchase_id = purchase.id
        db.session.commit()

        if storefront is not None and product is not None:
            if dm_action == Const.DM_ACTION_PURCHASE:
                if (storefront.id >= 505 and storefront.id <= 509) or re.search(r'^90\d{13}0$', storefront.fb_psid) is not None:
                    slack_outbound(
                        channel_name="lemonade-shops",
                        message_text=message_text,
                        image_url=product.image_url,
                        username=storefront.display_name_utf8,
                        webhook=Const.SLACK_SHOPS_WEBHOOK
                    )

                else:
                    send_text(
                        recipient_id=storefront.fb_psid,
                        message_text=message_text,
                        quick_replies=dm_quick_replies(storefront.fb_psid, purchase.id, Const.DM_ACTION_PURCHASE)
                    )

                # fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
                # slack_outbound(
                #     channel_name="lemonade-purchases",
                #     message_text="*{customer}* just purchased {product_name} from _{storefront_name}_.".format(customer=recipient_id if fb_user is None else fb_user.full_name_utf8, product_name=product.display_name_utf8, storefront_name=storefront.display_name_utf8),
                #     webhook=Const.SLACK_PURCHASES_WEBHOOK
                # )

            elif dm_action == Const.DM_ACTION_SEND:
                if recipient_id == customer.fb_psid and storefront is not None:
                    if (storefront.id >= 505 and storefront.id <= 509) or re.search(r'^90\d{13}0$', storefront.fb_psid) is not None:
                        slack_outbound(
                            channel_name = "lemonade-shops",
                            message_text = "Customer for purchase *#{purchase_id}* says:\n_{message_text}_".format(purchase_id=purchase.id, message_text=message_text),
                            username = storefront.display_name_utf8,
                            webhook = Const.SLACK_SHOPS_WEBHOOK
                        )

                    else:
                        send_text(
                            recipient_id = storefront.fb_psid,
                            message_text = "Customer says:\n{message_text}".format(message_text=message_text),
                            quick_replies = dm_quick_replies(storefront.fb_psid, purchase.id, dm_action)
                        )

                else:
                    send_text(
                        recipient_id = customer.fb_psid,
                        message_text = "Seller says:\n{message_text}".format(message_text=message_text),
                        quick_replies = dm_quick_replies(customer.fb_psid, purchase.id, dm_action)

                    )

                send_text(
                    recipient_id=recipient_id,
                    message_text="Message sent",
                    quick_replies=return_home_quick_reply())

            elif dm_action == Const.DM_ACTION_CLOSE:
                purchase.claim_state = 3
                db.session.commit()

                if recipient_id == customer.fb_psid:
                    if (storefront.id >= 505 and storefront.id <= 509) or re.search(r'^90\d{13}0$', storefront.fb_psid) is not None:
                        slack_outbound(
                            channel_name = "lemonade-shops",
                            message_text = "Customer for purchase *#{purchase_id}* closed DM".format(purchase_id=purchase.id),
                            username = storefront.display_name_utf8,
                            webhook = Const.SLACK_SHOPS_WEBHOOK
                        )

                    else:
                        send_text(storefront.fb_psid, "Customer closed the DM...", main_menu_quick_replies(recipient_id))
                    send_text(customer.fb_psid, "Closing out DM with seller...", [build_quick_reply(Const.KWIK_BTN_TEXT, "OK", Const.PB_PAYLOAD_CANCEL_ENTRY_SEQUENCE)])

                else:
                    if (storefront.id >= 505 and storefront.id <= 509) or re.search(r'^90\d{13}0$', storefront.fb_psid) is not None:
                        slack_outbound(
                            channel_name = "lemonade-shops",
                            message_text = "Closing out DM for purchase *#{purchase_id}*".format(purchase_id=purchase.id),
                            username = storefront.display_name_utf8,
                            webhook = Const.SLACK_SHOPS_WEBHOOK
                        )

                    else:
                        send_text(storefront.fb_psid, "Closing out DM with customer...", main_menu_quick_replies(recipient_id))
                    send_text(customer.fb_psid, "Seller closed the DM...", [build_quick_reply(Const.KWIK_BTN_TEXT, "OK", Const.PB_PAYLOAD_CANCEL_ENTRY_SEQUENCE)])


def purchase_timeout(purchase):
    logger.info("purchase_timeout(purchase=%s)" % (purchase,))

    customer = Customer.query.filter(Customer.id == purchase.customer_id).first()
    # storefront = Storefront.query.filter(Storefront.id == purchase.storefront_id).first()
    # product = Product.query.filter(Product.id == purchase.product_id).first()

    send_text(
        recipient_id=customer.fb_psid,
        message_text="Have you completed the PayPal checkout yet?",
        quick_replies=[
            build_quick_reply(Const.KWIK_BTN_TEXT, "Yes", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_PURCHASE_YES, purchase_id=purchase.id)),
            build_quick_reply(Const.KWIK_BTN_TEXT, "No", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_PURCHASE_NO, purchase_id=purchase.id))
        ] + cancel_entry_quick_reply()
    )


def clear_entry_sequences(recipient_id):
    logger.info("clear_entry_sequences(recipient_id=%s)" % (recipient_id,))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).first()

    #-- pending payment
    try:
        Payment.query.filter(Payment.fb_psid == recipient_id).delete()
        db.session.commit()
    except:
        db.session.rollback()

    #-- pending dms
    storefront_query = db.session.query(Storefront.id).filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).subquery('storefront_query')
    for purchase in db.session.query(Purchase).filter((Purchase.id == customer.purchase_id) | (Purchase.storefront_id.in_(storefront_query))).filter(Purchase.claim_state == 1):
        purchase.claim_state = 0

    #-- pending payouts
    if customer.paypal_name == "_{PENDING}_":
        customer.paypal_name = None

    if customer.paypal_email == "_{PENDING}_":
        customer.paypal_email = None

    if customer.bitcoin_addr == "_{PENDING}_":
        customer.bitcoin_addr = None

    if customer.fb_name == "_{PENDING}_":
        customer.fb_name = None

    #-- pending product
    try:
        Product.query.filter(Product.fb_psid == recipient_id).filter(Product.creation_state < 7).delete()
        db.session.commit()
    except:
        db.session.rollback()

    #-- pending storefront
    try:
        Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state < 4).delete()
        db.session.commit()
    except:
        db.session.rollback()


    db.session.commit()
    return


def welcome_message(recipient_id, entry_type, deeplink="/"):
    logger.info("welcome_message(recipient_id=%s, entry_type=%s, deeplink=%s)" % (recipient_id, entry_type, deeplink))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

    if entry_type == Const.MARKETPLACE_GREETING:
        send_image(recipient_id, Const.IMAGE_URL_GREETING)
        send_text(recipient_id, Const.ORTHODOX_GREETING)
        send_admin_carousel(recipient_id)

    elif entry_type == Const.STOREFRONT_ADMIN:
        send_text(recipient_id, Const.ORTHODOX_GREETING)

    elif entry_type == Const.STOREFRONT_AUTO_GEN and deeplink.split("/")[-1].lower() in Const.RESERVED_AUTO_GEN_STOREFRONTS.lower():
        storefront, product = autogen_storefront(recipient_id, deeplink.split("/")[-1])

        send_image(recipient_id, Const.IMAGE_URL_GREETING)
        send_text(recipient_id, Const.ORTHODOX_GREETING)
        send_text(recipient_id, "Auto generated your shop {storefront_name}.".format(storefront_name=storefront.display_name_utf8))
        send_text(recipient_id, product.messenger_url)
        send_text(recipient_id, "Every 2 {product_name}s you sell you will earn 1 {product_name}.".format(product_name=product.display_name_utf8))
        send_admin_carousel(recipient_id)

    elif entry_type == Const.CUSTOMER_REFERRAL:
        if re.search(r'^\/?createshop$', deeplink) is not None:
            fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
            send_tracker(fb_psid=recipient_id, category="adref", action=deeplink)

        product = Product.query.filter(Product.name.ilike(deeplink.split("/")[-1].lower())).filter(Product.creation_state == 7).first()
        if product is not None:
            customer.product_id = product.id
            db.session.commit()

            storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
            if storefront is not None:
                add_points(recipient_id, Const.POINT_AMOUNT_VIEW_PRODUCT)

                if product.video_url is not None and product.video_url != "":
                    send_video(recipient_id, product.video_url, product.attachment_id)

                else:
                    if storefront.logo_url is not None:
                        send_image(recipient_id, storefront.logo_url)

                send_tracker(fb_psid=recipient_id, category="view-shop", label=storefront.display_name_utf8)
                if add_subscription(recipient_id, storefront.id, product.id, deeplink):
                    send_tracker(fb_psid=recipient_id, category="subscribe", label=storefront.display_name_utf8)

                    send_text(
                        recipient_id=recipient_id,
                        message_text="Get a{a_an} {product_name} for ${price:.2f}\n{product_rating} star{plural} | {points} points".format(a_an="n" if is_vowel(product.display_name_utf8[0]) else "", product_name=product.display_name_utf8, price=product.price, product_rating=int(round(product.avg_rating)), plural="" if int(round(product.avg_rating)) == 1 else "s", points=locale.format("%d", customer.points, grouping=True))
                    )

                    send_image(
                        recipient_id=storefront.fb_psid,
                        url=Const.IMAGE_URL_NEW_SUBSCRIBER,
                        quick_replies=new_sub_quick_replies(recipient_id)
                    )
                    fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
                    send_text(storefront.fb_psid, "{fb_psid} just subscribed to your shop!".format(fb_psid=recipient_id[-4:],))

                else:
                    send_text(
                        recipient_id=recipient_id,
                        message_text="Get a{a_an} {product_name} for ${price:.2f}\n{product_rating} star{plural} | {points} points".format(a_an="n" if is_vowel(product.display_name_utf8[0]) else "", product_name=product.display_name_utf8, price=product.price, product_rating=int(round(product.avg_rating)), plural="" if int(round(product.avg_rating)) == 1 else "s", points=locale.format("%d", customer.points, grouping=True))
                    )

                send_home_content(recipient_id)


        else:
            send_text(recipient_id, Const.ORTHODOX_GREETING)
            send_admin_carousel(recipient_id)

    else:
        send_admin_carousel(recipient_id)


def autogen_storefront(recipient_id, name_prefix):
    logger.info("autogen_storefront(recipient_id=%s, name_prefix=%s)" % (recipient_id, name_prefix))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    details = {
        'ak47mistyshop'   : {
            'description'   : "Selling the cheapest Misty.",
            'price'         : 4.25,
            'image_url'     : "http://i.imgur.com/TQOAnps.jpg",
            'video_url'     : None,
            'attachment_id' : None,
            'tag'           : "gamebotsc"
        },
        'ak47vulcanshop'  : {
            'description'   : "Selling the cheapest Vulcan.",
            'price'         : 9.25,
            'image_url'     : "http://i.imgur.com/CnYFbzD.png",
            'video_url'     : None,
            'attachment_id' : None,
            'tag'           : "gamebotsc"
        },
        'mac10neonshop'   : {
            'description'   : "Selling the cheapest Neon.",
            'price'         : 0.95,
            'image_url'     : "http://i.imgur.com/mLDaoyA.png",
            'video_url'     : None,
            'attachment_id' : None,
            'tag'           : "gamebotsc"
        },
        'steamcardshop'   : {
            'description'   : "Selling the cheapest Steam card.",
            'price'         : 18.00,
            'image_url'     : "http://i.imgur.com/iKexmpe.png",
            'video_url'     : None,
            'attachment_id' : None,
            'tag'           : "gamebotsc"
        },
        'privatesnapchat' : {
            'description'   : "Selling access to Death By Candys Snapchat",
            'price'         : 5.00,
            'image_url'     : "http://i.imgur.com/mFm9Nlk.png",
            'video_url'     : None,
            'attachment_id' : None,
            'tag'           : "gamebotsc"
        },
        'gamebotscrate'   : {
            'description'   : "Gamebots daily crate. Items up to 15.00.",
            'price'         : 5.00,
            'image_url'     : "http://i.imgur.com/J4pzcki.png",
            'video_url'     : None,
            'attachment_id' : None,
            'tag'           : "gamebotsc"
        },
        'bonus'           : {
            'description'   : "3 bonus flips inside Gamebots!",
            'price'         : 5.99,
            'image_url'     : "http://lmon.us/thumbs/1489878300_741.jpg",
            'video_url'     : None,
            'attachment_id' : None,
            'tag'           : "gamebots"
        },
        'neonrider'       : {
            'description'   : "Get a MAC-10 Neon Rider for $1.20",
            'price'         : 1.15,
            'image_url'     : "http://i.imgur.com/PiKJ7k7.jpg",
            'video_url'     : "http://lmon.us/videos/neon.mp4",
            'attachment_id' : "226330947842742",
            'tag'           : "gamebotsc"
        },
        'ak47redline'     : {
            'description'   : "Get an AK47 Redline for $4.25",
            'price'         : 3.50,
            'image_url'     : "http://i.imgur.com/pcgbhwv.jpg",
            'video_url'     : "http://lmon.us/videos/redline.mp4",
            'attachment_id' : "226331167842720",
            'tag'           : "gamebotsc"
        },
        'frontsidemisty'  : {
            'description'   : "Get a Frontside Misty for $4.50",
            'price'         : 3.50,
            'image_url'     : "http://i.imgur.com/LUrC7P1.jpg",
            'video_url'     : "http://lmon.us/videos/misty.mp4",
            'attachment_id' : "226331344509369",
            'tag'           : "gamebotsc"
        }
    }

    storefront_name = "{name_prefix}{index}".format(name_prefix=name_prefix, index=recipient_id[-4:])
    product_name = "{name_prefix}{index}".format(name_prefix=name_prefix, index=recipient_id[-4:])

    try:
        Storefront.query.filter(Storefront.fb_psid == recipient_id).delete()
        db.session.commit()
    except:
        db.session.rollback()

    try:
        Product.query.filter(Product.fb_psid == recipient_id).delete()
        db.session.commit()
    except:
        db.session.rollback()


    storefront = Storefront(recipient_id)
    storefront.name = storefront_name
    storefront.display_name = storefront_name
    storefront.description = details[name_prefix.lower()]['description']
    storefront.logo_url = details[name_prefix.lower()]['image_url']
    storefront.prebot_url = "http://prebot.me/{storefront_name}".format(storefront_name=storefront_name)
    storefront.creation_state = 4
    db.session.add(storefront)
    db.session.commit()

    try:
        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('INSERT INTO `storefronts` (`id`, `owner_id`, `name`, `display_name`, `description`, `logo_url`, `prebot_url`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, storefront.name, storefront.display_name_utf8, storefront.description_utf8, storefront.logo_url, storefront.prebot_url))
            conn.commit()
            cur.execute('SELECT @@IDENTITY AS `id` FROM `storefronts`;')
            storefront.id = cur.fetchone()['id']
            db.session.commit()

    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    product = Product(recipient_id, storefront.id)
    product.name = product_name
    product.display_name = product_name
    product.release_date = calendar.timegm((datetime.utcnow() + relativedelta(months=int(0 / 30))).replace(hour=0, minute=0, second=0, microsecond=0).utctimetuple())
    product.description = "For sale starting on {release_date}".format(release_date=datetime.utcfromtimestamp(product.release_date).strftime('%a, %b %-d'))
    product.type_id = Const.PRODUCT_TYPE_VIRTUAL
    product.image_url = details[name_prefix.lower()]['image_url']
    product.video_url = details[name_prefix.lower()]['video_url']
    product.attachment_id = details[name_prefix.lower()]['attachment_id']
    product.prebot_url = "http://prebot.me/{product_name}".format(product_name=product_name)
    product.price = details[name_prefix.lower()]['price']
    product.tags = details[name_prefix.lower()]['tag']
    product.creation_state = 7
    db.session.add(product)
    db.session.commit()

    try:
        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('SELECT * FROM `products` WHERE `name` = %s AND `enabled` = 1;', (product.name,))
            if cur.fetchone() is None:
                cur.execute('INSERT INTO `products` (`id`, `storefront_id`, `type`, `name`, `display_name`, `description`, `tags`, `image_url`, `video_url`, `attachment_id`, `price`, `prebot_url`, `physical_url`, `release_date`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s), UTC_TIMESTAMP());', (product.storefront_id, product.type_id, product.name, product.display_name_utf8, product.description, "" if product.tags is None else product.tags.encode('utf-8'), product.image_url, product.video_url or "", product.attachment_id or "", product.price, product.prebot_url, product.physical_url or "", product.release_date))
                conn.commit()
                cur.execute('SELECT @@IDENTITY AS `id` FROM `products`;')
                product.id = cur.fetchone()['id']
                db.session.commit()

    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return (storefront, product)


def flip_product(recipient_id, product):
    logger.info("flip_product(recipient_id=%s, product=%s)" % (recipient_id, product))

    send_image(recipient_id, Const.IMAGE_URL_FLIP_GREETING)
    time.sleep(3)

    if random.uniform(0, 100) < 20 or (recipient_id == "996171033817503" and random.uniform(0, 100) < 80):
        code = hashlib.md5(str(time.time()).encode()).hexdigest()[-4:].upper()
        # send_image(recipient_id, Const.IMAGE_URL_FLIP_WIN)
        send_text(recipient_id, "You Won!\n\nA CSGO item from Gamebots. Text \"Giveaway\" to m.me/gamebotsc & follow instructions.")

        fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
        slack_outbound(
            channel_name=Const.SLACK_ORTHODOX_CHANNEL,
            username=Const.SLACK_ORTHODOX_HANDLE,
            webhook=Const.SLACK_ORTHODOX_WEBHOOK,
            message_text="*{fb_name}* ({fb_psid}) just won a _{product_name}_ by flipping.".format(fb_name=recipient_id if fb_user is None else fb_user.full_name_utf8, fb_psid=recipient_id, product_name=product.display_name_utf8),
            image_url=product.image_url
        )

    else:
        send_text(recipient_id, "YOU LOST!\n\nTap Flip Shop to try again.")


def write_message_log(recipient_id, message_id, message_txt):
    logger.info("write_message_log(recipient_id=%s, message_id=%s, message_txt=%s)" % (recipient_id, message_id, json.dumps(message_txt)))

    try:
        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('INSERT INTO `chat_logs` (`id`, `fbps_id`, `message_id`, `body`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (recipient_id, message_id, json.dumps(message_txt)))
            conn.commit()

    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


def main_menu_quick_replies(fb_psid):
    logger.info("main_menu_quick_replies(fb_psid=%s)" % (fb_psid))

    product = Product.query.filter(Product.fb_psid == fb_psid).first()
    storefront = Storefront.query.filter(Storefront.fb_psid == fb_psid).first()

    quick_replies = [
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Menu", payload=Const.PB_PAYLOAD_MAIN_MENU),
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Flip Shop", payload=Const.PB_PAYLOAD_RANDOM_STOREFRONT),
    ]

    if product is not None:
        quick_replies.append(build_quick_reply(Const.KWIK_BTN_TEXT, caption="Replace Item", payload=Const.PB_PAYLOAD_DELETE_PRODUCT))

    if storefront is not None:
        quick_replies.append(build_quick_reply(Const.KWIK_BTN_TEXT, caption="Replace Shop", payload=Const.PB_PAYLOAD_DELETE_STOREFRONT))

    quick_replies.append(build_quick_reply(Const.KWIK_BTN_TEXT, caption="Share Shop", payload=Const.PB_PAYLOAD_SHARE_PRODUCT if product is not None else Const.PB_PAYLOAD_SHARE_APP))

    if product is not None:
        quick_replies.append(build_quick_reply(Const.KWIK_BTN_TEXT, caption=product.messenger_url, payload=Const.PB_PAYLOAD_PREBOT_URL))

    return quick_replies


def new_sub_quick_replies(fb_psid):
    logger.info("new_sub_quick_replies(fb_psid=%s)" % (fb_psid,))

    return [
               build_quick_reply(Const.KWIK_BTN_TEXT, caption="Say Thanks", payload="{payload}-{fb_psid}".format(payload=Const.PB_PAYLOAD_SAY_THANKS, fb_psid=fb_psid))
           ] + cancel_entry_quick_reply()


def dm_quick_replies(fb_psid, purchase_id, dm_action=Const.DM_ACTION_PURCHASE):
    logger.info("dm_quick_replies(fb_psid=%s, purchase_id=%s, dm_action=%s)" % (fb_psid, purchase_id, dm_action))

    purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
    customer = Customer.query.filter(Customer.id == purchase.customer_id).first()

    quick_replies = []
    if customer.fb_psid == fb_psid:
        pass
        # quick_replies.append(
        #     build_quick_reply(Const.KWIK_BTN_TEXT, caption="Request PayPal.Me", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_DM_REQUEST_INVOICE, purchase_id=purchase.id))
        # )

    else:
        pass
        # quick_replies.append(
        #     build_quick_reply(Const.KWIK_BTN_TEXT, caption="Send PayPal.Me URL", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_DM_REQUEST_PAYMENT, purchase_id=purchase.id))
        # )

    quick_replies.extend([
        # build_quick_reply(Const.KWIK_BTN_TEXT, caption="Cancel Order", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_DM_CANCEL_PURCHASE, purchase_id=purchase.id)),
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Send FB Name", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_DM_SEND_FB_NAME, purchase_id=purchase.id)),
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Send URL", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_DM_SEND_URL, purchase_id=purchase.id)),
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Close DM", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_DM_CLOSE, purchase_id=purchase.id))
    ])

    return quick_replies


def activate_premium_quick_replies(storefront):
    logger.info("activate_premium_quick_replies(storefront=%s)" % (storefront,))

    return [
               build_quick_reply(Const.KWIK_BTN_TEXT, caption="${price:.2f}".format(price=Const.PREMIUM_SHOP_PRICE), payload=Const.PB_PAYLOAD_ACTIVATE_PRO_STOREFRONT)
           ] + cancel_entry_quick_reply()


def cancel_entry_quick_reply():
    logger.info("cancel_entry_quick_reply()")

    return [
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Cancel", payload=Const.PB_PAYLOAD_CANCEL_ENTRY_SEQUENCE)
    ]


def return_home_quick_reply(caption="OK"):
    logger.info("return_home_quick_reply(caption=%s)" % (caption,))

    return [
        build_quick_reply(Const.KWIK_BTN_TEXT, caption=caption, payload=Const.PB_PAYLOAD_HOME_CONTENT)
    ]


def cancel_payment_quick_reply():
    logger.info("cancel_payment_quick_reply()")

    return [
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Cancel Purchase", payload=Const.PB_PAYLOAD_PAYMENT_CANCEL)
    ]



def build_button(btn_type, caption="", url="", payload=""):
    # logger.info("build_button(btn_type=%s, caption=%s, url=%s, payload=%s)" % (btn_type, caption, url, payload))

    button = None
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

    elif btn_type == Const.CARD_BTN_URL_COMPACT:
        button = {
            'type'                 : Const.CARD_BTN_URL,
            'url'                  : url,
            'title'                : caption,
            #'messenger_extensions' : True,
            'webview_height_ratio' : "compact"
        }

    elif btn_type == Const.CARD_BTN_URL_TALL:
        button = {
            'type'                 : Const.CARD_BTN_URL,
            'url'                  : url,
            'title'                : caption,
            #'messenger_extensions' : True,
            'webview_height_ratio' : "tall"
        }

    elif btn_type == Const.CARD_BTN_URL_FULL:
        button = {
            'type'                 : Const.CARD_BTN_URL,
            'url'                  : url,
            'title'                : caption,
            #'messenger_extensions' : True,
            'webview_height_ratio' : "full"
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


def build_quick_reply(btn_type, caption, payload, image_url=None):
    # logger.info("build_quick_reply(btn_type=%s, caption=%s, payload=%s)" % (btn_type, caption, payload))

    button = None
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


def build_featured_storefront_elements(recipient_id, amt=3):
    logger.info("build_featured_storefront_elements(recipient_id=%s, amt=%s)" % (recipient_id, amt))

    elements = []

    flags = [
        ':cn:',
        ':de:',
        ':es:',
        ':fr:',
        ':gb:',
        ':it:',
        ':kr:',
        ':ru:',
        ':us:'
    ]

    try:
        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `products` WHERE (`type` = 5 OR `type` = 6) AND `enabled` = 1 ORDER BY RAND() LIMIT %s;', (min(max(amt, 0), 10),))

            for row in cur.fetchall():
                product = Product.query.filter(Product.id == row['id']).first()
                if product is not None:
                    storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
                    if storefront is not None:
                        elements.append(build_card_element(
                            # title = "{storefront_name} {flag}".format(storefront_name=storefront.display_name_utf8, flag=emoji.emojize(random.choice(flags), use_aliases=True)),
                            title = storefront.display_name_utf8,
                            subtitle = product.display_name_utf8,
                            image_url = product.image_url,
                            item_url = product.messenger_url,
                            buttons = [
                                build_button(Const.CARD_BTN_POSTBACK, caption="View Shop", payload="{payload}-{product_id}".format(payload=Const.PB_PAYLOAD_VIEW_PRODUCT, product_id=product.id)),
                                build_button(Const.CARD_BTN_INVITE)
                            ]
                        ))


    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return elements


def build_autogen_storefront_elements(recipient_id):
    logger.info("build_autogen_storefront_elements(recipient_id=%s)" % (recipient_id,))
    elements = []

    details = [
        {
            'key'       : "NeonRider",
            'title'     : "MAC-10 Neon Rider",
            'subtitle'  : "Get a Mac10 Neon Rider for $1.20",
            'image_url' : "http://i.imgur.com/PiKJ7k7.jpg"
        }, {
            'key'       : "AK47Redline",
            'title'     : "AK-47 Redline",
            'subtitle'  : "Get an AK47 Redline for $4.25",
            'image_url' : "http://i.imgur.com/pcgbhwv.jpg"
        }, {
            'key'       : "FrontsideMisty",
            'title'     : "Frontside Misty",
            'subtitle'  : "Get a Frontside Misty for $4.50",
            'image_url' : "http://i.imgur.com/LUrC7P1.jpg"
        }
    ]

    for detail in details:
        elements.append(build_card_element(
            title=detail['title'],
            subtitle=detail['subtitle'],
            image_url=detail['image_url'],
            buttons=[
                build_button(Const.CARD_BTN_POSTBACK, "Create", payload="{payload}-{key}".format(payload=Const.PB_PAYLOAD_AUTO_GEN_STOREFRONT, key=detail['key'])),
                build_button(Const.CARD_BTN_INVITE)
            ]
        ))

    return None if len(elements) == 0 else elements


def build_card_element(title, subtitle=None, image_url=None, item_url=None, buttons=None):
    # logger.info("build_card_element(title=%s, subtitle=%s, image_url=%s, item_url=%s, buttons=%s)" % (title, subtitle, image_url, item_url, buttons))

    element = {
        'title'     : title,
        'subtitle'  : subtitle or "",
        'image_url' : image_url,
        'item_url'  : item_url
    }

    if buttons is not None:
        element['buttons'] = buttons

    return element


def build_receipt_card(recipient_id, purchase_id):
    logger.info("build_receipt_card(recipient_id=%s, purchase_id=%s)" % (recipient_id, purchase_id))

    data = None
    purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
    if purchase is not None:
        customer = Customer.query.filter(Customer.id == purchase.customer_id).first()
        storefront = Storefront.query.filter(Storefront.id == purchase.storefront_id).first()
        product = Product.query.filter(Product.id == purchase.product_id).first()
        stripe_card = stripe.Customer.retrieve(customer.stripe_id).sources.retrieve(customer.card_id)

        if purchase.type == 1 and stripe_card is not None:
            payment_method = "{cc_brand} · {cc_suffix}".format(cc_brand=stripe_card['brand'], cc_suffix=stripe_card['last4'])

        elif purchase.type == 2:
            payment_method = "Bitcoin"

        elif purchase.type == 3:
            payment_method = "PayPal"


        data = {
            'recipient' : {
                'id' : recipient_id
            },
            'message' : {
                'attachment' : {
                    'type'    : "template",
                    'payload' : {
                        'template_type'  : "receipt",
                        'recipient_name' : customer.fb_psid,
                        'merchant_name'  : storefront.display_name_utf8,
                        'order_number'   : "{order_id}".format(order_id=purchase.id),
                        "currency"       : "USD",
                        'payment_method' : payment_method,
                        'order_url'      : "http://prebot.me/orders/{order_id}".format(order_id=purchase.id),
                        'timestamp'      : "{timestamp}".format(timestamp=purchase.added),
                        'elements'       : [{
                            'title'     : product.display_name_utf8,
                            'subtitle'  : product.description,
                            'quantity'  : 1,
                            'price'     : product.price,
                            'currency'  : "USD",
                            'image_url' : product.image_url
                        }],
                        'summary'        : {
                            'subtotal'      : product.price,
                            'shipping_cost' : 0.00,
                            'total_tax'     : 0.00,
                            'total_cost'    : product.price
                        }
                    }
                }
            }
        }

    return data


def build_list_card(recipient_id, body_elements, header_element=None, buttons=None, quick_replies=None):
    # logger.info("build_list_card(recipient_id=%s, body_elements=%s, header_element=%s, buttons=%s, quick_replies=%s)" % (recipient_id, body_elements, header_element, buttons, quick_replies))

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type'    : "template",
                'payload' : {
                    'template_type'     : "list",
                    'top_element_style' : "compact" if header_element is None else "large",
                    'elements'          : body_elements if header_element is None else [header_element] + body_elements
                }
            }
        }
    }

    if buttons is not None:
        data['message']['attachment']['payload']['buttons'] = buttons

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    return data


def build_standard_card(recipient_id, title, subtitle=None, image_url=None, item_url=None, buttons=None, quick_replies=None):
    # logger.info("build_standard_card(recipient_id=%s, title=%s, subtitle=%s, image_url=%s, item_url=%s, buttons=%s, quick_replies=%s)" % (recipient_id, title, subtitle, image_url, item_url, buttons, quick_replies))

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type'    : "template",
                'payload' : {
                    'template_type' : "generic",
                    'elements'      : [
                        build_card_element(
                            title = title,
                            subtitle = subtitle or "",
                            image_url = image_url,
                            item_url = item_url,
                            buttons = buttons
                        )
                    ]
                }
            }
        }
    }

    # if buttons is not None:
    #     data['message']['attachment']['payload']['elements'][0]['buttons'] = buttons

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    return data


def build_carousel(recipient_id, cards, quick_replies=None):
    # logger.info("build_carousel(recipient_id=%s, cards=%s, quick_replies=%s)" % (recipient_id, cards, quick_replies))

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type'    : "template",
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


def send_home_content(recipient_id):
    logger.info("send_home_content(recipient_id=%s)" % (recipient_id,))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    if customer.product_id is not None:
        product = Product.query.filter(Product.id == customer.product_id).first()

        if product is not None:
            increment_shop_views(recipient_id, product.id)
            purchase = Purchase.query.filter(Purchase.customer_id == customer.id).filter(Purchase.product_id == product.id).first()
            if purchase is not None:
                customer.purchase_id = purchase.id
                db.session.commit()
                send_customer_carousel(recipient_id, product.id)

            else:
                send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_CHECKOUT)
        else:
            send_admin_carousel(recipient_id)
    else:
        send_admin_carousel(recipient_id)


def send_admin_carousel(recipient_id):
    logger.info("send_admin_carousel(recipient_id=%s)" % (recipient_id))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).first()

    cards = []

    #-- look for created storefront
    if storefront is None:
        cards.append(
            build_card_element(
                title="Create Shop",
                subtitle="Tap Button Below",
                image_url=Const.IMAGE_URL_CREATE_STOREFRONT_CARD,
                buttons=[
                    build_button(Const.CARD_BTN_POSTBACK, caption="Create Shop", payload=Const.PB_PAYLOAD_CREATE_STOREFRONT)
                ]
            )
        )

        cards += build_autogen_storefront_elements(recipient_id)

    else:
        product = Product.query.filter(Product.storefront_id == storefront.id).filter(Product.creation_state == 7).first()
        if product is None:
            cards.append(
                build_card_element(
                    title="Add Item",
                    subtitle="Tap Button Below",
                    image_url=Const.IMAGE_URL_ADD_PRODUCT_CARD,
                    buttons=[
                        build_button(Const.CARD_BTN_POSTBACK, caption="Add Item", payload=Const.PB_PAYLOAD_ADD_PRODUCT)
                    ]
                )
            )

            cards += build_autogen_storefront_elements(recipient_id)

        else:
            purchases = Purchase.query.filter(Purchase.storefront_id == storefront.id).all()
            if len(purchases) > 0:
                if len(purchases) == 1:
                    subtitle = "1 Purchase"

                else:
                    subtitle = "{total} Purchases".format(total=len(purchases))

                cards.append(
                    build_card_element(
                        title="My Orders",
                        subtitle=subtitle,
                        image_url=Const.IMAGE_URL_PURCHASES_CARD,
                        buttons=[
                            build_button(Const.CARD_BTN_POSTBACK, caption="Message", payload=Const.PB_PAYLOAD_MESSAGE_CUSTOMERS)
                        ]
                    )
                )

            cards += build_autogen_storefront_elements(recipient_id)

    data = build_carousel(
        recipient_id=recipient_id,
        cards=cards,
        quick_replies=main_menu_quick_replies(recipient_id)
    )

    send_message(json.dumps(data))


def send_customer_carousel(recipient_id, product_id):
    logger.info("send_customer_carousel(recipient_id=%s, product_id=%s)" % (recipient_id, product_id))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

    product = Product.query.filter(Product.id == product_id).first()
    storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()

    elements = []
    if storefront is not None:
        increment_shop_views(recipient_id, product.id)

        purchase = Purchase.query.filter(Purchase.id == customer.purchase_id).first()
        if purchase is None:
            elements.append(
                build_card_element(
                    title = product.display_name_utf8,
                    subtitle = "{description} — ${price:.2f}".format(description=product.description, price=product.price),
                    image_url = product.image_url,
                    buttons = [
                        build_button(Const.CARD_BTN_POSTBACK, caption="Purchase", payload=Const.PB_PAYLOAD_CHECKOUT_PRODUCT)
                    ]
                )
            )

        else:
            elements.append(
                build_card_element(
                    title = "You purchased {product_name} on {purchase_date}".format(product_name=product.display_name_utf8, purchase_date=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%b %d @ %I:%M%P %Z').lstrip("0")),
                    subtitle = product.description,
                    image_url = product.image_url,
                    buttons = [
                        build_button(Const.CARD_BTN_POSTBACK, caption="Buy Another", payload=Const.PB_PAYLOAD_CHECKOUT_PRODUCT),
                        build_button(Const.CARD_BTN_POSTBACK, caption="Rate", payload=Const.PB_PAYLOAD_RATE_PRODUCT),
                        build_button(Const.CARD_BTN_POSTBACK, caption="Message Shop", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_DM_OPEN, purchase_id=purchase.id))
                    ]
                )
            )

    data = build_carousel(
        recipient_id = recipient_id,
        cards = elements,
        quick_replies = main_menu_quick_replies(recipient_id)
    )

    send_message(json.dumps(data))


def send_featured_carousel(recipient_id):
    logger.info("send_featured_carousel(recipient_id=%s)" % (recipient_id,))

    data = build_carousel(
        recipient_id=recipient_id,
        cards=build_featured_storefront_elements(recipient_id, 10),
        quick_replies=main_menu_quick_replies(recipient_id)
    )

    send_message(json.dumps(data))


def send_storefront_card(recipient_id, storefront_id, card_type=Const.CARD_TYPE_STOREFRONT):
    logger.info("send_storefront_card(recipient_id=%s, storefront_id=%s, card_type=%s)" % (recipient_id, storefront_id, card_type))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront = Storefront.query.filter(Storefront.id == storefront_id).first()
    product = Product.query.filter(Product.storefront_id == storefront_id).first()

    if storefront is not None:
        if card_type == Const.CARD_TYPE_STOREFRONT:
            data = build_standard_card(
                recipient_id = recipient_id,
                title = storefront.display_name_utf8,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.messenger_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="View Shop", url=storefront.messenger_url),
                    build_button(Const.CARD_BTN_INVITE)
                ]
            )

        elif card_type == Const.CARD_TYPE_STOREFRONT_PREVIEW:
            data = build_standard_card(
                recipient_id = recipient_id,
                title = storefront.display_name_utf8,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                quick_replies = [
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Submit", Const.PB_PAYLOAD_SUBMIT_STOREFRONT),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Re-Do", Const.PB_PAYLOAD_REDO_STOREFRONT),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Cancel", Const.PB_PAYLOAD_CANCEL_STOREFRONT)
                ]
            )

        elif card_type == Const.CARD_TYPE_STOREFRONT_ACTIVATE_PRO:
            # send_tracker(fb_psid=recipient_id, category="button-activate-pro")
            # send_tracker(fb_psid=recipient_id, category="button-paywall")

            product = Product.query.filter(Product.id == 1).first()
            if product is not None:
                data = build_list_card(
                    recipient_id = recipient_id,
                    body_elements = [
                        build_card_element(
                            title = "${price:.2f} per month".format(price=product.price),
                            subtitle = "via Paypal",
                            image_url = product.image_url,
                            buttons = [
                                build_button(Const.CARD_BTN_POSTBACK, caption="Buy", payload=Const.PB_PAYLOAD_CHECKOUT_PAYPAL)
                            ]
                        ),
                        build_card_element(
                            title = "${price:.2f} per month".format(price=product.price),
                            subtitle = "via Bitcoin",
                            image_url = product.image_url,
                            buttons = [
                                build_button(Const.CARD_BTN_POSTBACK, caption="Buy", payload=Const.PB_PAYLOAD_CHECKOUT_BITCOIN)
                            ]
                        ),
                        build_card_element(
                            title = "${price:.2f} per month".format(price=product.price),
                            subtitle = "via Stripe / CC",
                            image_url = product.image_url,
                            buttons = [
                                build_button(Const.CARD_BTN_POSTBACK, caption="Buy", payload=Const.PB_PAYLOAD_CHECKOUT_CREDIT_CARD)
                            ]
                        )
                    ],
                    header_element = build_card_element(
                        title = "Your shop is now restricted until you activate a payment plan",
                        image_url = product.image_url
                    ),
                    quick_replies = main_menu_quick_replies(recipient_id)
                )

        else:
            data = build_standard_card(
                recipient_id = recipient_id,
                title = storefront.display_name_utf8,
                subtitle = "View my shop now",
                image_url = storefront.logo_url,
                item_url = storefront.messenger_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="View Shop", url=storefront.messenger_url),
                    build_button(Const.CARD_BTN_INVITE)
                ]
            )

        send_message(json.dumps(data))


def send_product_card(recipient_id, product_id, card_type=Const.CARD_TYPE_PRODUCT):
    logger.info("send_product_card(recipient_id=%s, product_id=%s, card_type=%s)" % (recipient_id, product_id, card_type))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    product = Product.query.filter(Product.id == product_id).first()

    data = None
    if product is not None:
        storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()

        if card_type == Const.CARD_TYPE_PRODUCT:
            data = build_standard_card(
                recipient_id = recipient_id,
                title = product.display_name_utf8,
                subtitle = "View my shop now",
                image_url = product.image_url,
                item_url = product.messenger_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="View Shop", url=product.messenger_url),
                    build_button(Const.CARD_BTN_INVITE)
                ],
                quick_replies = main_menu_quick_replies(recipient_id)
            )

        elif card_type == Const.CARD_TYPE_PRODUCT_PREVIEW:
            data = build_standard_card(
                recipient_id = recipient_id,
                title = product.display_name_utf8,
                subtitle = "{description} — ${price:.2f}".format(description=product.description, price=product.price),
                image_url = product.image_url,
                item_url = product.video_url,
                quick_replies = [
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Submit", Const.PB_PAYLOAD_SUBMIT_PRODUCT),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Re-Do", Const.PB_PAYLOAD_REDO_PRODUCT),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Cancel", Const.PB_PAYLOAD_CANCEL_PRODUCT)
                ]
            )

        elif card_type == Const.CARD_TYPE_PRODUCT_SHARE:
            data = build_standard_card(
                recipient_id = recipient_id,
                title = product.display_name_utf8,
                subtitle = "View my shop now",
                image_url = product.image_url,
                item_url = product.messenger_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="View Shop", url=product.messenger_url),
                    build_button(Const.CARD_BTN_URL, caption="Flip to Win", url=re.sub(r'\/([A-Za-z0-9_\.\-]+)$', r'/flip/\1', product.messenger_url)),
                    build_button(Const.CARD_BTN_INVITE)
                ],
                quick_replies = main_menu_quick_replies(recipient_id)
            )

        elif card_type == Const.CARD_TYPE_PRODUCT_CHECKOUT:
            data = build_list_card(
                recipient_id = recipient_id,
                body_elements = [
                    build_card_element(
                        title = product.display_name_utf8,
                        subtitle = "${price:.2f}".format(price=product.price),
                        image_url = product.image_url,
                        item_url = product.messenger_url,
                        buttons = [
                            build_button(Const.CARD_BTN_POSTBACK, caption="Pay via PayPal", payload=Const.PB_PAYLOAD_CHECKOUT_PAYPAL)

                        ]
                    # ),
                    # build_card_element(
                    #     title = product.display_name_utf8,
                    #     subtitle = "${price:.2f}".format(price=product.price),
                    #     image_url = product.image_url,
                    #     item_url = product.messenger_url,
                    #     buttons = [
                    #         build_button(Const.CARD_BTN_POSTBACK, caption="Pay via Bitcoin", payload=Const.PB_PAYLOAD_CHECKOUT_BITCOIN)
                    #     ]
                    # ),
                    # build_card_element(
                    #     title = product.display_name_utf8,
                    #     subtitle = "${price:.2f}".format(price=product.price),
                    #     image_url = product.image_url,
                    #     item_url = product.messenger_url,
                    #     buttons = [
                    #         build_button(Const.CARD_BTN_POSTBACK, caption="Pay via Stripe", payload=Const.PB_PAYLOAD_CHECKOUT_CREDIT_CARD)
                    #     ]
                    )
                ],
                header_element = build_card_element(
                    title = storefront.display_name_utf8,
                    subtitle = storefront.description,
                    image_url = storefront.logo_url,
                    item_url = None
                ),
                quick_replies = main_menu_quick_replies(recipient_id)
            )

        elif card_type == Const.CARD_TYPE_PRODUCT_CHECKOUT_CC:
            stripe_card = stripe.Customer.retrieve(customer.stripe_id).sources.retrieve(customer.card_id)

            data = build_list_card(
                recipient_id = recipient_id,
                body_elements = [
                    build_card_element(
                        title = "Reserve Price:",
                        subtitle = "Total: ${price:.2f}".format(price=product.price)
                    ),
                    build_card_element(
                        title = "Payment Method:",
                        subtitle = "{cc_brand} · {cc_suffix}".format(cc_brand=stripe_card['brand'], cc_suffix=stripe_card['last4'])
                    ),
                    build_card_element(
                        title = "By tapping pay, you agree to Facebook's & Lemonade's terms & conditions.",
                        subtitle = "Terms & Conditions",
                        item_url = "http://prebot.me/terms"
                    )
                ],
                header_element = build_card_element(
                    title = product.display_name_utf8,
                    subtitle = "{product_description} - from {storefront_name}".format(product_description=product.description, storefront_name=storefront.display_name_utf8),
                    image_url = product.image_url,
                    item_url = None
                ),
                buttons = [
                    build_button(Const.CARD_BTN_POSTBACK, caption="Pay", payload=Const.PB_PAYLOAD_PURCHASE_PRODUCT)
                ],
                quick_replies = cancel_entry_quick_reply()
            )

        elif card_type == Const.CARD_TYPE_PRODUCT_INVOICE_PAYPAL:
            storefront_query = db.session.query(Storefront.fb_psid).filter(Storefront.id == product.storefront_id).subquery('storefront_query')
            storefront_owner = Customer.query.filter(Customer.fb_psid.in_(storefront_query)).first()

            if storefront_owner.paypal_email is not None:
                data = build_standard_card(
                    recipient_id=recipient_id,
                    title=product.display_name_utf8,
                    subtitle="${price:.2f}".format(price=product.price),
                    image_url=product.image_url,
                    buttons=[
                        #build_button(Const.CARD_BTN_URL_TALL, caption="${price:.2f} Confirm".format(price=product.price), url="https://paypal.me/{paypal_name}/{price:.2f}".format(paypal_name=storefront_owner.paypal_name, price=product.price))
                        build_button(Const.CARD_BTN_URL_TALL, caption="${price:.2f} Confirm".format(price=product.price), url="http://lmon.us/paypal/{product_id}/{user_id}".format(product_id=product.id, user_id=customer.id))
                    ],
                    quick_replies=cancel_entry_quick_reply()
                )

        elif card_type == Const.CARD_TYPE_PRODUCT_RECEIPT:
            data = build_receipt_card(recipient_id, customer.purchase_id)

        elif card_type == Const.CARD_TYPE_PRODUCT_PURCHASED:
            customer_query = db.session.query(Customer.purchase_id).filter(Customer.fb_psid == recipient_id).order_by(Purchase.added.desc()).subquery('customer_query')
            purchase = Purchase.query.filter(Purchase.id.in_(customer_query)).first()

            data = build_standard_card(
                recipient_id = recipient_id,
                title = "You purchased {product_name} on {purchase_date}".format(product_name=product.display_name_utf8, purchase_date=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%b %d @ %I:%M%P %Z').lstrip("0")),
                subtitle = product.description,
                image_url = product.image_url,
                buttons = [
                    build_button(Const.CARD_BTN_POSTBACK, caption="Buy Another", payload=Const.PB_PAYLOAD_CHECKOUT_PRODUCT),
                    build_button(Const.CARD_BTN_POSTBACK, caption="Rate", payload=Const.PB_PAYLOAD_RATE_PRODUCT),
                    build_button(Const.CARD_BTN_POSTBACK, caption="Message Owner", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_DM_OPEN, purchase_id=purchase.id))
                ],
                quick_replies = main_menu_quick_replies(recipient_id)
            )


        elif card_type == Const.CARD_TYPE_PRODUCT_RATE:
            rate_buttons = [
                build_button(Const.KWIK_BTN_TEXT, caption=str(Const.RATE_GLYPH * 1), payload=Const.PB_PAYLOAD_PRODUCT_RATE_1_STAR),
                build_button(Const.KWIK_BTN_TEXT, caption=(Const.RATE_GLYPH * 2), payload=Const.PB_PAYLOAD_PRODUCT_RATE_2_STAR),
                build_button(Const.KWIK_BTN_TEXT, caption=(Const.RATE_GLYPH * 3), payload=Const.PB_PAYLOAD_PRODUCT_RATE_3_STAR),
                build_button(Const.KWIK_BTN_TEXT, caption=(Const.RATE_GLYPH * 4), payload=Const.PB_PAYLOAD_PRODUCT_RATE_4_STAR),
                build_button(Const.KWIK_BTN_TEXT, caption=(Const.RATE_GLYPH * 5), payload=Const.PB_PAYLOAD_PRODUCT_RATE_5_STAR)
            ]

            stars = int(math.ceil(round(product.avg_rating, 3)))
            data = build_standard_card(
                recipient_id = recipient_id,
                title = "Rate {product_name}".format(product_name=product.display_name_utf8),
                subtitle = None if stars == 0 else "Average Rating: {stars}".format(stars=(Const.RATE_GLYPH * stars)),
                image_url = product.image_url,
                quick_replies = rate_buttons + cancel_entry_quick_reply()
            )


        else:
            data = build_standard_card(
                recipient_id = recipient_id,
                title = product.display_name_utf8,
                subtitle = "View my shop now",
                image_url = product.image_url,
                item_url = product.messenger_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="View Shop", url=product.messenger_url),
                    build_button(Const.CARD_BTN_INVITE)
                ],
                quick_replies = main_menu_quick_replies(recipient_id)
            )

        send_message(json.dumps(data))


def send_purchases_list_card(recipient_id, card_type=Const.CARD_TYPE_PRODUCT_PURCHASES):
    logger.info("send_purchases_list_card(recipient_id=%s, card_type=%s)" % (recipient_id, card_type))

    elements = []
    if card_type == Const.CARD_TYPE_PRODUCT_PURCHASES:
        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).first()

        for purchase in Purchase.query.filter(Purchase.storefront_id == storefront.id).order_by(Purchase.added.desc()):
            if len(elements) < 4:
                product = Product.query.filter(Product.id == purchase.product_id).first()
                customer = Customer.query.filter(Customer.id == purchase.customer_id).first()

                if purchase.type == 1:
                    subtitle = customer.email

                elif purchase.type == 2:
                    subtitle = customer.bitcoin_addr

                elif purchase.type == 3:
                    subtitle = customer.paypal_email

                elements.append(
                    build_card_element(
                        title="{product_name} - ${price:.2f}".format(product_name=product.display_name_utf8, price=product.price),
                        subtitle=subtitle,
                        image_url=product.image_url,
                        buttons=[
                            build_button(Const.CARD_BTN_POSTBACK, caption="Message", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_DM_OPEN, purchase_id=purchase.id))
                        ]
                    )
                )

    elif card_type == Const.CARD_TYPE_PRODUCTS_PURCHASED:
        customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
        for purchase in Purchase.query.filter(Purchase.customer_id == customer.id).order_by(Purchase.added.desc()):
            if len(elements) < 4:
                storefront = Storefront.query.filter(Storefront.id == purchase.storefront_id).first()
                product = Product.query.filter(Product.id == purchase.product_id).first()

                if storefront is not None and product is not None:
                    elements.append(
                        build_card_element(
                            title="{product_name} - ${price:.2f}".format(product_name=product.display_name_utf8, price=product.price),
                            subtitle=storefront.display_name_utf8,
                            image_url=product.image_url,
                            buttons=[
                                build_button(Const.CARD_BTN_POSTBACK, caption="Message", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_DM_OPEN, purchase_id=purchase.id))
                            ]
                        )
                    )

    else:
        pass

    header_element = None
    if len(elements) == 1:
        header_element = build_card_element(
            title="{storefront_name}".format(storefront_name=storefront.display_name_utf8),
            subtitle=storefront.description_utf8,
            image_url=storefront.logo_url
        )

    send_message(json.dumps(
        build_list_card(
            recipient_id=recipient_id,
            body_elements=elements,
            header_element=header_element,
            quick_replies=main_menu_quick_replies(recipient_id)
        )
    ))


def send_app_card(recipient_id):
    logger.info("send_app_card(recipient_id=%s)" % (recipient_id,))

    data = build_standard_card(
        recipient_id=recipient_id,
        title="Lemonade on Messenger",
        image_url="https://scard.tv/static/images/lmon8-logo.jpg",
        item_url="http://m.me/lmon8?ref=/",
        buttons=[
            build_button(Const.CARD_BTN_URL, caption="View Bot", url="http://m.me/lmon8?ref=/"),
            build_button(Const.CARD_BTN_INVITE)
        ],
        quick_replies=main_menu_quick_replies(recipient_id)
    )

    send_message(json.dumps(data))


#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


def received_payload(recipient_id, payload, type=Const.PAYLOAD_TYPE_POSTBACK):
    logger.info("received_payload(recipient_id=%s, payload=%s, type=%s)" % (recipient_id, payload, type))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()


    # postback btn
    if payload == Const.PB_PAYLOAD_RANDOM_STOREFRONT:
        send_tracker(fb_psid=recipient_id, category="next-shop")
        add_points(recipient_id, Const.POINT_AMOUNT_NEXT_SHOP)

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)

                product = None
                while product is None:
                    cur.execute('SELECT `id` FROM `products` WHERE (`type` = 5 OR `type` = 6) AND `enabled` = 1 ORDER BY RAND() LIMIT 1;')
                    row = cur.fetchone()
                    if row is not None:
                        product = Product.query.filter(Product.id == row['id']).first()
                        if product is not None:
                            flip_product(customer.fb_psid, product)
                            view_product(recipient_id, product)

                    else:
                        send_text(recipient_id, "No shops are available to flip right now, try again later.", main_menu_quick_replies(recipient_id))

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

    elif payload == Const.PB_PAYLOAD_PRODUCT_PURCHASES:
        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).first()
        if storefront is not None:
            if Purchase.query.filter(Purchase.storefront_id == storefront.id).count() > 0:
                send_purchases_list_card(recipient_id, Const.CARD_TYPE_PRODUCT_PURCHASES)

            else:
                send_text(recipient_id, "You do not have any sales yet!", main_menu_quick_replies(recipient_id))

    elif payload == Const.PB_PAYLOAD_PRODUCTS_PURCHASED:
        if Purchase.query.filter(Purchase.customer_id == customer.id).count() > 0:
            send_purchases_list_card(recipient_id, Const.CARD_TYPE_PRODUCTS_PURCHASED)

        else:
            send_text(recipient_id, "You have not purchased anything yet!", main_menu_quick_replies(recipient_id))

    elif payload == Const.PB_PAYLOAD_GREETING:
        logger.info("----------=BOT GREETING @(%s)=----------" % (time.strftime("%Y-%m-%d %H:%M:%S")))
        welcome_message(recipient_id, Const.MARKETPLACE_GREETING)

    elif re.search(r'^AUTO_GEN_STOREFRONT-(.+)$', payload) is not None:
        storefront, product = autogen_storefront(recipient_id, re.match(r'^AUTO_GEN_STOREFRONT\-(?P<key>.+)$', payload).group('key'))
        send_text(recipient_id, "Auto generated your shop {storefront_name}.".format(storefront_name=storefront.display_name_utf8))
        send_text(recipient_id, product.messenger_url)
        send_text(recipient_id, "Every 2 {product_name}s you sell you will earn 1 {product_name}.".format(product_name=product.display_name_utf8))
        send_admin_carousel(recipient_id)

    elif payload == Const.PB_PAYLOAD_CREATE_STOREFRONT:
        # send_tracker(fb_psid=recipient_id, category="button-create-shop")

        try:
            Storefront.query.filter(Storefront.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        try:
            Product.query.filter(Product.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        storefront = Storefront(recipient_id)
        db.session.add(storefront)
        db.session.commit()

        send_text(recipient_id, "Give your Shopbot a name.", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_DELETE_STOREFRONT:
        # send_tracker(fb_psid=recipient_id, category="button-delete-shop")

        for storefront in Storefront.query.filter(Storefront.fb_psid == recipient_id):
            send_text(recipient_id, "{storefront_name} has been removed.".format(storefront_name=storefront.display_name_utf8))

            try:
                Product.query.filter(Product.storefront_id == storefront.id).delete()
                db.session.commit()
            except:
                db.session.rollback()

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('UPDATE `storefronts` SET `enabled` = 0 WHERE `id` = %s;', (storefront.id,))
                    cur.execute('UPDATE `products` SET `enabled` = 0 WHERE `storefront_id` = %s;', (storefront.id,))
                    cur.execute('UPDATE `subscriptions` SET `enabled` = 0 WHERE `storefront_id` = %s;', (storefront.id,))
                    conn.commit()

            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

        try:
            Storefront.query.filter(Storefront.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        send_admin_carousel(recipient_id)

    elif payload == Const.PB_PAYLOAD_ADD_PRODUCT:
        # send_tracker(fb_psid=recipient_id, category="button-add-item")

        try:
            Product.query.filter(Product.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).first()
        if storefront is not None:
            product = Product(recipient_id, storefront.id)
            db.session.add(product)
            db.session.commit()

            send_text(recipient_id, "Upload a photo or video of what you are selling.", cancel_entry_quick_reply())

        else:
            storefront = Storefront(recipient_id)
            db.session.add(storefront)
            db.session.commit()

            send_text(recipient_id, "Give your Shopbot a name.", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_DELETE_PRODUCT:
        # send_tracker(fb_psid=recipient_id, category="button-delete-item")

        for product in Product.query.filter(Product.fb_psid == recipient_id):
            send_text(recipient_id, "Removing your existing product \"{product_name}\"...".format(product_name=product.display_name_utf8))

            try:
                Subscription.query.filter(Subscription.product_id == product.id).delete()
                db.session.commit()
            except:
                db.session.rollback()

        try:
            Product.query.filter(Product.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).first()
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('UPDATE `products` SET `enabled` = 0 WHERE `storefront_id` = %s;', (storefront.id,))
                cur.execute('UPDATE `subscriptions` SET `enabled` = 0 WHERE `storefront_id` = %s;', (storefront.id,))
                conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        product = Product(recipient_id, storefront.id)
        db.session.add(product)
        db.session.commit()
        send_text(recipient_id, "Upload a photo or video of what you are selling.", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_SHARE_PRODUCT:
        send_tracker(fb_psid=recipient_id, category="share")
        product = Product.query.filter(Product.fb_psid == recipient_id).filter(Product.creation_state == 7).first()
        if product is not None:
            add_points(recipient_id, Const.POINT_AMOUNT_SHARE_PRODUCT)
            send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_SHARE)

    elif re.search('^VIEW_PRODUCT\-(\d+)$', payload) is not None:
        product_id = re.match(r'^VIEW_PRODUCT\-(?P<product_id>\d+)$', payload).group('product_id')
        product = Product.query.filter(Product.id == product_id).first()
        view_product(recipient_id, product)

    elif payload == Const.PB_PAYLOAD_SUPPORT:
        # send_tracker(fb_psid=recipient_id, category="button-support")
        send_text(recipient_id, "Support for Lemonade:\nprebot.me/support")

    elif payload == Const.PB_PAYLOAD_CHECKOUT_PRODUCT:
        # send_tracker(fb_psid=recipient_id, category="button-reserve")

        product = Product.query.filter(Product.id == customer.product_id).first()
        if product is not None:
            send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_CHECKOUT)

    elif payload == Const.PB_PAYLOAD_CHECKOUT_BITCOIN:
        send_tracker(fb_psid=recipient_id, category="purchase")

        try:
            Payment.query.filter(Payment.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        db.session.add(Payment(fb_psid=recipient_id, source=Const.PAYMENT_SOURCE_BITCOIN))
        db.session.commit()

        product = Product.query.filter(Product.id == customer.product_id).first()
        if customer.bitcoin_addr is not None:
            send_text(recipient_id, "Using your saved bitcoin address {bitcoin_addr} for this purchase...".format(bitcoin_addr=customer.bitcoin_addr))
            if purchase_product(recipient_id, Const.PAYMENT_SOURCE_BITCOIN):
                try:
                    Payment.query.filter(Payment.fb_psid == recipient_id).delete()
                    db.session.commit()
                except:
                    db.session.rollback()

                    # send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_RECEIPT)
            else:
                pass

            add_points(recipient_id, Const.POINT_AMOUNT_PURCHASE_PRODUCT)
            if "gamebotsmods" in product.tags_list:
                send_text(recipient_id, "To complete this purchase you must complete the PayPal payment & the instructions below.\n\n1. Install 2 free apps: taps.io/skins\n2. Wait for approval", main_menu_quick_replies(recipient_id))
            send_customer_carousel(recipient_id, product.id)

        else:
            send_text(recipient_id, "Post your Bitcoin wallet's QR code or typein  the address", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_CHECKOUT_CREDIT_CARD:
        send_tracker(fb_psid=recipient_id, category="purchase")

        try:
            Payment.query.filter(Payment.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        product = Product.query.filter(Product.id == customer.product_id).first()
        if product is not None:
            if customer.stripe_id is None or customer.card_id is None:
                try:
                    conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('SELECT `stripe_id`, `card_id` FROM `users` WHERE `id` = %s AND `stripe_id` != "" AND `card_id` != "" LIMIT 1;', (customer.id,))
                        row = cur.fetchone()

                        if row is not None:
                            customer.stripe_id = row['stripe_id']
                            customer.card_id = row['card_id']
                            db.session.commit()

                except mysql.Error, e:
                    logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                finally:
                    if conn:
                        conn.close()

            if customer.stripe_id is not None and customer.card_id is not None:
                send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_CHECKOUT_CC)

            else:
                add_cc_payment(recipient_id)

    elif payload == Const.PB_PAYLOAD_CHECKOUT_PAYPAL:
        send_tracker(fb_psid=recipient_id, category="purchase")

        try:
            Payment.query.filter(Payment.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        db.session.add(Payment(recipient_id, Const.PAYMENT_SOURCE_PAYPAL))
        db.session.commit()

        product = Product.query.filter(Product.id == customer.product_id).first()
        storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
        if purchase_product(recipient_id, Const.PAYMENT_SOURCE_PAYPAL):
            Payment.query.filter(Payment.fb_psid == recipient_id).delete()
            add_points(recipient_id, Const.POINT_AMOUNT_PURCHASE_PRODUCT)
            # send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_RECEIPT)
            # send_customer_carousel(recipient_id, product.id)

            # if product.tags is not None and "gamebotsmods" in product.tags:
            #     send_text(recipient_id, "To complete this purchase you must complete the PayPal payment & the instructions below.\n\n1. Install 2 free apps: taps.io/skins\n2. Wait for approval", main_menu_quick_replies(recipient_id))
            #
            # elif product.tags is not None and "gamebots" in product.tags:
            #     code = hashlib.md5(str(time.time()).encode()).hexdigest()[-4:].upper()
            #
            #     send_text(recipient_id, "To complete this purchase you must complete the PayPal payment & wait for approval then the url will be released to you", main_menu_quick_replies(recipient_id))
            #     send_text(recipient_id, "Purchase for bonus with code {code}".format(code=code), main_menu_quick_replies(recipient_id))
            #
            #     payload = {
            #         'token'   : time.time(),
            #         'action'  : "insert",
            #         'code'    : code,
            #         'fb_psid' : recipient_id,
            #         'counter' : 1
            #     }
            #     response = requests.post("http://beta.modd.live/api/bonus_code.php", data=payload)

    elif payload == Const.PB_PAYLOAD_PURCHASE_PRODUCT:
        # send_tracker(fb_psid=recipient_id, category="button-purchase")

        product = Product.query.filter(Product.id == customer.product_id).first()
        if product is not None:
            send_text(recipient_id, "Completing your purchase…")
            if purchase_product(recipient_id, Const.PAYMENT_SOURCE_CREDIT_CARD):
                try:
                    Payment.query.filter(Payment.fb_psid == recipient_id).delete()
                    db.session.commit()
                except:
                    db.session.rollback()

                add_points(recipient_id, Const.POINT_AMOUNT_PURCHASE_PRODUCT)
                send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_RECEIPT)
                if "gamebotsmods" in product.tags:
                    send_text(recipient_id, "To complete this purchase you must complete the PayPal payment & the instructions below.\n\n1. Install 2 free apps: taps.io/skins\n2. Wait for approval", main_menu_quick_replies(recipient_id))
            else:
                pass

            send_customer_carousel(recipient_id, product.id)


    elif payload == Const.PB_PAYLOAD_RATE_PRODUCT:
        # send_tracker(fb_psid=recipient_id, category="button-rate-storefront")
        send_product_card(recipient_id, customer.product_id, Const.CARD_TYPE_PRODUCT_RATE)

    elif payload == Const.PB_PAYLOAD_MESSAGE_CUSTOMERS:
        # send_tracker(fb_psid=recipient_id, category="button-message-customers")
        send_purchases_list_card(recipient_id, Const.CARD_TYPE_PRODUCT_PURCHASES)

    elif payload == Const.PB_PAYLOAD_PAYOUT_PAYPAL:
        # send_tracker(fb_psid=recipient_id, category="button-paypal-payout")

        customer.paypal_email = "_{PENDING}_"
        db.session.commit()
        send_text(recipient_id, "Enter your PayPal email address", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_PAYOUT_BITCOIN:
        # send_tracker(fb_psid=recipient_id, category="button-bitcoin-payout")

        customer.bitcoin_addr = "_{PENDING}_"
        db.session.commit()
        send_text(recipient_id, "Post your Bitcoin wallet's QR code or type in the address", cancel_entry_quick_reply())

    elif re.search(r'^DM_OPEN\-(\d+)$', payload) is not None:
        # send_tracker(fb_psid=recipient_id, category="button-dm-open")
        purchase_id = re.match(r'^DM_OPEN\-(?P<purchase_id>\d+)$', payload).group('purchase_id')
        purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
        send_text(recipient_id, "Send the seller" if purchase.customer_id == customer.id else "Send the buyer", dm_quick_replies(recipient_id, purchase_id, Const.DM_ACTION_SEND))

    elif re.search(r'^DM_SEND_FB_NAME\-(\d+)$', payload) is not None:
        # send_tracker(fb_psid=recipient_id, category="button-dm-send-fb-name")
        purchase_id = re.match(r'^DM_SEND_FB_NAME\-(?P<purchase_id>\d+)$', payload).group('purchase_id')
        purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
        customer.fb_name = "_{PENDING}_"
        customer.purchase_id = purchase.id
        db.session.commit()

        send_text(recipient_id, "Type your Facebook username for the seller" if purchase.customer_id == customer.id else "Type your Facebook username for the buyer", cancel_entry_quick_reply())

    elif re.search(r'^DM_SEND_URL\-(\d+)$', payload) is not None:
        purchase_id = re.match(r'^DM_SEND_URL\-(?P<purchase_id>\d+)$', payload).group('purchase_id')
        purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
        customer.paypal_name = "_{PENDING}_"
        customer.purchase_id = purchase.id
        db.session.commit()

        send_text(recipient_id, "Type your URL here", cancel_entry_quick_reply())

    elif re.search(r'^DM_REQUEST_INVOICE\-(\d+)$', payload) is not None:
        # send_tracker(fb_psid=recipient_id, category="button-dm-request-invoice")
        purchase_id = re.match(r'^DM_REQUEST_INVOICE\-(?P<purchase_id>\d+)$', payload).group('purchase_id')
        customer.purchase_id = purchase_id
        db.session.commit()

        purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
        purchase.claim_state = 1
        db.session.commit()

        storefront_query = db.session.query(Storefront.fb_psid).filter(Storefront.id == purchase.storefront_id).subquery('storefront_query')
        storefront_owner = Customer.query.filter(Customer.fb_psid.in_(storefront_query)).first()

        send_product_card(recipient_id, purchase.product_id, Const.CARD_TYPE_PRODUCT_INVOICE_PAYPAL)

    elif re.search(r'^DM_REQUEST_PAYMENT\-(\d+)$', payload) is not None:
        # send_tracker(fb_psid=recipient_id, category="button-dm-request-payment")
        purchase_id = re.match(r'^DM_REQUEST_PAYMENT\-(?P<purchase_id>\d+)$', payload).group('purchase_id')
        purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
        purchase.claim_state = 1
        db.session.commit()

        send_product_card(Customer.query.filter(Customer.id == purchase.customer_id).first().fb_psid, purchase.product_id, Const.CARD_TYPE_PRODUCT_INVOICE_PAYPAL)
        send_text(recipient_id, "Request sent", return_home_quick_reply())

    elif re.search(r'^DM_CANCEL_PURCHASE\-(\d+)$', payload) is not None:
        # send_tracker(fb_psid=recipient_id, category="button-dm-cancel-purchase")
        purchase_id = re.match(r'^DM_CANCEL_PURCHASE\-(?P<purchase_id>\d+)$', payload).group('purchase_id')
        purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
        route_purchase_dm(recipient_id, purchase, Const.DM_ACTION_SEND, "CANCEL_ORDER")

    elif re.search(r'^DM_CLOSE\-(\d+)$', payload) is not None:
        # send_tracker(fb_psid=recipient_id, category="button-dm-close")
        purchase_id = re.match(r'^DM_CLOSE\-(?P<purchase_id>\d+)$', payload).group('purchase_id')
        purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
        route_purchase_dm(recipient_id, purchase, Const.DM_ACTION_CLOSE)

    # quick replies
    elif payload == Const.PB_PAYLOAD_MAIN_MENU:
        # send_tracker(fb_psid=recipient_id, category="button-menu")

        # if customer.purchase_id is not None:
        #     send_text(
        #         recipient_id=recipient_id,
        #         message_text="Did you complete your purchase?",
        #         quick_replies=[
        #             build_quick_reply(Const.KWIK_BTN_TEXT, "Yes", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_PURCHASE_COMPLETED_YES, purchase_id=customer.purchase_id)),
        #             build_quick_reply(Const.KWIK_BTN_TEXT, "No", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_PURCHASE_COMPLETED_NO, purchase_id=customer.purchase_id))
        #         ] + cancel_entry_quick_reply()
        #     )
        #
        # else:
        customer.storefront_id = None
        customer.product_id = None
        customer.purchase_id = None
        db.session.commit()

        send_admin_carousel(recipient_id)


    elif payload == Const.PB_PAYLOAD_HOME_CONTENT:
        # send_tracker(fb_psid=recipient_id, category="button-ok")
        send_home_content(recipient_id)

    elif payload == Const.PB_PAYLOAD_NEXT_STOREFRONT:
        send_tracker(fb_psid=recipient_id, category="next-shop")
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `id` FROM `products` WHERE (`type` = 5 OR `type` = 6) AND `enabled` = 1 ORDER BY RAND() LIMIT 1;')
                row = cur.fetchone()
                if row is not None:
                    product = Product.query.filter(Product.id == row['id']).first()
                    if product is not None:
                        storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
                        if storefront is not None:
                            view_product(recipient_id, product)


        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

    elif payload == Const.PB_PAYLOAD_FEATURE_STOREFRONT:
        send_tracker(fb_psid=recipient_id, category="feature-shop")
        # send_text(recipient_id, "Tap here to purchase:\nhttps://paypal.me/gamebotsc/1.99", main_menu_quick_replies(recipient_id))

    elif payload == Const.PB_PAYLOAD_CANCEL_ENTRY_SEQUENCE:
        # send_tracker(fb_psid=recipient_id, category="button-cancel-entry-sequence")

        clear_entry_sequences(recipient_id)
        send_home_content(recipient_id)

    elif payload == Const.PB_PAYLOAD_SHARE_APP:
        # send_tracker(fb_psid=recipient_id, category="button-say-thanks")
        send_app_card(recipient_id)

    elif re.search(r'^SAY_THANKS\-(.+)$', payload) is not None:
        # send_tracker(fb_psid=recipient_id, category="button-say-thanks")
        send_image(re.match(r'^SAY_THANKS\-(?P<fb_psid>.+)$', payload).group('fb_psid'), Const.IMAGE_URL_SAY_THANKS)

    elif payload == Const.PB_PAYLOAD_SUBMIT_STOREFRONT:
        send_tracker(fb_psid=recipient_id, category="create-shop")

        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 3).first()
        if storefront is not None:
            storefront.creation_state = 4
            storefront.added = int(time.time())
            db.session.commit()

            add_points(recipient_id, Const.POINT_AMOUNT_SUBMIT_STOREFRONT)

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('INSERT INTO `storefronts` (`id`, `owner_id`, `name`, `display_name`, `description`, `logo_url`, `prebot_url`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, storefront.name, storefront.display_name_utf8, storefront.description_utf8, storefront.logo_url, storefront.prebot_url))
                    conn.commit()
                    cur.execute('SELECT @@IDENTITY AS `id` FROM `storefronts`;')
                    storefront.id = cur.fetchone()['id']
                    db.session.commit()

            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

            # send_tracker(fb_psid=recipient_id, category="shop-sign-up")

            fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
            slack_outbound(
                channel_name=Const.SLACK_ORTHODOX_CHANNEL,
                username=Const.SLACK_ORTHODOX_HANDLE,
                webhook=Const.SLACK_ORTHODOX_WEBHOOK,
                message_text="*{fb_name}* just created a shop named _{storefront_name}_.".format(fb_name=recipient_id if fb_user is None else fb_user.full_name_utf8, storefront_name=storefront.display_name_utf8),
                image_url=storefront.logo_url
            )

            send_text(
                recipient_id=recipient_id,
                message_text="Great! You have created {storefront_name}. Do you want to add your PayPal or Bitcoin to receive payment?".format(storefront_name=storefront.display_name_utf8),
                quick_replies=[
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Add PayPal", Const.PB_PAYLOAD_PAYOUT_PAYPAL),
                    # build_quick_reply(Const.KWIK_BTN_TEXT, "Add Bitcoin", Const.PB_PAYLOAD_PAYOUT_BITCOIN),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Not Now", Const.PB_PAYLOAD_MAIN_MENU)
                ]
            )

    elif payload == Const.PB_PAYLOAD_REDO_STOREFRONT:
        # send_tracker(fb_psid=recipient_id, category="button-redo-store")

        try:
            Storefront.query.filter(Storefront.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        storefront = Storefront(recipient_id)
        db.session.add(storefront)
        db.session.commit()

        send_text(recipient_id, "Give your Lemonade Shop Bot a name.", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_CANCEL_STOREFRONT:
        # send_tracker(fb_psid=recipient_id, category="button-cancel-store")

        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 3).first()
        if storefront is not None:
            send_text(recipient_id, "Canceling your {storefront_name} shop creation...".format(storefront_name=storefront.display_name_utf8))

        try:
            Storefront.query.filter(Storefront.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        send_admin_carousel(recipient_id)

    elif re.search('^PRODUCT_RELEASE_(\d+)_DAYS$', payload) is not None:
        match = re.match(r'^PRODUCT_RELEASE_(?P<days>\d+)_DAYS$', payload)
        # send_tracker("button-product-release-{days}-days-store".format(days=match.group('days')), recipient_id, "")

        product = Product.query.filter(Product.fb_psid == recipient_id).filter(Product.creation_state == 3).first()
        if product is not None:
            product.release_date = calendar.timegm((datetime.utcnow() + relativedelta(months=int(int(match.group('days')) / 30))).replace(hour=0, minute=0, second=0, microsecond=0).utctimetuple())
            product.description = "For sale starting on {release_date}".format(release_date=datetime.utcfromtimestamp(product.release_date).strftime('%a, %b %-d'))
            product.creation_state = 4
            db.session.commit()

            send_text(recipient_id, "This item will be available today" if int(match.group('days')) < 30 else "This item will be available {release_date}".format(release_date=datetime.utcfromtimestamp(product.release_date).strftime('%A, %b %-d')))
            send_text(
                recipient_id=recipient_id,
                message_text="Is {product_name} a physical or virtual good?".format(product_name=product.display_name_utf8),
                quick_replies=[
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Physical", Const.PB_PAYLOAD_PRODUCT_TYPE_PHYSICAL),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Virtual", Const.PB_PAYLOAD_PRODUCT_TYPE_VIRTUAL)
                ] + cancel_entry_quick_reply()
            )

    elif payload == Const.PB_PAYLOAD_PRODUCT_TYPE_PHYSICAL:
        # send_tracker(fb_psid=recipient_id, category="button-product-physical")

        product = Product.query.filter(Product.fb_psid == recipient_id).filter(Product.creation_state == 4).first()
        if product is not None:
            product.type_id = Const.PRODUCT_TYPE_PHYSICAL
            db.session.commit()

            send_text(
                recipient_id=recipient_id,
                message_text="Enter the URL of this product from your existing website",
                quick_replies=cancel_entry_quick_reply()
            )

    elif payload == Const.PB_PAYLOAD_PRODUCT_TYPE_VIRTUAL:
        # send_tracker(fb_psid=recipient_id, category="button-product-virtual")

        product = Product.query.filter(Product.fb_psid == recipient_id).filter(Product.creation_state == 4).first()
        if product is not None:
            product.type_id = Const.PRODUCT_TYPE_VIRTUAL
            product.creation_state = 5
            db.session.commit()

            send_text(
                recipient_id=recipient_id,
                message_text="Enter some category tags separated by spaces or tap Skip",
                quick_replies=[
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Skip", Const.PB_PAYLOAD_PRODUCT_TAG_SKIP)
                ] + cancel_entry_quick_reply()
        )

    elif payload == Const.PB_PAYLOAD_PRODUCT_TAG_SKIP:
        # send_tracker(fb_psid=recipient_id, category="button-skip-tags")

        product = Product.query.filter(Product.fb_psid == recipient_id).filter(Product.creation_state == 5).first()
        if product is not None:
            product.creation_state = 6
            db.session.commit()

            send_text(recipient_id, "Here's what your product will look like:")
            send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_PREVIEW)

    elif payload == Const.PB_PAYLOAD_SUBMIT_PRODUCT:
        send_tracker(fb_psid=recipient_id, category="add-product")

        product = Product.query.filter(Product.fb_psid == recipient_id).first()
        if product is not None:
            product.creation_state = 7
            product.added = int(time.time())
            db.session.commit()

            add_points(recipient_id, Const.POINT_AMOUNT_SUBMIT_PRODUCT)
            logger.info("INSERT -------->")

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('SELECT * FROM `products` WHERE `name` = %s AND `enabled` = 1;', (product.name,))
                    logger.info("cur.fetchone() is None (%s)", (cur.fetchone() is None,))
                    if cur.fetchone() is None:
                        cur.execute('INSERT INTO `products` (`id`, `storefront_id`, `type`, `name`, `display_name`, `description`, `tags`, `image_url`, `video_url`, `attachment_id`, `price`, `prebot_url`, `physical_url`, `release_date`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s), UTC_TIMESTAMP());', (product.storefront_id, product.type_id, product.name, product.display_name_utf8, product.description, "" if product.tags is None else product.tags.encode('utf-8'), product.image_url, product.video_url or "", product.attachment_id or "", product.price, product.prebot_url, product.physical_url or "", product.release_date))
                        conn.commit()
                        cur.execute('SELECT @@IDENTITY AS `id` FROM `products`;')
                        product.id = cur.fetchone()['id']
                        db.session.commit()

            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

            storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
            fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
            slack_outbound(
                channel_name=Const.SLACK_ORTHODOX_CHANNEL,
                username=Const.SLACK_ORTHODOX_HANDLE,
                webhook=Const.SLACK_ORTHODOX_WEBHOOK,
                message_text="*{fb_name}* just created a {product_type} product named _{product_name}_ for the shop _{storefront_name}_.\n{physical_url}".format(fb_name=recipient_id if fb_user is None else fb_user.full_name_utf8, product_type="virtual" if product.type_id == Const.PRODUCT_TYPE_VIRTUAL else "physical", product_name=product.display_name_utf8, storefront_name=storefront.display_name_utf8, physical_url=product.physical_url or ""),
                image_url=product.image_url
            )

            send_admin_carousel(recipient_id)

            # send_image(recipient_id, Const.IMAGE_URL_PRODUCT_CREATED)
            send_text(
                recipient_id=recipient_id,
                message_text="You have successfully added {product_name} to {storefront_name}.\n\nShare {product_name}'s card with your customers now.\n\n{product_url}\n\nTap Menu then Share on Messenger.".format(product_name=product.display_name_utf8, storefront_name=storefront.display_name_utf8, product_url=product.messenger_url),
                quick_replies=main_menu_quick_replies(recipient_id)
            )


            # prev_subscribers = []
            # try:
            #     conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            #     with conn:
            #         cur = conn.cursor(mysql.cursors.DictCursor)
            #         cur.execute('SELECT `user_id` FROM `subscriptions` WHERE `storefront_id` = %s;', (storefront.id))
            #         for row in cur.fetchall():
            #             customer = Customer.query.filter(Customer.id == row['user_id']).first()
            #             if customer is not None:
            #                 prev_subscribers.append(customer.fb_psid)
            #
            # except mysql.Error, e:
            #     logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))
            #
            # finally:
            #     if conn:
            #         conn.close()
            #
            # for fb_psid in prev_subscribers:
            #     send_text(
            #         recipient_id=fb_psid,
            #         message_text="{storefront_name} just added {product_name} to their shop!".format(storefront_name=storefront.display_name_utf8, product_name=product.display_name_utf8),
            #         quick_replies=[
            #             build_quick_reply(Const.KWIK_BTN_TEXT, "View Product", payload="{payload}-{product_id}".format(payload=Const.PB_PAYLOAD_VIEW_PRODUCT, product_id=product.id)),
            #         ] + cancel_entry_quick_reply()
            #     )

    elif payload == Const.PB_PAYLOAD_REDO_PRODUCT:
        # send_tracker(fb_psid=recipient_id, category="button-redo-product")

        try:
            Product.query.filter(Product.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).first()
        db.session.add(Product(recipient_id, storefront.id))
        db.session.commit()

        send_text(recipient_id, "Upload a photo or video of what you are selling.", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_CANCEL_PRODUCT:
        # send_tracker(fb_psid=recipient_id, category="button-undo-product")

        product = Product.query.filter(Product.fb_psid == recipient_id).first()
        if product is not None:
            send_text(recipient_id, "Canceling your {product_name} product creation...".format(product_name=product.display_name_utf8))

        try:
            Product.query.filter(Product.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        send_admin_carousel(recipient_id)

    elif payload == Const.PB_PAYLOAD_AFFILIATE_GIVEAWAY:
        # send_tracker(fb_psid=recipient_id, category="button-givaway")
        send_text(recipient_id, "Win CS:GO items by playing flip coin with Lemonade! Details coming soon.", quick_replies=[build_quick_reply(Const.KWIK_BTN_TEXT, caption="Menu", payload=Const.PB_PAYLOAD_MAIN_MENU)])

    elif payload == Const.PB_PAYLOAD_PREBOT_URL:
        # send_tracker(fb_psid=recipient_id, category="button-url")

        product = Product.query.filter(Product.fb_psid == recipient_id).first()
        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).first()
        if storefront is not None and product is not None:
            send_text(recipient_id, "http://{messenger_url}".format(messenger_url=product.messenger_url), main_menu_quick_replies(recipient_id))
            send_text(recipient_id, "Tap, hold, copy {storefront_name}'s shop link above.".format(storefront_name=storefront.display_name_utf8), main_menu_quick_replies(recipient_id))

        else:
            send_text(recipient_id, "Couldn't locate your shop!", main_menu_quick_replies(recipient_id))

    elif payload == Const.PB_PAYLOAD_GIVEAWAYS_YES:
        # send_tracker(fb_psid=recipient_id, category="button-giveaways-yes")

        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).first()
        storefront.giveaway = 1
        db.session.commit()

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('UPDATE `storefronts` SET `giveaway` = 1 WHERE `id` = %s;', (storefront.id,))
                conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        product = Product.query.filter(Product.storefront_id == storefront.id).first()
        if product is not None:
            subscriptions = Subscription.query.filter(Subscription.product_id == product.id).filter(Subscription.enabled == 1).all()
            send_text(
                recipient_id=recipient_id,
                message_text="Great! Once you have 20 customers subscribed to {storefront_name} item giveaways will unlock.".format(storefront_name=storefront.display_name_utf8) if len(subscriptions) < 20 else "Great! Item giveaways will now be unlocked for {storefront_name}.".format(storefront_name=storefront.display_name_utf8),
                quick_replies=main_menu_quick_replies(recipient_id)
            )

        else:
            send_text(recipient_id, "Great! Once you have 20 customers subscribed to {storefront_name} item giveaways will unlock.".format(storefront_name=storefront.display_name_utf8), [build_quick_reply(Const.KWIK_BTN_TEXT, caption="Menu", payload=Const.PB_PAYLOAD_MAIN_MENU)])

    elif payload == Const.PB_PAYLOAD_GIVEAWAYS_NO:
        # send_tracker(fb_psid=recipient_id, category="button-giveaways-no")
        send_admin_carousel(recipient_id)

    elif payload == Const.PB_PAYLOAD_CHECKOUT_PRODUCT:
        # send_tracker(fb_psid=recipient_id, category="button-reserve")

        product = Product.query.filter(Product.id == customer.product_id).first()
        if product is not None:
            send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_CHECKOUT)

    elif payload == Const.PB_PAYLOAD_PAYMENT_YES:
        # send_tracker(fb_psid=recipient_id, category="button-payment-yes")
        # send_tracker(fb_psid=recipient_id, category="button-purchase-product")

        payment = Payment.query.filter(Payment.fb_psid == recipient_id).filter(Payment.source == Const.PAYMENT_SOURCE_CREDIT_CARD).filter(Payment.creation_state == 5).first()
        if payment is not None:
            payment.creation_state = 6
            db.session.commit()
            send_product_card(recipient_id, customer.product_id, Const.CARD_TYPE_PRODUCT_CHECKOUT_CC if add_cc_payment(recipient_id) else Const.CARD_TYPE_PRODUCT_CHECKOUT)

    elif payload == Const.PB_PAYLOAD_PAYMENT_NO:
        # send_tracker(fb_psid=recipient_id, category="button-payment-no")
        try:
            Payment.query.filter(Payment.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()
        add_cc_payment(recipient_id)

    elif payload == Const.PB_PAYLOAD_PAYMENT_CANCEL:
        # send_tracker(fb_psid=recipient_id, category="button-payment-cancel")

        try:
            Payment.query.filter(Payment.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        send_product_card(recipient_id, customer.product_id, Const.CARD_TYPE_PRODUCT_CHECKOUT)

    elif payload == Const.PB_PAYLOAD_PAYOUT_PAYPAL:
        # send_tracker(fb_psid=recipient_id, category="button-paypal-payout")

        # customer.paypal_name = "_{PENDING}_"
        # db.session.commit()
        # send_text(recipient_id, "Enter your PayPal.Me handle", cancel_entry_quick_reply())

        customer.paypal_email = "_{PENDING}_"
        db.session.commit()
        send_text(recipient_id, "Enter your PayPal email address", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_PAYOUT_BITCOIN:
        # send_tracker(fb_psid=recipient_id, category="button-bitcoin-payout")

        customer.bitcoin_addr = "_{PENDING}_"
        db.session.commit()
        send_text(recipient_id, "Post your Bitcoin wallet's QR code or type in the address", cancel_entry_quick_reply())

    elif re.search(r'^PAYPAL_PURCHASE_COMPLETE\-(\d+)$', payload) is not None:
        purchase = Purchase.query.filter(Purchase.id == re.match(r'^PAYPAL_PURCHASE_COMPLETE\-(?P<purchase_id>.+)$', payload).group('purchase_id')).first()
        if purchase is not None:
            product = Product.query.filter(Product.id == purchase.product_id).first()
            storefront = Storefront.query.filter(Storefront.id == purchase.storefront_id).first()

            customer.paypal_name = "_{PENDING}_"
            db.session.commit()
            send_text(recipient_id, "Type your trade URL here", cancel_entry_quick_reply())

    elif re.search(r'^PRODUCT_RATE_(\d+)_STAR$', payload) is not None:
        match = re.match(r'PRODUCT_RATE_(?P<stars>\d+)_STAR', payload)
        # send_tracker("button-product-rate-{stars}-star".format(stars=match.group('stars')), recipient_id, "")

        purchase = Purchase.query.filter(Purchase.id == customer.purchase_id).first()
        product = Product.query.filter(Product.id == purchase.product_id).first()

        if product is not None:
            rating = Rating(product.id, recipient_id, int(match.group('stars')))
            db.session.add(rating)

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('INSERT INTO `product_ratings` (`id`, `product_id`, `user_id`, `stars`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (product.id, customer.id, rating.stars))
                    conn.commit()

            except mysql.Error as e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

            total_rating = 0.0
            for rating in Rating.query.filter(Rating.product_id == product.id):
                total_rating += rating.stars

            product.avg_rating = total_rating / float(min(max(Rating.query.filter(Rating.product_id == product.id).count(), 1), 5))
            db.session.commit()

            send_text(recipient_id, "Thank you for your feedback!")
            send_customer_carousel(recipient_id, product.id)

    elif payload == Const.PB_PAYLOAD_ACTIVATE_PRO_STOREFRONT:
        # send_tracker(fb_psid=recipient_id, category="button-activate-pro")
        pass

    else:
        # send_tracker(fb_psid=recipient_id, category="unknown-button")
        send_text(recipient_id, "Button not recognized!")



def recieved_attachment(recipient_id, attachment_type, payload):
    logger.info("recieved_attachment(recipient_id=%s, attachment_type=%s, payload=%s)" % (recipient_id, attachment_type, payload))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

    #return "OK", 200


    #------- IMAGE MESSAGE
    if attachment_type == "image":
        logger.info("IMAGE: %s" % (payload))

        if customer.bitcoin_addr == "_{PENDING}_":
            timestamp = ("%d" % (int(time.time())))
            image_file = "/var/www/html/thumbs/qr_{timestamp}.jpg".format(timestamp=timestamp)

            copy_thread = threading.Thread(
                target=copy_remote_asset,
                name="qr_copy",
                kwargs={
                    'src_url'    : payload['url'],
                    'local_file' : image_file
                }
            )
            copy_thread.start()
            copy_thread.join()

            qr = qrtools.QR()
            qr.decode(image_file)

            if 'bitcoin' in qr.data and re.search(r'^(.*)?[13][a-km-zA-HJ-NP-Z1-9]{25,34}(.*)?$', qr.data) is not None:
                bitcoin_addr = re.match(r'^(.*)?(?P<bitcoin_addr>[13][a-km-zA-HJ-NP-Z1-9]{25,34})(.*)?$', qr.data).group('bitcoin_addr')
                customer.bitcoin_addr = bitcoin_addr
                db.session.commit()

                try:
                    conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('SELECT `id` FROM `payout` WHERE `user_id` = %s LIMIT 1;', (customer.id,))
                        row = cur.fetchone()
                        if row is None:
                            cur.execute('INSERT INTO `payout` (`id`, `user_id`, `bitcoin`, `updated`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP(), UTC_TIMESTAMP());', (customer.id, customer.bitcoin_addr))
                        else:
                            cur.execute('UPDATE `payout` SET `bitcoin` = %s, `updated` = UTC_TIMESTAMP() WHERE `id` = %s LIMIT 1;', (customer.bitcoin_addr, row['id']))
                        conn.commit()

                except mysql.Error, e:
                    logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                finally:
                    if conn:
                        conn.close()

                send_text(recipient_id, "Bitcoin payout address set to {bitcoin_addr}".format(bitcoin_addr=customer.bitcoin_addr))
                send_text(recipient_id, "Great! You have created {storefront_name}. Now add an item to sell.".format(storefront_name=storefront.display_name_utf8))
                send_admin_carousel(recipient_id)

            else:
                send_text(recipient_id, "Invalid bitcoin address, please resubmit QR code.", quick_replies=cancel_entry_quick_reply())

            return "OK", 200


        #-- bitcoin payment
        payment = Payment.query.filter(Payment.fb_psid == recipient_id).filter(Payment.source == Const.PAYMENT_SOURCE_BITCOIN).first()
        if payment is not None:
            timestamp = ("%d" % (int(time.time())))
            image_file = "/var/www/html/thumbs/qr_{timestamp}.jpg".format(timestamp=timestamp)

            copy_thread = threading.Thread(
                target=copy_remote_asset,
                name="qr_copy",
                kwargs={
                    'src_url'    : payload['url'],
                    'local_file' : image_file
                }
            )
            copy_thread.start()
            copy_thread.join()

            qr = qrtools.QR()
            qr.decode(image_file)

            if 'bitcoin' in qr.data and re.search(r'^(.*)?[13][a-km-zA-HJ-NP-Z1-9]{25,34}(.*)?$', qr.data) is not None:
                bitcoin_addr = re.match(r'^(.*)?(?P<bitcoin_addr>[13][a-km-zA-HJ-NP-Z1-9]{25,34})(.*)?$', qr.data).group('bitcoin_addr')

                customer.bitcoin_addr = bitcoin_addr
                db.session.commit()

                send_text(recipient_id, "Bitcoin address set to {bitcoin_addr}".format(bitcoin_addr=customer.bitcoin_addr))
                purchase_product(recipient_id, Const.PAYMENT_SOURCE_BITCOIN)

            else:
                send_text(recipient_id, "Invalid bitcoin address, please resubmit QR code.", quick_replies=cancel_entry_quick_reply())

            return "OK", 200


        #-- storefront creation
        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).first()
        if storefront is not None:
            if storefront.creation_state == 2:
                timestamp = ("%.03f" % (time.time())).replace(".", "_")
                image_file = "/var/www/html/thumbs/{timestamp}.jpg".format(timestamp=timestamp)

                copy_thread = threading.Thread(
                    target=copy_remote_asset,
                    name="image_copy",
                    kwargs={
                        'src_url'    : payload['url'],
                        'local_file' : image_file
                    }
                )
                copy_thread.start()
                copy_thread.join()

                storefront.creation_state = 3
                storefront.logo_url = "http://lmon.us/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
                db.session.commit()

                send_text(recipient_id, "Here's what your Shopbot will look like:")
                send_storefront_card(recipient_id, storefront.id, Const.CARD_TYPE_STOREFRONT_PREVIEW)

                image_sizer_sq = ImageSizer(image_file)
                image_sizer_sq.start()

                image_sizer_ls = ImageSizer(in_file=image_file, out_file=None, canvas_size=(400, 300))
                image_sizer_ls.start()

                image_sizer_pt = ImageSizer(in_file=image_file, out_file=None, canvas_size=(480, 640))
                image_sizer_pt.start()

                image_sizer_ws = ImageSizer(in_file=image_file, canvas_size=(1280, 720))
                image_sizer_ws.start()

                return "OK", 200


            #-- product creation
            elif storefront.creation_state == 4:
                logger.info("---------------- HAS STORE")
                product = Product.query.filter(Product.storefront_id == storefront.id).filter(Product.creation_state == 0).first()
                if product is not None:
                    logger.info("---------------- PRODUCT HERE")
                    timestamp = ("%.03f" % (time.time())).replace(".", "_")
                    image_file = "/var/www/html/thumbs/{timestamp}.jpg".format(timestamp=timestamp)

                    copy_thread = threading.Thread(
                        target=copy_remote_asset,
                        name="image_copy",
                        kwargs={
                            'src_url'    : payload['url'],
                            'local_file' : image_file
                        }
                    )
                    copy_thread.start()
                    copy_thread.join()

                    product.creation_state = 1
                    product.image_url = "http://lmon.us/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
                    db.session.commit()

                    send_text(recipient_id, "Give your product a title.", cancel_entry_quick_reply())

                    image_sizer_sq = ImageSizer(in_file=image_file, out_file=None)
                    image_sizer_sq.start()

                    image_sizer_ls = ImageSizer(in_file=image_file, out_file=None, canvas_size=(400, 300))
                    image_sizer_ls.start()

                    image_sizer_pt = ImageSizer(in_file=image_file, out_file=None, canvas_size=(480, 640))
                    image_sizer_pt.start()

                    image_sizer_ws = ImageSizer(in_file=image_file, canvas_size=(1280, 720))
                    image_sizer_ws.start()

                else:
                    handle_wrong_reply(recipient_id)

                return "OK", 200

        else:
            handle_wrong_reply(recipient_id)


    #------- VIDEO MESSAGE
    elif attachment_type == "video":
        logger.info("VIDEO: %s" % (payload['url']))

        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).first()
        if storefront is None or storefront.creation_state < 4:
            handle_wrong_reply(recipient_id)

        storefront_query = db.session.query(Storefront.id).filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).subquery('storefront_query')
        product = Product.query.filter(Product.storefront_id.in_(storefront_query)).filter(Product.creation_state == 0).first()
        if product is not None:
            timestamp = ("%.03f" % (time.time())).replace(".", "_")
            image_file = "/var/www/html/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
            video_file = "/var/www/html/videos/{timestamp}.mp4".format(timestamp=timestamp)

            video_metadata = VideoMetaData(payload['url'])
            video_metadata.start()
            video_metadata.join()

            copy_thread = threading.Thread(
                target=copy_remote_asset,
                name="video_copy",
                kwargs={
                    'src_url'    : payload['url'],
                    'local_file' : video_file
                }
            )
            copy_thread.start()
            copy_thread.join()

            image_renderer = VideoImageRenderer(video_file, image_file, int(video_metadata.info['duration'] * 0.5))
            image_renderer.start()
            image_renderer.join()

            image_sizer_sq = ImageSizer(in_file=image_file, out_file=None)
            image_sizer_sq.start()

            image_sizer_ls = ImageSizer(in_file=image_file, out_file=None, canvas_size=(400, 300))
            image_sizer_ls.start()

            image_sizer_pt = ImageSizer(in_file=image_file, out_file=None, canvas_size=(480, 640))
            image_sizer_pt.start()

            image_sizer_ws = ImageSizer(in_file=image_file, canvas_size=(1280, 720))
            image_sizer_ws.start()

            product.creation_state = 1
            product.image_url = "http://lmon.us/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
            product.video_url = "http://lmon.us/videos/{timestamp}.mp4".format(timestamp=timestamp)
            db.session.commit()

            send_text(recipient_id, "Give your product a title.", cancel_entry_quick_reply())

        else:
            handle_wrong_reply(recipient_id)
            return "OK", 200

    else:
        send_admin_carousel(recipient_id)

    return "OK", 200


def received_text_response(recipient_id, message_text):
    logger.info("received_text_response(recipient_id=%s, message_text=%s)" % (recipient_id, message_text))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

    #-- purge sqlite db
    if message_text == "/shops":
        message_text = "Active shops:"
        for product in db.session.query(Product).filter((Product.id < 949) & (Product.id > 9866)).filter(Product.creation_state == 7):
            logger.info("-------- %s" % (product.display_name_utf8,))
            message_text = "{message_text}\n/{deeplink}".format(message_text=message_text, deeplink=product.name)
        send_text(recipient_id, message_text)

    elif message_text == "/featured":
        send_featured_carousel(recipient_id)


    #-- gamebots referral code
    elif message_text.startswith(":"):
        pass


    #-- force referral
    elif message_text.startswith("/"):
        welcome_message(recipient_id, Const.CUSTOMER_REFERRAL, message_text)


    #-- show admin carousel
    elif message_text.lower() in Const.RESERVED_COMMAND_REPLIES:
        clear_entry_sequences(recipient_id)
        send_admin_carousel(recipient_id)


    #-- appnext reply
    elif message_text.lower() in Const.RESERVED_APPNEXT_REPLIES:
        send_text(recipient_id, "Instructions…\n\n1. GO: taps.io/skins\n\n2. OPEN & Screenshot each free game or app you install.\n\n3. SEND screenshots for proof on Twitter.com/gamebotsc \n\nEvery free game or app you install increases your chances of winning.", main_menu_quick_replies(recipient_id))


    elif message_text.lower() in Const.RESERVED_BONUS_AUTO_GEN_REPLIES:
        storefront, product = autogen_storefront(recipient_id, message_text)

        send_text(recipient_id, "Auto generated your shop {storefront_name}.".format(storefront_name=storefront.display_name_utf8))
        send_text(recipient_id, product.messenger_url)
        send_text(recipient_id, "Every 2 {product_name}s you sell you will earn 1 {product_name}.".format(product_name=product.display_name_utf8))
        send_admin_carousel(recipient_id)


    #-- quit message
    elif message_text.lower() in Const.RESERVED_OPTOUT_REPLIES:
        clear_entry_sequences(recipient_id)
        send_text(recipient_id, Const.GOODBYE_MESSAGE)

    else:
        #-- entering paypal payout info
        if customer.paypal_email == "_{PENDING}_":
            if re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', message_text) is None:
                send_text(recipient_id, "Invalid email address, try again", cancel_entry_quick_reply())

            # if re.match(r'^[a-zA-Z0-9_.+-]+$', message_text) is None:
            #     send_text(recipient_id, "Invalid PayPal.Me handle, try again", cancel_entry_quick_reply())

            else:
                customer.paypal_email = message_text
                db.session.commit()

                try:
                    conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('SELECT `id` FROM `payout` WHERE `user_id` = %s LIMIT 1;', (customer.id,))
                        row = cur.fetchone()
                        if row is None:
                            cur.execute('INSERT INTO `payout` (`id`, `user_id`, `paypal_email`, `updated`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP(), UTC_TIMESTAMP());', (customer.id, message_text))
                        else:
                            cur.execute('UPDATE `payout` SET `paypal_email` = %s, `updated` = UTC_TIMESTAMP() WHERE `id` = %s LIMIT 1;', (message_text, row['id']))
                        conn.commit()

                except mysql.Error, e:
                    logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                finally:
                    if conn:
                        conn.close()

                send_text(recipient_id, "PayPal email set", main_menu_quick_replies(recipient_id))

                storefront_query = db.session.query(Storefront.id).filter(Storefront.fb_psid == recipient_id).subquery('storefront_query')
                purchase = Purchase.query.filter(Purchase.storefront_id.in_(storefront_query)).filter(Purchase.claim_state == 1).first()
                if purchase is not None:
                    send_product_card(Customer.query.filter(Customer.id == purchase.customer_id).first().fb_psid, purchase.product_id, Const.CARD_TYPE_PRODUCT_INVOICE_PAYPAL)

            return "OK", 200


        #-- entering bitcoin payout
        if customer.bitcoin_addr == "_{PENDING}_":
            if re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', message_text) is None:
                send_text(recipient_id, "Invalid bitcoin address, it needs to start w/ 1 or 3, and be between 26 & 35 characters long.", quick_replies=cancel_entry_quick_reply())
                return "OK", 200

            else:
                customer.bitcoin_addr = None
                db.session.commit()

                try:
                    conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('SELECT `id` FROM `payout` WHERE `user_id` = %s LIMIT 1;', (customer.id,))
                        row = cur.fetchone()
                        if row is None:
                            cur.execute('INSERT INTO `payout` (`id`, `user_id`, `bitcoin`, `updated`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP(), UTC_TIMESTAMP());', (customer.id, message_text))
                        else:
                            cur.execute('UPDATE `payout` SET `bitcoin` = %s, `updated` = UTC_TIMESTAMP() WHERE `id` = %s LIMIT 1;', (message_text, row['id']))
                        conn.commit()

                except mysql.Error, e:
                    logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                finally:
                    if conn:
                        conn.close()

                send_text(recipient_id, "Bitcoin payout address set to {bitcoin_addr}".format(bitcoin_addr=message_text), main_menu_quick_replies(recipient_id))

                storefront_query = db.session.query(Storefront.id).filter(Storefront.fb_psid == recipient_id).subquery('storefront_query')
                purchase = Purchase.query.filter(Purchase.storefront_id.in_(storefront_query)).filter(Purchase.claim_state == 1).first()
                if purchase is not None:
                    route_purchase_dm(recipient_id, purchase, Const.DM_ACTION_SEND, "Send payment to bitcoin address {bitcoin_addr}".format(paypal_addr=message_text))

                else:
                    send_admin_carousel(recipient_id)

            return "OK", 200


        #-- check for in-progress payment
        payment = Payment.query.filter(Payment.fb_psid == recipient_id).first()
        if payment is not None:
            product = Product.query.filter(Product.id == customer.product_id).first()
            if product is not None:
                if payment.source == Const.PAYMENT_SOURCE_BITCOIN:
                    if re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', message_text) is None:
                        send_text(recipient_id, "Invalid bitcoin address, it needs to start w/ 1 or 3, and be between 26 & 35 characters long.", quick_replies=cancel_entry_quick_reply())

                    else:
                        customer.bitcoin_addr = message_text
                        db.session.commit()

                        if purchase_product(recipient_id, Const.PAYMENT_SOURCE_BITCOIN):
                            try:
                                Payment.query.filter(Payment.fb_psid == recipient_id).delete()
                                db.session.commit()
                            except:
                                db.session.rollback()
                                # send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_RECEIPT)
                        else:
                            pass

                        send_customer_carousel(recipient_id, product.id)

                elif payment.source == Const.PAYMENT_SOURCE_CREDIT_CARD:
                    if payment.creation_state == 0:
                        if re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', message_text) is None:
                            send_text(recipient_id, "Invalid email address, try again", cancel_entry_quick_reply())

                        else:
                            customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
                            customer.email = message_text
                            payment.email = message_text
                            payment.creation_state = 1
                            send_text(recipient_id, "Enter the card holder's name", cancel_entry_quick_reply())

                    elif payment.creation_state == 1:
                        payment.full_name = message_text
                        payment.creation_state = 2
                        send_text(recipient_id, "Enter the card's account number", cancel_entry_quick_reply())

                    elif payment.creation_state == 2:
                        if message_text.isdigit():
                            payment.acct_number = message_text
                            payment.creation_state = 3
                            send_text(recipient_id, "Enter the card's expiration date (example MM/YY)", cancel_entry_quick_reply())

                        else:
                            send_text(recipient_id, "Card account numbers need to be only digits", cancel_entry_quick_reply())

                    elif payment.creation_state == 3:
                        if re.match(r'^(1[0-2]|0[1-9])\/([1-9]\d)$', message_text) is None:
                            send_text(recipient_id, "Expiration date needs to be in the format MM/YY", cancel_entry_quick_reply())

                        else:
                            payment.expiration = datetime.strptime(message_text, '%m/%y').date()
                            payment.creation_state = 4
                            send_text(recipient_id, "Enter the CVC or CVV2 code on the card's back", cancel_entry_quick_reply())

                    elif payment.creation_state == 4:
                        if re.match(r'^(\d{3,})$', message_text) is None:
                            send_text(recipient_id, "CVC / CVV2 codes need to be at least 3 digits", cancel_entry_quick_reply())

                        else:
                            payment.cvc = message_text
                            payment.creation_state = 5

                            send_text(
                                recipient_id = recipient_id,
                                message_text= "Are these details correct?\nEmail: {email}\nName: {full_name}\nCard #: {acct_number}\nExpiration: {expiration:%m/%Y}\nCVC / CVV2: {cvc}".format(email=payment.email, full_name=payment.full_name, acct_number=(re.sub(r'\d', "*", payment.acct_number)[:-4] + payment.acct_number[-4:]), expiration=payment.expiration, cvc=payment.cvc),
                                quick_replies = [
                                    build_quick_reply(Const.KWIK_BTN_TEXT, "Yes", Const.PB_PAYLOAD_PAYMENT_YES),
                                    build_quick_reply(Const.KWIK_BTN_TEXT, "No", Const.PB_PAYLOAD_PAYMENT_NO),
                                ] + cancel_entry_quick_reply()
                            )


                elif payment.source == Const.PAYMENT_SOURCE_PAYPAL:
                    customer.paypal_email = message_text
                    db.session.commit()

                    if purchase_product(recipient_id, Const.PAYMENT_SOURCE_PAYPAL):
                        try:
                            Payment.query.filter(Payment.fb_psid == recipient_id).delete()
                            db.session.commit()
                        except:
                            db.session.rollback()
                        # send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_RECEIPT)
                    else:
                        pass

                    send_customer_carousel(recipient_id, product.id)

            return "OK", 200

        if customer.fb_name == "_{PENDING}_":
            purchase = Purchase.query.filter(Purchase.id == customer.purchase_id).first()
            if purchase is not None:
                customer.fb_name = message_text
                db.session.commit()
                route_purchase_dm(recipient_id, purchase, Const.DM_ACTION_SEND, "Contact me directly: https://m.me/{fb_name}".format(fb_name=customer.fb_name))

            return "OK", 200

        if customer.paypal_name == "_{PENDING}_":
            purchase = Purchase.query.filter(Purchase.id == customer.purchase_id).first()

            if purchase is not None:
                customer.paypal_name = message_text
                db.session.commit()
                route_purchase_dm(recipient_id, purchase, Const.DM_ACTION_SEND, "My trade URL: {paypal_name}".format(paypal_name=customer.paypal_name))
                send_text(recipient_id, "Trade URL set to: {paypal_name}".format(paypal_name=customer.paypal_name), main_menu_quick_replies(recipient_id))
                send_customer_carousel(recipient_id, purchase.product_id)

            return "OK", 200

        #-- has active storefront
        storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).first()
        if storefront is not None:

            #-- look for in-progress product creation
            product = Product.query.filter(Product.storefront_id == storefront.id).filter(Product.creation_state < 7).first()
            if product is not None:

                #-- name submitted
                if product.creation_state == 1:
                    try:
                        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('SELECT `id` FROM `products` WHERE `display_name` = %s AND `enabled` = 1;', (message_text,))
                            row = cur.fetchone()

                            if row is None:
                                product.creation_state = 2
                                product.display_name = message_text
                                product.name = re.sub(Const.IGNORED_NAME_PATTERN, "", message_text.encode('ascii', 'ignore'))
                                product.prebot_url = "http://prebot.me/{product_name}".format(product_name=product.name)
                                db.session.commit()

                            send_text(recipient_id, "That name is already taken, please choose another" if row is not None else "Enter the price of {product_name} in USD. (example 78.00)".format(product_name=product.display_name_utf8), cancel_entry_quick_reply())

                    except mysql.Error, e:
                        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                    finally:
                        if conn:
                            conn.close()


                elif product.creation_state == 2:
                    if message_text.replace(".", "", 1).isdigit():
                        product.creation_state = 3
                        product.price = round(float(message_text), 2)
                        db.session.commit()

                        send_text(
                            recipient_id=recipient_id,
                            message_text="Select a date the product will be available.",
                            quick_replies=[
                                build_quick_reply(Const.KWIK_BTN_TEXT, "Right Now", Const.PB_PAYLOAD_PRODUCT_RELEASE_NOW),
                                build_quick_reply(Const.KWIK_BTN_TEXT, "Next Month", Const.PB_PAYLOAD_PRODUCT_RELEASE_30_DAYS),
                                build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=2)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_60_DAYS),
                                build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=3)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_90_DAYS),
                                build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=4)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_120_DAYS)
                            ] + cancel_entry_quick_reply()
                        )

                    else:
                        send_text(recipient_id, "Enter a valid price in USD (example 78.00)", cancel_entry_quick_reply())


                elif product.creation_state == 4 and product.type_id == Const.PRODUCT_TYPE_PHYSICAL:
                    if re.search(r'[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&\/=]*)$', message_text) is None:
                        send_text(recipient_id, "Invalid URL, try again", cancel_entry_quick_reply())

                    else:
                        product.physical_url = message_text
                        product.creation_state = 5
                        db.session.commit()

                        send_text(
                            recipient_id=recipient_id,
                            message_text="Enter some category tags separated by spaces or tap Skip",
                            quick_replies=[
                                build_quick_reply(Const.KWIK_BTN_TEXT, "Skip", Const.PB_PAYLOAD_PRODUCT_TAG_SKIP)
                            ] + cancel_entry_quick_reply()
                        )

                elif product.creation_state == 5:
                    product.creation_state = 6
                    product.tags = message_text
                    db.session.commit()


                    send_text(recipient_id, "Here's what your product will look like:")
                    send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_PREVIEW)

                #-- entered text at wrong step
                else:
                    handle_wrong_reply(recipient_id)

                return "OK", 200

            else:
                product = Product.query.filter(Product.storefront_id == storefront.id).filter(Product.broadcast_message == "_{PENDING}_").first()
                if product is not None:
                    product.broadcast_message = message_text
                    db.session.commit()

                    try:
                        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('UPDATE `products` SET `broadcast_message` = %s WHERE `storefront_id` = %s;', (product.broadcast_message, product.storefront_id))
                            cur.execute('UPDATE `subscriptions` SET `broadcast` = 1 WHERE `storefront_id` = %s;', (product.storefront_id,))
                            conn.commit()

                    except mysql.Error, e:
                        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                    finally:
                        if conn:
                            conn.close()

                    send_text(recipient_id, "Great! Your message will be sent to your customers shortly.")
                    send_admin_carousel(recipient_id)

                else:
                    welcome_message(recipient_id, Const.CUSTOMER_REFERRAL, message_text)

        else:
            #-- look for in-progress storefront creation
            storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state < 4).first()
            if storefront is not None:

                #-- name submitted
                if storefront.creation_state == 0:
                    try:
                        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('SELECT `id` FROM `storefronts` WHERE `display_name` = %s AND `enabled` = 1;', (message_text,))
                            row = cur.fetchone()

                            if row is None:
                                storefront.creation_state = 1
                                storefront.display_name = message_text
                                storefront.name = re.sub(Const.IGNORED_NAME_PATTERN, "", message_text.encode('ascii', 'ignore'))
                                storefront.prebot_url = "http://prebot.me/{storefront_name}".format(storefront_name=storefront.name)
                                db.session.commit()

                            send_text(recipient_id, "That name is already taken, please choose another" if row is not None else "Explain what you are making or selling.", cancel_entry_quick_reply())

                    except mysql.Error, e:
                        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                    finally:
                        if conn:
                            conn.close()


                #-- description entered
                elif storefront.creation_state == 1:
                    storefront.creation_state = 2
                    storefront.description = message_text
                    db.session.commit()

                    send_text(recipient_id, "Upload a Shopbot profile image.", cancel_entry_quick_reply())

                #-- entered text at wrong step
                else:
                    handle_wrong_reply(recipient_id)

                return "OK", 200

            else:
                welcome_message(recipient_id, Const.CUSTOMER_REFERRAL, message_text)


def handle_wrong_reply(recipient_id):
    logger.info("handle_wrong_reply(recipient_id=%s)" % (recipient_id))

    #-- payment creation in-progress
    payment = Payment.query.filter(Payment.fb_psid == recipient_id).first()
    if payment is not None:
        if payment.source == Const.PAYMENT_SOURCE_CREDIT_CARD and payment.creation_state < 6:
            add_cc_payment(recipient_id)

        elif payment.source == Const.PAYMENT_SOURCE_BITCOIN:
            send_text(recipient_id, "Invalid bitcoin address, it needs to start w/ 1 or 3, and be between 25 & 34 characters long.", quick_replies=cancel_entry_quick_reply())

        elif payment.source == Const.PAYMENT_SOURCE_PAYPAL:
            send_text(recipient_id, "Invalid email address, try again", cancel_entry_quick_reply())

        return "OK", 200

    #-- storefront creation in-progress
    storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state < 4).first()
    if storefront is not None:
        send_text(recipient_id, "Incorrect response!")
        if storefront.creation_state == 0:
            send_text(recipient_id, "Give your Shopbot a name.", cancel_entry_quick_reply())

        elif storefront.creation_state == 1:
            send_text(recipient_id, "Explain what you are making or selling.", cancel_entry_quick_reply())

        elif storefront.creation_state == 2:
            send_text(recipient_id, "Upload a Shopbot profile image.", cancel_entry_quick_reply())

        elif storefront.creation_state == 3:
            send_text(recipient_id, "Here's what your Shopbot will look like:")
            send_storefront_card(recipient_id, storefront.id, Const.CARD_TYPE_STOREFRONT_PREVIEW)

        return "OK", 200

    #-- product creation in progress
    else:
        storefront_query = db.session.query(Storefront.id).filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).subquery('storefront_query')
        product = Product.query.filter(Product.storefront_id.in_(storefront_query)).filter(Product.creation_state < 7).first()
        if product is not None:
            send_text(recipient_id, "Incorrect response!")
            if product.creation_state == 0:
                send_text(recipient_id, "Upload a photo or video of what you are selling.", cancel_entry_quick_reply())

            elif product.creation_state == 1:
                send_text(recipient_id, "Give your product a title.", cancel_entry_quick_reply())

            elif product.creation_state == 2:
                send_text(recipient_id, "Enter the price of {product_name} in USD. (example 78.00)".format(product_name=product.display_name_utf8), cancel_entry_quick_reply())

            elif product.creation_state == 3:
                send_text(
                    recipient_id=recipient_id,
                    message_text="Select a date the product will be available.",
                    quick_replies=[
                        build_quick_reply(Const.KWIK_BTN_TEXT, "Right Now", Const.PB_PAYLOAD_PRODUCT_RELEASE_NOW),
                        build_quick_reply(Const.KWIK_BTN_TEXT, "Next Month", Const.PB_PAYLOAD_PRODUCT_RELEASE_30_DAYS),
                        build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=2)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_60_DAYS),
                        build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=3)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_90_DAYS),
                        build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=4)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_120_DAYS)
                    ] + cancel_entry_quick_reply()
                )

            elif product.creation_state == 4:
                send_text(
                    recipient_id=recipient_id,
                    message_text="Is {product_name} a physical or virtual good?".format(product_name=product.display_name_utf8),
                    quick_replies=[
                        build_quick_reply(Const.KWIK_BTN_TEXT, "Physical", Const.PB_PAYLOAD_PRODUCT_TYPE_PHYSICAL),
                        build_quick_reply(Const.KWIK_BTN_TEXT, "Virtual", Const.PB_PAYLOAD_PRODUCT_TYPE_VIRTUAL)
                    ] + cancel_entry_quick_reply()
                )

            elif product.creation_state == 5:
                send_text(
                    recipient_id=recipient_id,
                    message_text="Enter some category tags separated by spaces or tap Skip",
                    quick_replies=[
                        build_quick_reply(Const.KWIK_BTN_TEXT, "Skip", Const.PB_PAYLOAD_PRODUCT_TAG_SKIP)
                    ] + cancel_entry_quick_reply()
                )

            elif product.creation_state == 6:
                send_text(recipient_id, "Here's what your product will look like:")
                send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_PREVIEW)

    return "OK", 200


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


@app.route('/', methods=['POST'])
def fbbot():

    #if 'delivery' in request.data or 'read' in request.data or 'optin' in request.data:
    #return "OK", 200

    data = request.get_json()

    # logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    # logger.info("[=-=-=-=-=-=-=-[POST DATA]-=-=-=-=-=-=-=-=]")
    # logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    # logger.info(data)
    # logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")

    if data['object'] == "page":
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                sender_id = messaging_event['sender']['id']
                recipient_id = messaging_event['recipient']['id']  # the recipient's ID, which should be your page's facebook ID
                timestamp = messaging_event['timestamp']

                message_id = None
                message_text = None
                quick_reply = None

                # if sender_id == "1214675165306847":
                #     logger.info("-=- BYPASS-USER -=-")
                #     return "OK", 200

                if 'echo' in messaging_event:
                    logger.info("-=- MESSAGE-ECHO -=-")
                    return "OK", 200

                if 'delivery' in messaging_event:
                    # logger.info("-=- DELIVERY-CONFIRM -=-")
                    return "OK", 200

                if 'read' in messaging_event:
                    # logger.info("-=- READ-CONFIRM -=- %s" % (recipient_id))
                    send_tracker(fb_psid=sender_id, category="read-receipt")
                    return "OK", 200

                if 'optin' in messaging_event:
                    # logger.info("-=- OPT-IN -=-")
                    return "OK", 200


                referral = None if 'referral' not in messaging_event else messaging_event['referral']['ref'].encode('ascii', 'ignore')
                if referral is None and 'postback' in messaging_event and 'referral' in messaging_event['postback']:
                    referral = messaging_event['postback']['referral']['ref'].encode('ascii', 'ignore')

                #-- check mysql for user
                customer = sync_user(sender_id, referral)

                #-- entered via url referral
                if referral is not None:
                    if "/flip/" in referral:
                        product = Product.query.filter(Product.name.ilike(referral.split("/")[-1].lower())).filter(Product.creation_state == 7).first()
                        if product is not None:
                            flip_product(customer.fb_psid, product)

                    welcome_message(customer.fb_psid, Const.CUSTOMER_REFERRAL if referral[1:] not in Const.RESERVED_AUTO_GEN_STOREFRONTS else Const.STOREFRONT_AUTO_GEN, referral)
                    return "OK", 200


                #-- users data
                logger.info("\n=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
                logger.info("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
                logger.info("CUSTOMER -->%s" % (customer))
                logger.info("FB_USER -->%s" % (FBUser.query.filter(FBUser.fb_psid == customer.fb_psid).all()))
                logger.info("PURCHASED -->%s" % (Purchase.query.filter(Purchase.customer_id == customer.id).all()))

                #-- storefront & product
                storefront = Storefront.query.filter(Storefront.fb_psid == customer.fb_psid).first()
                product = Product.query.filter(Product.fb_psid == customer.fb_psid).first()
                logger.info("STOREFRONT -->%s" % (storefront))
                logger.info("PRODUCT -->%s" % (product))

                #-- product related
                if storefront is not None and product is not None:
                    logger.info("SUBSCRIPTIONS -->%s" % (db.session.query(Subscription).filter((Subscription.storefront_id == storefront.id) | (Subscription.product_id == product.id)).all()))
                    logger.info("PURCHASES -->%s" % (db.session.query(Purchase).filter((Purchase.storefront_id == storefront.id) | (Purchase.product_id == product.id)).all()))
                logger.info("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
                logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n")



                # #-- lockout if subscriber count > max
                # if storefront is not None and product is not None:
                #     subscriptions_total = db.session.query(Subscription).filter((Subscription.storefront_id == storefront.id) | (Subscription.product_id == product.id)).count()
                #     if Const.SUBSCRIBERS_MAX_FREE_TIER - subscriptions_total <= 0:
                #         product = Product.query.filter(Product.id == 1).first()
                #         if product is not None:
                #             customer.product_id = product.id
                #             db.session.commit()
                #
                #             send_text(customer.fb_psid, "You have reached {max_subscriptions} subscribers and your shop is locked. Please select a payment method. taps.io/lmon8".format(max_subscriptions=Const.SUBSCRIBERS_MAX_FREE_TIER))
                #             send_storefront_card(customer.fb_psid, product.storefront_id, Const.CARD_TYPE_STOREFRONT_ACTIVATE_PRO)
                #         return "OK", 200



                #-- postback response w/ payload
                if 'postback' in messaging_event:
                    payload = messaging_event['postback']['payload']
                    logger.info("-=- POSTBACK RESPONSE -=- (%s)" % (payload))
                    if 'id' in messaging_event:
                        write_message_log(customer.fb_psid, messaging_event['id'], { key : messaging_event[key] for key in messaging_event if key != 'timestamp' })


                    received_payload(customer.fb_psid, payload, Const.PAYLOAD_TYPE_POSTBACK)
                    return "OK", 200


                #-- actual message
                if 'message' in messaging_event:
                    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECEIVED ->%s" % (customer.fb_psid))

                    message = messaging_event['message']
                    message_id = message['mid']

                    #-- insert to log
                    write_message_log(customer.fb_psid, message_id, message)

                    if 'quick_reply' in message:
                        quick_reply = message['quick_reply']['payload']
                        logger.info("QR --> %s" % (quick_reply))
                        received_payload(customer.fb_psid, quick_reply, Const.PAYLOAD_TYPE_QUICK_REPLY)
                        return "OK", 200


                    if 'attachments' in message:
                        for attachment in message['attachments']:
                            if attachment['type'] == "fallback" and 'text' in message:
                                received_text_response(customer.fb_psid, message['text'])

                            else:
                                recieved_attachment(customer.fb_psid, attachment['type'], attachment['payload'])
                        return "OK", 200


                    if 'text' in message:
                        received_text_response(customer.fb_psid, message['text'])
                        return "OK", 200

                else:
                    send_text(customer.fb_psid, Const.UNKNOWN_MESSAGE)

    return "OK", 200


#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#



@app.route('/slack/', methods=['POST'])
def slack():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\»  '/slack/'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form)))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.SLACK_TOKEN:
        channel_id = request.form['channel_id']
        message_text = request.form['text'].replace(request.form['trigger_word'], "")

        if re.search(r'^\ \d+\ .*$', message_text) is not None:
            match = re.match(r'^\ (?P<purchase_id>\d+)\ (?P<message_txt>.*)$', message_text)
            purchase_id = match.group('purchase_id')
            message_txt = match.group('message_txt')

            logger.info("purchase_id=%s\tmessage_txt=%s" % (purchase_id, message_txt))

            purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
            if purchase is not None:
                if message_txt.lower() == "close":
                    route_purchase_dm(channel_id, purchase, Const.DM_ACTION_CLOSE)

                else:
                    route_purchase_dm(channel_id, purchase, Const.DM_ACTION_SEND, message_txt)

            else:
                logger.info("PURCHASE NOT FOUND!!")
                slack_outbound(
                    channel_name = "lemonade-shops",
                    message_text = "Couldn't locate that purchase!",
                    webhook = Const.SLACK_SHOPS_WEBHOOK
                )

        else:
            logger.info("PURCHASE NOT FOUND!!")
            slack_outbound(
                channel_name = "lemonade-shops",
                message_text = "Couldn't locate that purchase!",
                webhook = Const.SLACK_SHOPS_WEBHOOK
            )

    else:
        logger.info("INAVLID TOKEN!!")
        slack_outbound(
            channel_name = "lemonade-shops",
            message_text = "Invalid token!",
            webhook = Const.SLACK_SHOPS_WEBHOOK
        )

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

        customer_id = request.form['user_id']
        product_id = request.form['product_id']

        logger.info("product_id=%s, customer_id=%s" % (product_id, customer_id))

        purchase = Purchase.query.filter(Purchase.customer_id == customer_id).filter(Purchase.product_id == product_id).order_by(Purchase.added.desc()).first()
        if purchase is not None:
            logger.info("purchase=%s", (purchase,))
            purchase.claim_state = 5
            db.session.commit()

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('UPDATE `purchases` SET `claim_state` = 5 WHERE `id` = %s LIMIT 1;', (purchase.id,))
                    conn.commit()

            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

            customer = Customer.query.filter(Customer.id == customer_id).first()
            fb_user = FBUser.query.filter(FBUser.fb_psid == customer.fb_psid).first()
            product = Product.query.filter(Product.id == product_id).first()
            storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()

            slack_outbound(
                channel_name="lemonade-purchases",
                message_text="*{customer}* just purchased _{product_name}_ for ${price:.2f} from _{storefront_name}_ via PayPal.".format(customer=recipient_id if fb_user is None else fb_user.full_name_utf8, product_name=product.display_name_utf8, price=product.price, storefront_name=storefront.display_name_utf8),
                webhook=Const.SLACK_PURCHASES_WEBHOOK
            )

            customer.paypal_name = "_{PENDING}_"
            db.session.commit()
            send_text(customer.fb_psid, "Purchase complete!\nType your trade URL here", cancel_entry_quick_reply())

            # send_text(
            #     recipient_id=customer.fb_psid,
            #     message_text="After completing the PayPal checkout, tap OK",
            #     quick_replies=[
            #         build_quick_reply(Const.KWIK_BTN_TEXT, "OK", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_PAYPAL_PURCHASE_COMPLETE, purchase_id=purchase.id))
            #     ] + cancel_entry_quick_reply()
            # )

    return "OK", 200


#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


@app.route('/', methods=['GET'])
def verify():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= GET --   (%s)->%s" % (request.args.get('hub.mode'), request.args))
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
    data = {
        'recipient'     : {
            'id' : recipient_id
        },
        'sender_action' : "typing_on" if is_typing else "typing_off"
    }

    send_message(json.dumps(data))


def send_text(recipient_id, message_text, quick_replies=None):
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


def send_image(recipient_id, url, attachment_id=None, quick_replies=None):
    send_typing_indicator(recipient_id, True)

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

    if attachment_id is not None:
        data['message']['attachment']['payload'] = { 'attachment_id' : attachment_id }

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
        'message'   : {
            'attachment' : {
                'type'    : "video",
                'payload' : {
                    'url'         : url,
                    'is_reusable' : True
                }
            }
        }
    }

    if attachment_id is not None:
        data['message']['attachment']['payload'] = { 'attachment_id' : attachment_id }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_message(payload):
    logger.info("send_message(payload=%s)" % (payload))

    response = requests.post(
        url = "https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN),
        headers = { 'Content-Type' : "application/json" },
        data = payload
    )
    logger.info("SEND MESSAGE response: %s" % (response.json()))

    return True


def fb_graph_user(recipient_id):
    logger.info("fb_graph_user(recipient_id=%s)" % (recipient_id))

    params = {
        'fields'       : "first_name,last_name,profile_pic,locale,timezone,gender,is_payment_enabled",
        'access_token' : Const.ACCESS_TOKEN
    }
    response = requests.get("https://graph.facebook.com/v2.6/{recipient_id}".format(recipient_id=recipient_id), params=params)
    return None if 'error' in response.json() else response.json()


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


if __name__ == '__main__':
    from gevent import monkey
    monkey.patch_all()

    logger.info("Firin up FbBot using verify token [%s]." % (Const.VERIFY_TOKEN))
    app.run(debug=True)




#-=-# TODO: #-=-#
'''
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    return 'You want path: %s' % path


def get_serializer(secret_key=None):
    return URLSafeSerializer(secret_key=app.secret_key if secret_key is None else secret_key)


def get_activation_link(user):
    s = get_serializer()
    payload = s.dumps(user.id)
    return url_for('activate_user', payload=payload, _external=True)


@app.route('/storefront/activate/<payload>', methods=['POST'])
def activate_user(payload):
    s = get_serializer()

    try:
        user_id = s.loads(payload)

    except BadSignature:
        abort(404)

    user = User.query.get_or_404(user_id)
    user.activate()
    flash('User activated')
    return redirect(url_for('index'))


def redeem_voucher(payload):
    s = get_serializer()
    try:
        user_id, voucher_id = s.loads(payload)
    except BadSignature:
        abort(404)

    user = User.query.get_or_404(user_id)
    voucher = Voucher.query.get_or_404(voucher_id)
    voucher.redeem_for(user)
    flash('Voucher redeemed')
    return redirect(url_for('index'))


def get_redeem_link(user, voucher):
    s = get_serializer()
    payload = s.dumps([user.id, voucher.id])
    return url_for('redeem_voucher', payload=payload,
                   _external=True)


# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#

'''
