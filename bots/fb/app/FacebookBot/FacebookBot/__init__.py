#!/usr/bin/env python
# encoding=utf8

import calendar
import hashlib
import itertools
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
from sqlalchemy import func
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


class QueueIter(object):
    auto_inc_generator = itertools.count(0)
    ind = next(auto_inc_generator)

    def __init(self, offset=1):
        if offset > 1:
            self.auto_inc_generator = itertools.count(offset)
        self.ind = next(self.auto_inc_generator)




class CoerceUTF8(db.TypeDecorator):
    """Safely coerce Python bytestrings to Unicode
    before passing off to the database."""

    impl = db.Unicode

    def process_bind_param(self, value, dialect):
        if isinstance(value, str):
            value = value.decode('utf-8')
        return value


class QueueIndexer(db.Model):
    __tablename__ = "queue_indexer"

    id = db.Column(db.Integer, primary_key=True)
    fb_psid = db.Column(db.String(255))
    added = db.Column(db.Integer)

    def __init__(self, fb_psid):
        self.fb_psid = fb_psid
        self.added = int(time.time())

    def __repr__(self):
        return "<QueueIncrementor id=%s, fb_psid=%s, added=%s>" % (self.id, self.fb_psid, self.added)


class Customer(db.Model):
    __tablename__ = "customers"

    id = db.Column(db.Integer, primary_key=True)
    fb_psid = db.Column(db.String(255))
    fb_name = db.Column(CoerceUTF8)
    email = db.Column(db.String(255))
    referrer = db.Column(db.String(255))
    input_state = db.Column(db.Integer)
    locked = db.Column(db.Integer)
    trade_url = db.Column(db.String(255))
    paypal_name = db.Column(db.String(255))
    paypal_email = db.Column(db.String(255))
    steam_id64 = db.Column(db.String(255))
    kik_name = db.Column(db.String(255))
    bitcoin_addr = db.Column(db.String(255))
    social = db.Column(db.String(255))
    stripe_id = db.Column(db.String(255))
    card_id = db.Column(db.String(255))
    storefront_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    purchase_id = db.Column(db.Integer)
    points = db.Column(db.Integer)
    tokens = db.Column(db.Float)
    added = db.Column(db.Integer)

    def __init__(self, fb_psid, referrer="/"):
        self.fb_psid = fb_psid
        self.referrer = referrer
        self.locked = 1
        self.points = 0
        self.added = int(time.time())

    def __repr__(self):
        return "<Customer id=%s, fb_psid=%s, fb_name=%s, email=%s, bitcoin_addr=%s, referrer=%s, input_state=%s, locked=%s, trade_url=%s, paypal_name=%s, paypal_email=%s, steam_id64=%s, social=%s, storefront_id=%s, product_id=%s, purchase_id=%s, points=%s, tokens=%s, added=%s>" % (self.id, self.fb_psid, self.fb_name, self.email, self.bitcoin_addr, self.referrer, self.input_state, self.locked, self.trade_url, self.paypal_name, self.paypal_email, self.steam_id64, self.social, self.storefront_id, self.product_id, self.purchase_id, self.points, self.tokens, self.added)


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
        return None
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
    image_url = db.Column(db.String(500))
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
    def tag_list_utf8(self):
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
        self.release_date = int(time.time())


    def __repr__(self):
        return "<Product id=%s, fb_psid=%s, storefront_id=%s, type_id=%s, creation_state=%s, name=%s, display_name=%s, description=%s, tags=%s, image_url=%s, video_url=%s, price=%s, prebot_url=%s, views=%s, avg_rating=%.2f, physical_url=%s, release_date=%s, added=%s>" % (self.id, self.fb_psid, self.storefront_id, self.type_id, self.creation_state, self.name, self.display_name_utf8, self.description_utf8, self.tag_list_utf8, self.image_url, self.video_url, self.price, self.prebot_url, self.views, self.avg_rating, self.physical_url, self.release_date, self.added)


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
    logo_url = db.Column(db.String(500))
    video_url = db.Column(db.String(255))
    prebot_url = db.Column(db.String(255))
    giveaway = db.Column(db.Integer)
    views = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, fb_psid, type_id=Const.STOREFRONT_TYPE_CUSTOM):
        self.fb_psid = fb_psid
        self.creation_state = 0
        self.type_id = type_id
        self.giveaway = 0
        self.views = 0

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


def fb_psid_profile(recipient_id):
    logger.info("fb_psid_profile(recipient_id=%s)" % (recipient_id))

    fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
    return recipient_id if fb_user is None else fb_user


def queue_position(recipient_id, offset=0):
    logger.info("queue_position(recipient_id=%s, offset=%s)" % (recipient_id, offset))

    queue_indexer = QueueIndexer.query.filter(QueueIndexer.fb_psid == recipient_id).first()
    if queue_indexer is None:
        queue_indexer = QueueIndexer(recipient_id)
        db.session.add(queue_indexer)
        db.session.commit()

        if queue_indexer.id < offset:
            while queue_indexer.id < offset:
                queue_indexer.id += random.gauss(offset, offset ** 0.5)

    return queue_indexer.id + offset

# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #

    query = db.session.query(
        func.sum(Customer.id, type=db.Integer).label('summation'),
        func.count().label('records')
    ).all()


    summation, total = query[0]


    # logger.info("SQLAlchemy WTF func subquery summation_query=%s, summation=%s, summation/scalar()=%s", (summation_query, summation, summation.scalar()))
    #logger.info("\n\n[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]\n]:::::]]]] WTF ::::::] --- query=%s, adj=%s\n[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]\n\n\n", (query, len(query),))
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]\n::::::] --- query=%s, len(query)=1" % (query,))
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]\n::::::] --- query[0]=%s" % (query[0],))
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]\n::::::] --- summation=%s, records=%s" % (summation, total))

    for res in query:
        logger.info(res)


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #
# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #



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

    conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
            if customer is None:
                customer = Customer(fb_psid=recipient_id, referrer=deeplink)
                db.session.add(customer)
            db.session.commit()

            #-- check db for existing user
            cur.execute('SELECT `id` FROM `users` WHERE `fb_psid` = %s LIMIT 1;', (recipient_id,))
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
                customer.referrer = deeplink
                db.session.commit()

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


def flip_wins_for_interval(recipient_id, interval=24):
    logger.info("flip_wins_for_interval(recipient_id=%s, interval=%s)" % (recipient_id, interval))

    total = 0
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    if customer is not None:
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT COUNT(*) AS `tot` FROM `flip_wins` WHERE `user_id` = %s AND `added` >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL %s HOUR);', (customer.id, interval))
                row = cur.fetchone()
                total = row['tot']

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

    return total


def add_points(recipient_id, amount=0):
    logger.info("add_points(recipient_id=%s, amount=%s)" % (recipient_id, amount))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    if customer is not None:
        fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('INSERT INTO `points` (`id`, `user_id`, `fb_psid`, `full_name`, `amount`, `added`) VALUES (NULL, %s, %s, %s, %s, UTC_TIMESTAMP);', (customer.id, recipient_id, "" if fb_user is None else fb_user.full_name_utf8, amount))
                cur.execute('UPDATE `users` SET `points` = `points` + %s WHERE `id` = %s LIMIT 1;', (amount, customer.id))
                conn.commit()
                cur.execute('SELECT `points` FROM `users` WHERE `id` = %s LIMIT 1;', (customer.id,))
                row = cur.fetchone()
                customer.points = 0 if row is None else int(row['points'])
                db.session.commit()

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        # send_tracker(fb_psid=recipient_id, category="add-points", action="{fb_psid} / {full_name}".format(fb_psid=recipient_id, full_name="N/A" if fb_user is None else fb_user.full_name_utf8), label=customer.points)


def customer_points_rank(recipient_id):
    logger.info("customer_points_rank(recipient_id=%s)" % (recipient_id,))

    rank = 0
    try:
        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('SELECT `fb_psid`, `points` FROM `users` ORDER BY `points` DESC;')
            cnt = 1
            for row in cur.fetchall():
                if row['fb_psid'] == recipient_id:
                   rank = cnt
                cnt += 1

    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

    return (rank, customer.points)


def points_per_dollar(amount=0):
    logger.info("points_per_dollar(amount=%s)" % (amount,))
    return locale.format('%d', int(amount * Const.POINTS_PER_DOLLAR), grouping=True)


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


def flip_product(recipient_id, product):
    logger.info("flip_product(recipient_id=%s, product=%s)" % (recipient_id, product))
    send_tracker(fb_psid=recipient_id, category="flip", label=product.display_name_utf8)

    storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    if customer is not None and customer.referrer is not None and re.search(r'^\/flip\/([A-Za-z0-9_\.\-]+)$', customer.referrer) is not None:
        customer.referrer = re.sub(r'^\/flip\/([A-Za-z0-9_\.\-]+)$', r'/\1', customer.referrer)
        db.session.commit()

    outcome = random.uniform(0, 1) < (1 / float(5)) if "disneyjp" not in product.tag_list_utf8 else True
    send_tracker(fb_psid=recipient_id, category="%s" % ("win" if outcome is True else "loss",), label=product.display_name_utf8)

    if "disneyjp" in product.tag_list_utf8:
        send_image(recipient_id, "https://i.imgur.com/rsiKG84.gif", "259175247891645")

    send_image(recipient_id, Const.IMAGE_URL_FLIP_START, "248316088977561")
    add_points(recipient_id, Const.POINT_AMOUNT_FLIP_STOREFRONT_WIN)
    if outcome is True:  # or (recipient_id in Const.ADMIN_FB_PSIDS and random.uniform(0, 100) < 80):
        send_tracker(fb_psid=recipient_id, category="transaction", label="win")
        code = hashlib.md5(str(time.time()).encode()).hexdigest()[-4:].upper()

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('INSERT INTO `flip_wins` (`id`, `user_id`, `storefront_id`, `product_id`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, 0 if storefront is None else storefront.id, product.id))
                conn.commit()
                cur.execute('SELECT @@IDENTITY AS `id` FROM `flip_wins`;')

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


        #send_video(recipient_id, "https://scard.tv/videos/output_cCFqWP.mp4", "247917669017403")
        time.sleep(0.875)

        fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
        slack_outbound(
            channel_name=Const.SLACK_ORTHODOX_CHANNEL,
            message_text="*{fb_name}* ({fb_psid}) just won {points} Lemonade Pts by flipping {product_name}.".format(fb_name=recipient_id if fb_user is None else fb_user.full_name_utf8, fb_psid=recipient_id, points=Const.POINT_AMOUNT_FLIP_STOREFRONT_WIN, product_name=product.display_name_utf8)
        )

    try:
        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('INSERT INTO `user_flips` (`id`, `user_id`, `product_id`, `won`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, product.id, 0 if outcome is False else 1))
            conn.commit()
            cur.execute('SELECT @@IDENTITY AS `id` FROM `user_flips`;')

    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


    return outcome


def view_product(recipient_id, product, welcome_entry=False):
    logger.info("view_product(recipient_id=%s, product=%s, entry=%s)" % (recipient_id, product, welcome_entry))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    customer.referrer = None
    db.session.commit()

    if product is not None:
        # if product.price >= 1.50 and customer.points < 1.50 * Const.POINTS_PER_DOLLAR:
        #     send_text(recipient_id, "You need at least {points} Points to have access to this item.".format(points=locale.format('%d', int(10.00 * Const.POINTS_PER_DOLLAR), grouping=True)), main_menu_quick_replies(recipient_id))
        #     return "OK", 200

        customer.product_id = product.id
        db.session.commit()
        # send_tracker(fb_psid=recipient_id, category="view-shop", label=product.display_name_utf8)
        increment_shop_views(recipient_id, product.id)

        add_points(recipient_id, Const.POINT_AMOUNT_VIEW_PRODUCT)

        # if product.video_url is not None and product.video_url != "":
        #     send_video(recipient_id, product.video_url, product.attachment_id)

        send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_ENTRY if welcome_entry is True else Const.CARD_TYPE_PRODUCT_CHECKOUT)

        if "disneyjp" in product.tag_list_utf8:
            customer.paypal_email = "_{PENDING}_"
            db.session.commit()
            send_text(recipient_id, "You WON! 100x Ruby Pack in Disney's Tsum Tsum.\n\nPlease enter your Disney Tsum Tsum username for the item to transfer.", cancel_entry_quick_reply())


def purchase_points_pak(recipient_id, amount):
    logger.info("purchase_points_pak(recipient_id=%s, amount=%s)" % (recipient_id, amount))

    if amount == 5:
        product_id = 2

    elif amount == 10:
        product_id = 3

    elif amount == 20:
        product_id = 4

    else:
        product_id = 0

    product = Product.query.filter(Product.id == product_id).first()
    if product is not None:
        customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
        storefront = Storefront.query.filter(Storefront.id == 1).first()

        try:
            Payment.query.filter(Payment.fb_psid == recipient_id).delete()
            db.session.commit()
        except:
            db.session.rollback()

        purchase = Purchase(customer.id, storefront.id, product.id, 3)
        purchase.claim_state = 1

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
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

        send_message(json.dumps(build_standard_card(
            recipient_id=recipient_id,
            title=product.display_name_utf8,
            subtitle=product.description,
            image_url=product.image_url,
            buttons=[
                build_button(Const.CARD_BTN_URL_TALL, caption="${price:.2f} Confirm".format(price=product.price), url="http://lmon.us/paypal/{product_id}/{user_id}".format(product_id=product.id, user_id=customer.id))
            ]
        )))

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
                    # send_tracker(fb_psid=recipient_id, category="purchase-complete-bitcoin")

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
                        # send_tracker(fb_psid=recipient_id, category="purchase-complete-stripe")

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


                elif source == Const.PAYMENT_SOURCE_FB:
                    purchase = Purchase(customer.id, storefront.id, product.id, 5)
                    purchase.claim_state = 0

                    try:
                        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('INSERT INTO `purchases` (`id`, `user_id`, `product_id`, `type`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, product.id, 4))
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

                    send_tracker(fb_psid=recipient_id, category="fb-purchase")
                    send_tracker(fb_psid=recipient_id, category="transaction", label="purchase")

                    storefront_owner = Customer.query.filter(Customer.fb_psid == storefront.fb_psid).first()
                    if storefront_owner is not None:
                        send_image(storefront.fb_psid, Const.IMAGE_URL_PRODUCT_PURCHASED)
                        route_purchase_dm(recipient_id, purchase, Const.DM_ACTION_PURCHASE, "Purchase made for {product_name} at {pacific_time}.".format(product_name=product.display_name_utf8, pacific_time=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%I:%M%P %Z').lstrip("0")))

                        return True

                elif source == Const.PAYMENT_SOURCE_PAYPAL:
                    purchase = Purchase(customer.id, storefront.id, product.id, 3)
                    purchase.claim_state = 0

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

                    send_tracker(fb_psid=recipient_id, category="paypal-purchase")
                    send_tracker(fb_psid=recipient_id, category="transaction", label="paypal")

                    storefront_owner = Customer.query.filter(Customer.fb_psid == storefront.fb_psid).first()
                    if storefront_owner is not None:
                        send_image(storefront.fb_psid, Const.IMAGE_URL_PRODUCT_PURCHASED)
                        send_message(json.dumps(build_standard_card(
                            recipient_id=recipient_id,
                            title=product.display_name_utf8,
                            subtitle="${price:.2f}".format(price=product.price),
                            image_url=product.image_url,
                            buttons=[
                                build_button(Const.CARD_BTN_URL_TALL, caption="${price:.2f} Confirm".format(price=product.price), url="http://lmon.us/paypal/{product_id}/{user_id}".format(product_id=product.id, user_id=customer.id))
                            ]
                        )))

                        route_purchase_dm(recipient_id, purchase, Const.DM_ACTION_PURCHASE, "Purchase made for {product_name} at {pacific_time}.".format(product_name=product.display_name_utf8, pacific_time=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%I:%M%P %Z').lstrip("0")))

                        return True

                elif source == Const.PAYMENT_SOURCE_POINTS:
                    logger.info("PURCHASE -----------> customer.points=%s, price=%s" % (customer.points, product.price * Const.POINTS_PER_DOLLAR))
                    if customer.points >= product.price * Const.POINTS_PER_DOLLAR:
                        purchase = Purchase(customer.id, storefront.id, product.id, 4)
                        purchase.claim_state = 0

                        try:
                            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                            with conn:
                                cur = conn.cursor(mysql.cursors.DictCursor)
                                cur.execute('INSERT INTO `purchases` (`id`, `user_id`, `product_id`, `type`, `paid`, `added`) VALUES (NULL, %s, %s, %s, 1, UTC_TIMESTAMP());', (customer.id, product.id, 4))
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

                        send_tracker(fb_psid=recipient_id, category="points-purchase")
                        send_tracker(fb_psid=recipient_id, category="transaction", label="points")
                        add_points(recipient_id, -int(product.price * Const.POINTS_PER_DOLLAR))

                        fb_user = FBUser.query.filter(FBUser.fb_psid == customer.fb_psid).first()
                        slack_outbound(
                            channel_name="lmon8-001",
                            message_text="*{customer}* ({fb_psid}) just purchased _{product_name}_ for {points} pts.\nTrade URL: {trade_url}".format(customer=customer.fb_psid if fb_user is None else fb_user.full_name_utf8, fb_psid=customer.fb_psid, product_name=product.display_name_utf8, points=locale.format('%d', int(product.price * Const.POINTS_PER_DOLLAR), grouping=True), trade_url=customer.trade_url or "N/A"),
                            webhook=Const.SLACK_PURCHASES_WEBHOOK
                        )
                        return True

                    else:
                        return False
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

    if customer.kik_name == "_{PENDING}_":
        customer.kik_name = None

    if customer.bitcoin_addr == "_{PENDING}_":
        customer.bitcoin_addr = None

    if customer.fb_name == "_{PENDING}_":
        customer.fb_name = None

    if customer.trade_url == "_{PENDING}_":
        customer.trade_url = None

    if customer.social == "_{PENDING}_":
        customer.social = None

    if customer.referrer == "/pizza":
        customer.referrer = None

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
    fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()

    if entry_type == Const.ENTRY_MARKETPLACE_GREETING:
        # send_image(recipient_id, Const.IMAGE_URL_GREETING)
        send_text(recipient_id, Const.ORTHODOX_GREETING.format(first_name=fb_user.first_name))
        send_admin_carousel(recipient_id)

    elif entry_type == Const.ENTRY_STOREFRONT_AUTO_GEN and deeplink.split("/")[-1].lower() in Const.RESERVED_AUTO_GEN_STOREFRONTS.lower():
        storefront, product = autogen_storefront(recipient_id, deeplink.split("/")[-1])

        # send_image(recipient_id, Const.IMAGE_URL_GREETING)
        send_text(recipient_id, Const.ORTHODOX_GREETING.format(first_name=fb_user.first_name))

        if storefront is not None and product is not None:
            send_text(recipient_id, "{storefront_name} created.\n{prebot_url}".format(storefront_name=storefront.display_name_utf8, prebot_url=product.messenger_url), main_menu_quick_replies(recipient_id))

        else:
            send_text(recipient_id, "{storefront_name} is not available to resell at this time.".format(storefront_name=re.match(r'^AUTO_GEN_STOREFRONT\-(?P<key>.+)$', payload).group('key')), main_menu_quick_replies(recipient_id))

        slack_outbound(
            channel_name=Const.SLACK_ORTHODOX_CHANNEL,
            message_text="{fb_user} arrived to autogen {storefront_name} via deeplink {slug_trigger}".format(fb_user=fb_psid_profile(recipient_id).full_name_utf8, storefront_name=re.match(r'^AUTO_GEN_STOREFRONT\-(?P<key>.+)$', payload).group('key'), deeplink=deeplink)
        )

    elif entry_type == Const.ENTRY_PRODUCT_REFERRAL:
        product = Product.query.filter(Product.name.ilike(deeplink.split("/")[-1].lower())).filter(Product.creation_state == 7).first()
        if product is not None:
            storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()

            if "disneyjp" in product.tag_list_utf8:
                customer.product_id = product.id
                db.session.commit()
                send_text(recipient_id, "Please enter passcode.", cancel_entry_quick_reply())

            else:
                if "/flip/" in deeplink:
                    send_text(recipient_id, "Loading {storefront_name}…".format(storefront_name=product.display_name_utf8 if storefront is None else storefront.display_name_utf8))
                    flip_product(recipient_id, product)

                if "gamebots-points" in product.tag_list_utf8:
                    customer.product_id = product.id
                    db.session.commit()
                    send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_CHECKOUT)

                else:
                    view_product(recipient_id, product, True)

            slack_outbound(
                channel_name=Const.SLACK_ORTHODOX_CHANNEL,
                message_text="{fb_user} arrived via referral {deeplink}".format(fb_user=fb_psid_profile(recipient_id).full_name_utf8, deeplink=deeplink)
            )

        else:
            send_text(recipient_id, Const.ORTHODOX_GREETING.format(first_name="there" if fb_user is None else fb_user.first_name))
            send_admin_carousel(recipient_id)

    elif entry_type == Const.ENTRY_USER_REFERRAL:
        ref_customer = Customer.query.filter(Customer.fb_psid == re.match(r'^\/ref\/(?P<fb_psid>\d+)$', deeplink or "/").group('fb_psid')).first()
        if ref_customer is not None:
            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('SELECT `id` FROM `referral_entries` WHERE `source_id` = %s AND `entry_id` = %s LIMIT 1;', (ref_customer.id, customer.id))
                    if cur.fetchone() is None:
                        if customer.fb_psid != ref_customer.fb_psid:
                            cur.execute('INSERT INTO `referral_entries` (`id`, `source_id`, `entry_id`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());', (ref_customer.id, customer.id))
                            conn.commit()
                            send_text(recipient_id, "You added {points} Pts for entering a referral".format(points=Const.POINT_AMOUNT_REFFERAL), main_menu_quick_replies(recipient_id))
                            send_text(ref_customer.fb_psid, "{points} Pts have been added because someone entered your referral code!".format(points=Const.POINT_AMOUNT_REFFERAL_OWNER), main_menu_quick_replies(recipient_id))
                            add_points(recipient_id, Const.POINT_AMOUNT_REFFERAL)
                            add_points(ref_customer.fb_psid, Const.POINT_AMOUNT_REFFERAL_OWNER)

                        else:
                            send_text(recipient_id, "You cannot enter your own referral code", main_menu_quick_replies(recipient_id))

                    else:
                        send_text(recipient_id, "You already entered that referral code", main_menu_quick_replies(recipient_id))


            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

        else:
            send_text(recipient_id, "Couldn't locate that referral code, try another", main_menu_quick_replies(recipient_id))

    elif entry_type == Const.ENTRY_GIVEAWAY_REFERRAL:
        # send_tracker(fb_psid=recipient_id, category="giveaway-{source}".format(source=re.match(r'^\/giveaway\/(?P<source>(twitter)|(snapchat)|(discord))$', deeplink or "/").group('source')))

        if customer.points < Const.GIVEAWAY_POINT_THRESHOLD:
            send_text(recipient_id, "You must have at least {points} pts to enter the daily givaway.".format(points=locale.format('%d', Const.GIVEAWAY_POINT_THRESHOLD, grouping=True)), main_menu_quick_replies(recipient_id))

        else:
            product_name = None
            image_url = None
            total = 0
            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('SELECT `id` FROM `giveaways` WHERE `fb_psid` = %s AND `added` >= UTC_DATE() LIMIT 1;', (recipient_id,))

                    if cur.fetchone() is None:
                        cur.execute('INSERT INTO `giveaways` (`id`, `user_id`, `fb_psid`, `source`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, customer.fb_psid, re.match(r'^\/giveaway(?P<source>(\/twitter)|(\/snapchat)|(\/discord))?$', deeplink or "/").group('source') or "lmon8"))
                        conn.commit()

                    cur.execute('SELECT COUNT(*) AS `total` FROM `giveaways` WHERE `added` >= UTC_DATE();')
                    total = max(0, cur.fetchone()['total'] - 1)

                    with open("/var/www/FacebookBot/FacebookBot/data/txt/giveaways.txt") as fp:
                        for i, line in enumerate(fp):
                            if i == datetime.now().day:
                                product_name = line.split(",")[0]
                                image_url = line.split(",")[-1]
                                break

            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()


            send_text(recipient_id, "You have completed a giveaway entry with {total} other player{suff}. You will be messaged here when the winner is selected.\n\nToday's extra item is:\n{product_name}".format(total=locale.format('%d', total, grouping=True), suff="" if total == 1 else "s", product_name=product_name), main_menu_quick_replies(recipient_id))
            send_image(customer.fb_psid, image_url, quick_replies=main_menu_quick_replies(recipient_id))
            send_tracker(fb_psid=customer.fb_psid, category="transaction", label="giveaway")
            send_tracker(fb_psid=customer.fb_psid, category="giveaway", label=product_name)


    elif entry_type == Const.ENTRY_ICO_REFERRAL:
        send_ico_info(recipient_id)

    else:
        send_admin_carousel(recipient_id)



def clone_storefront(recipient_id, storefront_id):
    logger.info("clone_storefront(recipient_id=%s, storefront_id=%s)" % (recipient_id, storefront_id))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront_ref = Storefront.query.filter(Storefront.id == storefront_id).first()
    if storefront_ref is not None:
        product_ref = Product.query.filter(Product.storefront_id == storefront_ref.id).first()
        if product_ref is not None:
            if Storefront.query.filter(Storefront.fb_psid == recipient_id).count() > 0:
                for storefront in Storefront.query.filter(Storefront.fb_psid == recipient_id):
                    if storefront is not None:
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

                try:
                    Product.query.filter(Product.fb_psid == recipient_id).delete()
                    db.session.commit()
                except:
                    db.session.rollback()

        if storefront_ref is not None and product_ref is not None:
            storefront_name = "{storefront_name} - {fb_psid}".format(storefront_name=re.match('^(?P<storefront_name>.*)\ \-\ \d{4}$', storefront_ref.display_name).group('storefront_name'), fb_psid=recipient_id[-4:])
            product_name = storefront_name

            storefront = Storefront(recipient_id)
            storefront.name = re.sub(Const.IGNORED_NAME_PATTERN, "", storefront_name.encode('ascii', 'ignore'))
            storefront.display_name = storefront_name
            storefront.description = storefront_ref.description
            storefront.logo_url = storefront_ref.logo_url
            storefront.prebot_url = "http://prebot.me/{storefront_name}".format(storefront_name=storefront.name)
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
            product.name = re.sub(Const.IGNORED_NAME_PATTERN, "", product_name.encode('ascii', 'ignore'))
            product.display_name = product_name
            product.release_date = calendar.timegm((datetime.utcnow() + relativedelta(months=0)).replace(hour=0, minute=0, second=0, microsecond=0).utctimetuple())
            product.description = "For sale starting on {release_date}".format(release_date=datetime.utcfromtimestamp(product.release_date).strftime('%a, %b %-d'))
            product.type_id = product_ref.type_id
            product.image_url = product_ref.image_url
            product.video_url = product_ref.video_url
            product.attachment_id = product_ref.attachment_id
            product.prebot_url = "http://prebot.me/{product_name}".format(product_name=product.name)
            product.price = product_ref.price
            product.tags = "autogen-resell {tags}".format(tags=product_ref.tags)
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

            # send_tracker(fb_psid=recipient_id, category="resell", label=product.display_name_utf8)

            return (storefront, product)

    return (None, None)


def autogen_template_storefront(recipient_id, name_prefix):
    logger.info("autogen_template_storefront(recipient_id=%s, name_prefix=%s)" % (recipient_id, name_prefix))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    templates = {
        #-- latest carousel templates
        'm4a4desolatespace' : {
            'type_id'       : Const.PRODUCT_TYPE_GAME_ITEM,
            'title'         : "M4A4 | Desolate Space",
            'description'   : "CSGO Item",
            'price'         : 11.50,
            'image_url'     : "https://i.imgur.com/gglfp8g.png",
            'video_url'     : None,
            'attachment_id' : None,
            'tags'          : "autogen-carousel"
        },
        'sxyhxysbodyarmor': {
            'type_id'      : Const.PRODUCT_TYPE_GAME_ITEM,
            'title'        : "Sxyhxy's Body Armor",
            'description'  : "H1Z1 Item",
            'price'        : 3.45,
            'image_url'    : "https://i.imgur.com/h0noHDl.png",
            'video_url'    : None,
            'attachment_id': None,
            'tags'         : "autogen-carousel"
        },
        'mac10neonrider': {
            'type_id'      : Const.PRODUCT_TYPE_GAME_ITEM,
            'title'        : "MAC-10 | Neon Rider",
            'description'  : "CSGO Item",
            'price'        : 2.88,
            'image_url'    : "https://i.imgur.com/UAEGI9p.png",
            'video_url'    : None,
            'attachment_id': None,
            'tags'         : "autogen-carousel"
        },
        'p2000imperialdragon': {
            'type_id'      : Const.PRODUCT_TYPE_GAME_ITEM,
            'title'        : "P2000 Imperial Dragon",
            'description'  : "CSGO Item",
            'price'        : 3.45,
            'image_url'    : "https://i.imgur.com/bqvhFIt.png",
            'video_url'    : None,
            'attachment_id': None,
            'tags'         : "autogen-carousel"
        },
        'clawsofthebloodmoon': {
            'type_id'      : Const.PRODUCT_TYPE_GAME_ITEM,
            'title'        : "Claws of the Blood Moon",
            'description'  : "Dota 2 Item",
            'price'        : 12.65,
            'image_url'    : "https://i.imgur.com/Mei2qZT.png",
            'video_url'    : None,
            'attachment_id': None,
            'tags'         : "autogen-carousel"
        },
        'm4a1shyperbeast': {
            'type_id'      : Const.PRODUCT_TYPE_GAME_ITEM,
            'title'        : "M4A1-S | Hyper Beast",
            'description'  : "CSGO Item",
            'price'        : 13.80,
            'image_url'    : "https://i.imgur.com/FP7wGYk.png",
            'video_url'    : None,
            'attachment_id': None,
            'tags'         : "autogen-carousel"
        },
        'gamebotsmysteryflip': {
            'type_id'      : Const.PRODUCT_TYPE_GAME_ITEM,
            'title'        : "Gamebots Mystery Flip",
            'description'  : "1 Flip High Tier Item",
            'price'        : 3.44,
            'image_url'    : "https://i.imgur.com/lGxBTQR.png",
            'video_url'    : None,
            'attachment_id': None,
            'tags'         : "autogen-carousel bonus-flip"
        }
    }

    if name_prefix.lower() == "autogen":
        name_prefix = random.choice(templates.keys())

    if name_prefix.lower() in templates:
        template = templates[name_prefix.lower()]

        if Storefront.query.filter(Storefront.fb_psid == recipient_id).count() > 0:
            for storefront in Storefront.query.filter(Storefront.fb_psid == recipient_id):
                #send_text(recipient_id, "{storefront_name} has been removed.".format(storefront_name=storefront.display_name_utf8))

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


        storefront_name = "{name_prefix} - {fb_psid}".format(name_prefix=template['title'], fb_psid=recipient_id[-4:])
        product_name = storefront_name

        storefront = Storefront(recipient_id)
        storefront.name = re.sub(Const.IGNORED_NAME_PATTERN, "", storefront_name.encode('ascii', 'ignore'))
        storefront.display_name = storefront_name
        storefront.description = template['description']
        storefront.logo_url = template['image_url']
        storefront.prebot_url = "http://prebot.me/{storefront_name}".format(storefront_name=storefront.name)
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
        product.name = re.sub(Const.IGNORED_NAME_PATTERN, "", product_name.encode('ascii', 'ignore'))
        product.display_name = product_name
        product.release_date = calendar.timegm((datetime.utcnow() + relativedelta(months=0)).replace(hour=0, minute=0, second=0, microsecond=0).utctimetuple())
        product.description = "For sale starting on {release_date}".format(release_date=datetime.utcfromtimestamp(product.release_date).strftime('%a, %b %-d'))
        product.type_id = template['type_id']
        product.image_url = template['image_url']
        product.video_url = template['video_url']
        product.attachment_id = template['attachment_id']
        product.prebot_url = "http://prebot.me/{product_name}".format(product_name=product.name)
        product.price = template['price']
        product.tags = template['tags']
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

    return (None, None)


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
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Flip", payload=Const.PB_PAYLOAD_RND_FLIP_STOREFRONT)
    ]

    if storefront is None:
        quick_replies.append(build_quick_reply(Const.KWIK_BTN_TEXT, caption="Create Shop", payload=Const.PB_PAYLOAD_BUILD_STOREFRONT))

    quick_replies.append(build_quick_reply(Const.KWIK_BTN_TEXT, caption="Share ({points} Pts)".format(points=Const.POINT_AMOUNT_SHARE_APP), payload=Const.PB_PAYLOAD_SHARE_APP))


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


def point_pak_quick_replies():
    logger.info("point_pak_quick_replies()")

    return [
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="$5 - 100,00 pts", payload=Const.PB_PAYLOAD_PURCHASE_POINTS_PAK_5),
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="$10 - 300,000 pts", payload=Const.PB_PAYLOAD_PURCHASE_POINTS_PAK_10),
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="$20 - 600,000 pts", payload=Const.PB_PAYLOAD_PURCHASE_POINTS_PAK_20)
    ]


def build_button(btn_type, caption="", url=None, payload=None, price=None):
    logger.info("build_button(btn_type=%s, caption=%s, url=%s, payload=%s, price=%s)" % (btn_type, caption, url, payload, price))

    button = None
    if btn_type == Const.CARD_BTN_PAYMENT:
        button = {
            'type'           : "payment",
            'title'          : "Buy",
            'payload'        : Const.PB_PAYLOAD_CHECKOUT_FB,
            'payment_summary': {
                'currency'           : "USD",
                'payment_type'       : "FIXED_AMOUNT",
                'is_test_payment'    : False,
                'merchant_name'      : "Gamebots",
                'requested_user_info': [
                    "contact_name",
                    "contact_email"
                ],
                'price_list'         : [{
                    'label' : "Subtotal",
                    'amount': price
                }]
            }
        }

    elif btn_type == Const.CARD_BTN_POSTBACK:
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


def build_sponsor_element():
    logger.info("build_sponsor_element()")

    return build_card_element(
        title="Flip Shops to Win",
        subtitle="Flip to win Lmon8 PTS",
        image_url=Const.IMAGE_URL_FLIP_SPONSOR_CARD,
        buttons=[
            build_button(Const.CARD_BTN_POSTBACK, caption="Flip Now ({points} Pts)".format(points=Const.POINT_AMOUNT_FLIP_STOREFRONT_WIN), payload=Const.PB_PAYLOAD_RND_FLIP_STOREFRONT)
        ]
    )


def build_featured_storefront_elements(amt=3):
    logger.info("build_featured_storefront_elements(amt=%s)" % (amt,))

    elements = []
    try:
        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `products` WHERE `tags` LIKE %s AND `enabled` = 1 ORDER BY RAND() LIMIT %s;', ("%{tag}%".format(tag="autogen-import"), min(max(amt, 0), 10)))
            for row in cur.fetchall():
                product = Product.query.filter(Product.id == row['id']).first()
                if product is not None:
                    storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
                    if storefront is not None:
                        elements.append(build_card_element(
                            title=storefront.display_name_utf8,
                            subtitle=product.display_name_utf8,
                            image_url=product.image_url,
                            item_url=product.messenger_url,
                            buttons=[
                                build_button(Const.CARD_BTN_POSTBACK, caption="Flip Now", payload="{payload}-{product_id}".format(payload=Const.PB_PAYLOAD_VIEW_PRODUCT, product_id=product.id)),
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

    templates = [{
        'key'      : "GamebotsMysteryFlip",
        'title'    : "Gamebots Mystery Flip",
        'subtitle' : "1 Flip High Tier Item",
        'image_url': "https://i.imgur.com/lGxBTQR.png"
    }]

    try:
        conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            product = None
            while product is None:
                cur.execute('SELECT `id`, `name`, `display_name`, `image_url` FROM `products` WHERE `tags` LIKE %s AND `enabled` = 1 ORDER BY `views` DESC LIMIT 5;', ("%{tag}%".format(tag="autogen-import"),))
                for row in cur.fetchall():
                    if row is not None:
                        product = Product.query.filter(Product.id == row['id']).first()
                        if product is not None:
                            templates.append({
                                'key'       : row['name'][:-4],
                                'title'     : re.sub(r'\ \-\ \d{4}$', "", row['display_name']),
                                'subtitle'  : "CS:GO Item",
                                'image_url' : row['image_url']
                            })

    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    for template in templates:
        elements.append(build_card_element(
            title=template['title'],
            subtitle=template['subtitle'],
            image_url=template['image_url'],
            buttons=[
                build_button(Const.CARD_BTN_POSTBACK, "Resell ({points} Pts)".format(points=locale.format('%d', Const.POINT_AMOUNT_RESELL_STOREFRONT, grouping=True)), payload="{payload}-{key}".format(payload=Const.PB_PAYLOAD_AUTO_GEN_STOREFRONT, key=template['key'])),
                build_button(Const.CARD_BTN_POSTBACK, "View Shop", payload="{payload}-{key}".format(payload=Const.PB_PAYLOAD_SEARCH_STOREFRONT, key=template['key']))
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
            send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_CHECKOUT)

        else:
            send_admin_carousel(recipient_id)
    else:
        send_admin_carousel(recipient_id)


def send_admin_carousel(recipient_id):
    logger.info("send_admin_carousel(recipient_id=%s)" % (recipient_id))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront = Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == 4).first()

    cards = [
    ]

    #-- look for created storefront
    if storefront is None:
        cards.append(build_sponsor_element())

        cards.append(
            build_card_element(
                title="Refer a Friend to Lmon8",
                subtitle="Share your Lmon8 referral URL",
                image_url=Const.IMAGE_URL_REFERRAL_CARD,
                buttons=[
                    build_button(Const.CARD_BTN_POSTBACK, caption="Referral Link", payload=Const.PB_PAYLOAD_REFERRAL_FAQ)
                ]
            )
        )

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

            cards.append(build_sponsor_element())
            cards.append(
                build_card_element(
                    title="Refer a Friend to Lmon8",
                    subtitle="Share your Lmon8 referral URL",
                    image_url=Const.IMAGE_URL_REFERRAL_CARD,
                    buttons=[
                        build_button(Const.CARD_BTN_POSTBACK, caption="Referral Link", payload=Const.PB_PAYLOAD_REFERRAL_FAQ)
                    ]
                )
            )

        else:
            cards.append(build_sponsor_element())
            purchases = Purchase.query.filter(Purchase.storefront_id == storefront.id).all()
            cards.append(
                build_card_element(
                    title="Refer a Friend to Lmon8",
                    subtitle="Share your Lmom8 ID now with Friends",
                    image_url=Const.IMAGE_URL_REFERRAL_CARD,
                    buttons=[
                        build_button(Const.CARD_BTN_POSTBACK, caption="Referral Link", payload=Const.PB_PAYLOAD_REFERRAL_FAQ)
                    ]
                )
            )


    cards.append(
        build_card_element(
            title="Lmon8 ICO",
            subtitle="Tap to learn more about our ICO",
            image_url="https://i.imgur.com/TXBVzcf.png",
            buttons=[
                build_button(Const.CARD_BTN_POSTBACK, caption="Lmon8 ICO", payload=Const.PB_PAYLOAD_ICO)
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
    if product is not None:
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
                            build_button(Const.CARD_BTN_POSTBACK, caption="Rate", payload=Const.PB_PAYLOAD_RATE_PRODUCT)
                        ]
                    )
                )

        data = build_carousel(
            recipient_id = recipient_id,
            cards = elements,
            quick_replies = main_menu_quick_replies(recipient_id)
        )

        send_message(json.dumps(data))


def send_autogen_carousel(recipient_id):
    logger.info("send_autogen_carousel(recipient_id=%s)" % (recipient_id,))

    data = build_carousel(
        recipient_id=recipient_id,
        cards=build_autogen_storefront_elements(recipient_id),
        quick_replies=main_menu_quick_replies(recipient_id)
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


def send_point_pak_carousel(recipient_id):
    logger.info("send_point_pak_carousel(recipient_id=%s)" % (recipient_id,))

    elements = []
    for product_id in range(2, 4):
        product = Product.query.filter(Product.id == 2).first()
        elements.append(
            build_card_element(
                title=product.display_name_utf8,
                subtitle=product.description,
                image_url=product.image_url,
                buttons=[
                    build_button(Const.CARD_BTN_URL_TALL, caption="${price:.2f} Confirm".format(price=product.price), url="http://lmon.us/paypal/{product_id}/{user_id}".format(product_id=product.id, user_id=customer.id))
                ]
            )
        )

    data = build_carousel(
        recipient_id=recipient_id,
        cards=elements,
        quick_replies=main_menu_quick_replies(recipient_id)
    )

    send_message(json.dumps(data))


def send_storefront_card(recipient_id, storefront_id, card_type=Const.CARD_TYPE_STOREFRONT_SHARE):
    logger.info("send_storefront_card(recipient_id=%s, storefront_id=%s, card_type=%s)" % (recipient_id, storefront_id, card_type))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront = Storefront.query.filter(Storefront.id == storefront_id).first()
    product = Product.query.filter(Product.storefront_id == storefront_id).first()

    if storefront is not None:
        if card_type == Const.CARD_TYPE_STOREFRONT_ENTRY:
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

        elif card_type == Const.CARD_TYPE_STOREFRONT_SHARE:
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


def send_product_card(recipient_id, product_id, card_type=Const.CARD_TYPE_PRODUCT_CHECKOUT):
    logger.info("send_product_card(recipient_id=%s, product_id=%s, card_type=%s)" % (recipient_id, product_id, card_type))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    product = Product.query.filter(Product.id == product_id).first()

    data = None
    if product is not None:
        storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()

        if card_type == Const.CARD_TYPE_PRODUCT_ENTRY:
            data = build_standard_card(
                recipient_id = recipient_id,
                title = product.display_name_utf8,
                subtitle ="{description} - ${price:.2f}".format(description=product.description, price=product.price),
                image_url = product.image_url,
                buttons = [
                    build_button(Const.CARD_BTN_POSTBACK, caption="Buy", payload=Const.PB_PAYLOAD_CHECKOUT_PRODUCT),
                    build_button(Const.CARD_BTN_POSTBACK, caption="Share ({points} Pts)".format(points=Const.POINT_AMOUNT_SHARE_APP), payload=Const.PB_PAYLOAD_SHARE_APP),
                    build_button(Const.CARD_BTN_POSTBACK, caption="Resell ({points} Pts)".format(points=locale.format('%d', Const.POINT_AMOUNT_RESELL_STOREFRONT, grouping=True)), payload=Const.PB_PAYLOAD_RESELL_STOREFRONT)
                ],
                quick_replies = main_menu_quick_replies(recipient_id)
            )

        elif card_type == Const.CARD_TYPE_PRODUCT_PREVIEW:
            data = build_standard_card(
                recipient_id = recipient_id,
                title = product.display_name_utf8,
                subtitle = "{description} — ${price:.2f}".format(description=product.description, price=product.price),
                image_url = product.image_url,
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
                    #build_button(Const.CARD_BTN_URL, caption="Flip", url=re.sub(r'\/([A-Za-z0-9_\.\-]+)$', r'/flip/\1', product.messenger_url)),
                    build_button(Const.CARD_BTN_INVITE)
                ],
                quick_replies = main_menu_quick_replies(recipient_id)
            )

        elif card_type == Const.CARD_TYPE_PRODUCT_CHECKOUT:
            data = build_standard_card(
                recipient_id=recipient_id,
                title=product.display_name_utf8,
                subtitle="{points}pts".format(points=points_per_dollar(product.price)),
                image_url=product.image_url,
                item_url=product.messenger_url,
                buttons=[
                    build_button(Const.CARD_BTN_POSTBACK, "Resell ({points} Pts)".format(points=locale.format('%d', Const.POINT_AMOUNT_RESELL_STOREFRONT, grouping=True)), payload=Const.PB_PAYLOAD_RESELL_STOREFRONT),
                    build_button(Const.CARD_BTN_POSTBACK, caption="{points} Points".format(points=points_per_dollar(product.price)), payload=Const.PB_PAYLOAD_CHECKOUT_POINTS),
                    build_button(Const.CARD_BTN_POSTBACK, caption="Share ({points} Pts)".format(points=Const.POINT_AMOUNT_SHARE_APP), payload=Const.PB_PAYLOAD_SHARE_APP)
                ],
                quick_replies=[build_quick_reply(Const.KWIK_BTN_TEXT, caption="Next Shop", payload=Const.PB_PAYLOAD_RND_FLIP_STOREFRONT)] + main_menu_quick_replies(recipient_id)
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
                        build_button(Const.CARD_BTN_URL_TALL, caption="Pay now with PayPal", url="http://lmon.us/paypal/{product_id}/{user_id}".format(product_id=product.id, user_id=customer.id))
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
                    #build_button(Const.CARD_BTN_POSTBACK, caption="Message Owner", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_DM_OPEN, purchase_id=purchase.id))
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

                subtitle = ""
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
        title="Welcome to Lmon8",
        subtitle="The world's largest virtual mall.",
        image_url=Const.IMAGE_URL_SHARE_MESSENGER_CARD,
        item_url="http://m.me/lmon8?ref=/",
        buttons=[
            build_button(Const.CARD_BTN_URL, caption="View Shop", url="http://m.me/lmon8?ref=/"),
            build_button(Const.CARD_BTN_INVITE)
        ],
        quick_replies=main_menu_quick_replies(recipient_id)
    )

    send_message(json.dumps(data))


def send_mystery_flip_card(recipient_id, giveaway=False):
    logger.info("send_mystery_flip_card(recipient_id=%s, giveaway=%s)" % (recipient_id, giveaway))

    bonus_code = "{prefix}{hash}".format(prefix="giveaway-" if giveaway is True else "", hash=hashlib.md5(recipient_id.encode()).hexdigest())
    payload = {
        'token'      : Const.MYSTERY_FLIP_TOKEN,
        'bonus_code' : bonus_code
    }

    response = requests.post("https://gamebot.tv/gamebots/bonus-flip/", data=payload)
    if response.text != "code-exists":
        data = build_standard_card(
            recipient_id=recipient_id,
            title="Gamebots Mystery Flip" if giveaway is False else "Gamebots Giveaway",
            subtitle="1 Flip High Tier Item",
            image_url="https://i.imgur.com/ApmGnSW.png",
            item_url="http://m.me/gamebotsc?ref=/{bonus_code}".format(bonus_code=bonus_code),
            buttons=[
                build_button(Const.CARD_BTN_URL, caption="Activate", url="http://m.me/gamebotsc?ref=/{bonus_code}".format(bonus_code=bonus_code))
            ],
            quick_replies=main_menu_quick_replies(recipient_id)
        )

        send_message(json.dumps(data))

    else:
        send_text(recipient_id, "You can only use one Mystery Flip per day. Your purchase flip may be used in 24 hours.", return_home_quick_reply())


def send_referral_card(recipient_id):
    logger.info("send_referral_card(recipient_id=%s)" % (recipient_id,))


def send_discord_card(recipient_id):
    logger.info("send_discord_card(recipient_id=%s)" % (recipient_id,))

    send_message(json.dumps(build_standard_card(
        recipient_id=recipient_id,
        title="Lmon8 on Discord",
        image_url="https://discordapp.com/assets/ee7c382d9257652a88c8f7b7f22a994d.png",
        item_url="http://taps.io/BvR8w",
        buttons=[
            build_button(Const.CARD_BTN_URL, caption="Activate", url="http://taps.io/BvR8w")
        ],
        quick_replies=main_menu_quick_replies(recipient_id)
    )))


def send_install_card(recipient_id):
    logger.info("send_install_card(recipient_id=%s)" % (recipient_id,))

    send_message(json.dumps(build_standard_card(
        recipient_id=recipient_id,
        title="Earn More Flips",
        image_url="https://i.imgur.com/DbcITTT.png",
        item_url="http://taps.io/Bvj-A",
        buttons=[
            build_button(Const.CARD_BTN_URL, caption="Activate", url="http://taps.io/Bvj-A")
        ],
        quick_replies=main_menu_quick_replies(recipient_id)
    )))



def send_gamebots_card(recipient_id):
    logger.info("send_gamebots_card(recipient_id=%s)" % (recipient_id,))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    product = Product.query.filter(Product.id == customer.product_id).first()

    purchase_code = "gb.{md5}".format(md5=hashlib.md5(("%s" % time.time()).encode()).hexdigest())
    payload = {
        'token'         : Const.GAMEBOTS_POINTS_TOKEN,
        'purchase_code' : purchase_code,
        'amount'        : product.price
    }

    response = requests.post("https://gamebot.tv/gamebots/points-purchase/", data=payload)
    if response.text != "code-exists":
        data = build_standard_card(
            recipient_id=recipient_id,
            title=product.display_name_utf8,
            subtitle=product.description,
            image_url=product.image_url,
            item_url="http://m.me/gamebotsc?ref=/{purchase_code}".format(purchase_code=purchase_code),
            buttons=[
                build_button(Const.CARD_BTN_URL, caption="Activate", url="http://m.me/gamebotsc?ref=/{purchase_code}".format(purchase_code=purchase_code))
            ],
            quick_replies=main_menu_quick_replies(recipient_id)
        )

        send_message(json.dumps(data))

    else:
        send_text(recipient_id, "You can only perform one mystery flip in a 24 hour period", return_home_quick_reply())


def send_steam_card(recipient_id):
    logger.info("send_steam_card(recipient_id=%s)" % (recipient_id,))

    send_message(json.dumps(build_standard_card(
        recipient_id=recipient_id,
        title="Sign into Steam to unlock",
        image_url="https://i.imgur.com/b5aSPCL.png",
        buttons=[
            build_button(Const.CARD_BTN_URL_TALL, caption="Steam Sign In", url="http://lmon.us/claim.php?fb_psid={fb_psid}".format(fb_psid=recipient_id))
        ],
        quick_replies=None
    )))
    send_text(recipient_id, "Sign into Steam to unlock Lmon8 access and utilize your points.")



def send_trade_card(recipient_id):
    logger.info("send_trade_card(recipient_id=%s)" % (recipient_id, ))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    send_message(json.dumps(build_standard_card(
        recipient_id=recipient_id,
        title="Trade any item to unlock",
        image_url="https://i.imgur.com/iHwDWin.png",
        buttons=[
            build_button(Const.CARD_BTN_URL_TALL, caption="Trade Item", url="http://lmon.us/trader/{customer_id}".format(customer_id=customer.id))
        ],
        quick_replies=None
    )))
    send_text(recipient_id, "Please trade any item to unlock access to Lmon8 and utilize your points.")

#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


def send_ico_info(recipient_id):
    logger.info("send_ico_info(recipient_id=%s)" % (recipient_id,))

    tokens = 0
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    if customer is not None:
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT SUM(`tokens`) AS `total` FROM `users`;')
                total = float(cur.fetchone()['total'])

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


        tokens = total

        send_video(recipient_id, url="http://prebot.me/videos/lmon8_final.mp4", attachment_id="285225218619981")
        send_text(recipient_id, "Lmon8 is hosting an Initial Coin Offering (ICO) in Q4 2017. A total of ${price} or {tokens} Lmon8 tokens have been reserved.\n\nAll proceeds from the release of Lmon8 tokens in the ICO shall be used to finance further development, support, marketing of new gaming projects: trading platforms and gaming services associated with virtual items.".format(price=locale.format('%.2f', round(tokens * Const.TOKENS_PER_DOLLAR, 2), grouping=True), tokens=locale.format('%.5f', tokens, grouping=True)))
        send_text(
            recipient_id=recipient_id,
            message_text="Deposit skins and or transfer PTS to reserve Lmon8 tokens below.",
            quick_replies=[
                build_quick_reply(Const.KWIK_BTN_TEXT, "Deposit Skins", payload=Const.PB_PAYLOAD_DEPOSIT_SKINS),
                build_quick_reply(Const.KWIK_BTN_TEXT, "Transfer PTS", payload=Const.PB_PAYLOAD_TRANSFER_POINTS),
                build_quick_reply(Const.KWIK_BTN_TEXT, "What is Lmon8?", payload=Const.PB_PAYLOAD_LMON8_FAQ),
                build_quick_reply(Const.KWIK_BTN_TEXT, "What is an ICO?", payload=Const.PB_PAYLOAD_ICO_FAQ),
                build_quick_reply(Const.KWIK_BTN_TEXT, caption="Menu", payload=Const.PB_PAYLOAD_MAIN_MENU)
            ]
        )


def received_fb_payment(customer, fb_payment):
    logger.info("received_fb_payment(customer=%s, fb_payment=%s)" % (customer, fb_payment))

    db.session.add(Payment(customer.fb_psid, Const.PAYMENT_SOURCE_FB))
    db.session.commit()

    product = Product.query.filter(Product.id == customer.product_id).first()
    if product is not None:
        storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
        if storefront is not None:
            customer.email = fb_payment['requested_user_info']['contact_email']
            purchase = Purchase(customer.id, storefront.id, product.id, 5, fb_payment['payment_credential']['charge_id'])
            purchase.claim_state = 0
            db.session.add(purchase)

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('INSERT INTO `purchases` (`id`, `user_id`, `product_id`, `type`, `charge_id`, `transaction_id`, `paid`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, 1, UTC_TIMESTAMP());', (customer.id, product.id, 5, purchase.charge_id, fb_payment['payment_credential']['fb_payment_id']))
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
            route_purchase_dm(customer.fb_psid, purchase, Const.DM_ACTION_PURCHASE, "Purchase complete for {product_name} at {pacific_time}.\nTo complete this order send the customer ({customer_email}) the item now.".format(product_name=product.display_name_utf8, pacific_time=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%I:%M%P %Z').lstrip("0"), customer_email=customer.email))

            add_points(customer.fb_psid, Const.POINT_AMOUNT_PURCHASE_PRODUCT)

            fb_user = FBUser.query.filter(FBUser.fb_psid == customer.fb_psid).first()
            slack_outbound(
                channel_name="lemonade-purchases",
                message_text="*{customer}* ({email}) just purchased _{product_name}_ for ${price:.2f} from _{storefront_name}_ via FB Payments.\nTrade URL: {trade_url}\nAlt social: {social}".format(customer=customer.fb_psid if fb_user is None else fb_user.full_name_utf8, email=customer.email, product_name=product.display_name_utf8, price=product.price, storefront_name=storefront.display_name_utf8, trade_url=customer.trade_url or "N/A", social=customer.social or "N/A"),
                webhook=Const.SLACK_PURCHASES_WEBHOOK
            )

            time.sleep(3)
            send_text(customer.fb_psid, "Purchase complete!")
            if product.type_id == Const.PRODUCT_TYPE_GAME_ITEM:
                if customer.trade_url is None:
                    customer.trade_url = "_{PENDING}_"
                    db.session.commit()
                    send_text(customer.fb_psid, "Purchase complete.\nPlease enter your Steam Trade URL.", cancel_entry_quick_reply())

                else:
                    send_text(
                        recipient_id=customer.fb_psid,
                        message_text="Steam Trade URL set to {trade_url}\n\nWould you like to change it?".format(trade_url=customer.trade_url),
                        quick_replies=[
                            build_quick_reply(Const.KWIK_BTN_TEXT, "OK", payload=Const.PB_PAYLOAD_TRADE_URL),
                            build_quick_reply(Const.KWIK_BTN_TEXT, "Keep", payload=Const.PB_PAYLOAD_TRADE_URL_KEEP),
                        ]
                    )

            elif product.type_id == Const.PRODUCT_TYPE_STICKER:
                if customer.social is None:
                    customer.social = "_{PENDING}_"
                    db.session.commit()
                    send_text(customer.fb_psid, "Purchase complete.\nPlease enter your Line ID.", cancel_entry_quick_reply())

                else:
                    send_text(
                        recipient_id=customer.fb_psid,
                        message_text="Line ID set to {social}\n\nWould you like to change it?".format(social=customer.social),
                        quick_replies=[
                            build_quick_reply(Const.KWIK_BTN_TEXT, "OK", payload=Const.PB_PAYLOAD_ALT_SOCIAL),
                            build_quick_reply(Const.KWIK_BTN_TEXT, "Keep", payload=Const.PB_PAYLOAD_ALT_SOCIAL_KEEP),

                        ])



def received_payload(recipient_id, payload, type=Const.PAYLOAD_TYPE_POSTBACK):
    logger.info("received_payload(recipient_id=%s, payload=%s, type=%s)" % (recipient_id, payload, type))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

    # postback btn
    if payload == Const.PB_PAYLOAD_RND_FLIP_STOREFRONT:
        send_tracker(fb_psid=recipient_id, category="flip")
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)

                product = None
                while product is None:
                    cur.execute('SELECT `id` FROM `products` WHERE `tags` LIKE %s AND `enabled` = 1 ORDER BY RAND() LIMIT 1;', ("%{tag}%".format(tag="autogen-import"),))
                    row = cur.fetchone()
                    if row is not None:
                        product = Product.query.filter(Product.id == row['id']).first()
                        if product is not None:
                            if flip_wins_for_interval(recipient_id) < Const.FLIPS_PER_24_HOUR:
                                add_points(recipient_id, Const.POINT_AMOUNT_NEXT_SHOP)

                                if random.uniform(0, 1) >= 0.85:
                                    send_discord_card(recipient_id)

                                else:
                                    flip_product(recipient_id, product)

                            else:
                                send_text(recipient_id, "You are only allowed up to {max_flips} flip wins per 24 hour period.".format(max_flips=Const.FLIPS_PER_24_HOUR))

                            view_product(recipient_id, product)

                    else:
                        send_text(recipient_id, "No shops are available to flip right now, try again later.", main_menu_quick_replies(recipient_id))

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

    elif payload == Const.PB_PAYLOAD_MYSTERY_FLIP:
        send_mystery_flip_card(recipient_id)

    elif payload == Const.PB_PAYLOAD_DISNEY_YES:
        customer.paypal_email = None
        db.session.commit()
        #send_image(recipient_id, "https://i.imgur.com/xv2mhAp.gif", "259258191216684", main_menu_quick_replies(recipient_id))
        send_image(recipient_id, "https://i.imgur.com/6Q8o21L.gif", "259272831215220")

    elif payload == Const.PB_PAYLOAD_DISNEY_NO:
        customer.paypal_email = "_{PENDING}_"
        db.session.commit()
        send_text(recipient_id, "Please enter your Disney Tsum Tsum username for the item to transfer.", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_ICO:
        send_ico_info(recipient_id)

    elif payload == Const.PB_PAYLOAD_DEPOSIT_SKINS:
        if customer.steam_id64 is None:
            send_steam_card(recipient_id)
            return "OK", 200

        else:
            if customer.trade_url is None:
                customer.trade_url = "_{PENDING}_"
                db.session.commit();

                send_text(fb_psid, "Steam had been connected to your Lmon8 account, enter your trade url now.")

            else:
                send_trade_card(recipient_id)
                return "OK", 200

    elif payload == Const.PB_PAYLOAD_LMON8_FAQ:
        send_text(
            recipient_id=recipient_id,
            message_text="Lmon8 is the world's fastest growing virtual mall  on Facebook Messenger, Line Messenger, and Kik Messenger.\n\nOn July 5th 2017 we are allowing early adopters to deposit skins and pts for software tokens of Lmon8. Lmon8's technology allows you buy, sell, resell, and win virtual in-game items.",
            quick_replies=[
                build_quick_reply(Const.KWIK_BTN_TEXT, "Deposit Skins", payload=Const.PB_PAYLOAD_DEPOSIT_SKINS),
                build_quick_reply(Const.KWIK_BTN_TEXT, "Transfer PTS", payload=Const.PB_PAYLOAD_TRANSFER_POINTS),
                build_quick_reply(Const.KWIK_BTN_TEXT, "What is Lmon8?", payload=Const.PB_PAYLOAD_LMON8_FAQ),
                build_quick_reply(Const.KWIK_BTN_TEXT, "What is an ICO?", payload=Const.PB_PAYLOAD_ICO_FAQ),
                build_quick_reply(Const.KWIK_BTN_TEXT, caption="Menu", payload=Const.PB_PAYLOAD_MAIN_MENU)
            ]
        )

    elif payload == Const.PB_PAYLOAD_ICO_FAQ:
        send_text(
            recipient_id=recipient_id,
            message_text="An initial coin offering (ICO) is a means of crowdfunding the release of a new cryptocurrency. Generally, tokens for the new cryptocurrency are sold to raise money for technical development before the cryptocurrency is released.",
            quick_replies=[
                build_quick_reply(Const.KWIK_BTN_TEXT, "Deposit Skins", payload=Const.PB_PAYLOAD_DEPOSIT_SKINS),
                build_quick_reply(Const.KWIK_BTN_TEXT, "Transfer PTS", payload=Const.PB_PAYLOAD_TRANSFER_POINTS),
                build_quick_reply(Const.KWIK_BTN_TEXT, "What is Lmon8?", payload=Const.PB_PAYLOAD_LMON8_FAQ),
                build_quick_reply(Const.KWIK_BTN_TEXT, "What is an ICO?", payload=Const.PB_PAYLOAD_ICO_FAQ),
                build_quick_reply(Const.KWIK_BTN_TEXT, caption="Menu", payload=Const.PB_PAYLOAD_MAIN_MENU)
            ]
        )

    elif payload == Const.PB_PAYLOAD_TRANSFER_POINTS:
        customer.input_state = 1
        db.session.commit()

        send_text(recipient_id, "How many PTS do you want to transfer?", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_CONVERT_YES:
        points = customer.input_state
        customer.input_state = 2
        customer.tokens = customer.tokens or 0
        customer.tokens += (points / float(Const.POINTS_PER_DOLLAR)) * Const.TOKENS_PER_DOLLAR
        add_points(recipient_id, -points)
        db.session.commit()

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('UPDATE `users` SET `tokens` = `tokens` + %s WHERE `id` = %s LIMIT 1;', ((points / float(Const.POINTS_PER_DOLLAR)) * Const.TOKENS_PER_DOLLAR,  customer.id,))
                conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(recipient_id, "You have transferred {points} PTS for {tokens} Lmon8 tokens. For more information on Lmom8's ICO please join our slack channel.".format(points=locale.format('%d', points, grouping=True), tokens=locale.format('%.5f', (points / float(Const.POINTS_PER_DOLLAR)) * Const.TOKENS_PER_DOLLAR, grouping=True)))
        send_text(recipient_id, " https://discord.gg/sgmcn8K", main_menu_quick_replies(recipient_id))

    elif payload == Const.PB_PAYLOAD_CONVERT_NO:
        customer.input_state = 1
        db.session.commit()

        send_text(recipient_id, "How many PTS do you want to transfer?", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_CUSTOMER_POINTS:
        rank, points = customer_points_rank(recipient_id)
        send_text(recipient_id, "You have {points} Lmon8 Points & are Ranked #{rank}.".format(points=locale.format('%d', points, grouping=True), rank=locale.format('%d', rank, grouping=True)), main_menu_quick_replies(recipient_id))

    elif payload == Const.PB_PAYLOAD_REFERRAL_FAQ:
        send_text(recipient_id, "Share your Lmon8 ID with Friends.")
        send_text(recipient_id, "https://m.me/lmon8?ref=/ref/{fb_psid}".format(fb_psid=recipient_id), main_menu_quick_replies(recipient_id))

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
        logger.info("----------=BOT GREETING @(%s)=----------" % (time.strftime('%Y-%m-%d %H:%M:%S')))
        welcome_message(recipient_id, Const.ENTRY_MARKETPLACE_GREETING)

        slack_outbound(
            channel_name=Const.SLACK_ORTHODOX_CHANNEL,
            message_text="{fb_user} arrived from “Getting Started” btn via deeplink {deeplink}".format(fb_user=fb_psid_profile(recipient_id).full_name_utf8, deeplink=customer.referrer)
        )


    elif payload == Const.PB_PAYLOAD_RESELL_STOREFRONT:
        # send_text(recipient_id, "This is not available to resell at this time.", main_menu_quick_replies(recipient_id))
        product = Product.query.filter(Product.id == customer.product_id).first()
        if product.storefront_id is not None:
            storefront, product = clone_storefront(recipient_id, product.storefront_id)
            # send_tracker(fb_psid=recipient_id, category="resell", label=product.display_name_utf8)
            if storefront is not None and product is not None:
                send_text(recipient_id, "Welcome to the Lmon8 Reseller Program. Every time an item is sold you will get {points} Pts. Keep Flipping!".format(points=locale.format('%d', Const.POINT_AMOUNT_RESELL_STOREFRONT, grouping=True)))
                send_text(recipient_id, "{storefront_name} created.\n{prebot_url}".format(storefront_name=storefront.display_name_utf8, prebot_url=product.messenger_url), [build_quick_reply(Const.KWIK_BTN_TEXT, caption="Share ({points} Pts)".format(points=Const.POINT_AMOUNT_SHARE_APP), payload=Const.PB_PAYLOAD_SHARE_APP)] + main_menu_quick_replies(recipient_id))

            else:
                send_text(recipient_id, "This is not available to resell at this time.", main_menu_quick_replies(recipient_id))
        else:
            send_text(recipient_id, "This is not available to resell at this time.", main_menu_quick_replies(recipient_id))


    elif re.search(r'^AUTO_GEN_STOREFRONT\-(.+)$', payload) is not None:
        send_tracker(fb_psid=recipient_id, category="transaction", label="resell")
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `id` FROM `products` WHERE `name` LIKE %s ORDER BY `views` DESC LIMIT 1;', ("%{name}%".format(name=re.match(r'^AUTO_GEN_STOREFRONT\-(?P<key>.+)$', payload).group('key')),))
                row = cur.fetchone()
                if row is not None:
                    product = Product.query.filter(Product.id == row['id']).first()
                    if product.storefront_id is not None:
                        storefront, product = clone_storefront(recipient_id, product.storefront_id)
                        # send_tracker(fb_psid=recipient_id, category="resell", label=product.display_name_utf8)
                        if storefront is not None and product is not None:
                            send_text(recipient_id, "Welcome to the Lmon8 Reseller Program. Every time an item is sold you will get {points} Pts. Keep Flipping!".format(points=locale.format('%d', Const.POINT_AMOUNT_RESELL_STOREFRONT, grouping=True)))
                            send_text(recipient_id, "{storefront_name} created.\n{prebot_url}".format(storefront_name=storefront.display_name_utf8, prebot_url=product.messenger_url), [build_quick_reply(Const.KWIK_BTN_TEXT, caption="Share ({points} Pts)".format(points=Const.POINT_AMOUNT_SHARE_APP), payload=Const.PB_PAYLOAD_SHARE_APP)] + main_menu_quick_replies(recipient_id))

                        else:
                            send_text(recipient_id, "This is not available to resell at this time.", main_menu_quick_replies(recipient_id))
                    else:
                        send_text(recipient_id, "This is not available to resell at this time.", main_menu_quick_replies(recipient_id))

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


    elif re.search(r'^SEARCH_STOREFRONT\-(.+)$', payload) is not None:
        search_term = re.match(r'^SEARCH_STOREFRONT-(?P<search_term>.*)([A-Z][a-z0-9]+){2}$', payload).group('search_term')
        products = Product.query.filter(Product.name.ilike("{search_term}%".format(search_term=search_term))).all()
        if len(products) > 0:
            product = random.choice(products)
            if product is not None:
                view_product(recipient_id, product)

        else:
            send_text(recipient_id, "Couldn't find any shops for {search_term}, why don't you create one.".format(search_term=search_term), main_menu_quick_replies(recipient_id))


    elif payload == Const.PB_PAYLOAD_BUILD_STOREFRONT:
        send_text(
            recipient_id=recipient_id,
            message_text="Do you want to create a custom shop or become a reseller?",
            quick_replies=[
                build_quick_reply(Const.KWIK_BTN_TEXT, "Custom", payload=Const.PB_PAYLOAD_CREATE_STOREFRONT),
                build_quick_reply(Const.KWIK_BTN_TEXT, "Resell", payload=Const.PB_PAYLOAD_RESELLER_CAROUSEL)
            ] + cancel_entry_quick_reply()
        )

    elif payload == Const.PB_PAYLOAD_RESELLER_CAROUSEL:
        send_autogen_carousel(recipient_id)

    elif payload == Const.PB_PAYLOAD_CREATE_STOREFRONT:
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

        send_text(recipient_id, "Give your shop a name.", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_DELETE_STOREFRONT:
        if Storefront.query.filter(Storefront.fb_psid == recipient_id).count() == 0:
            send_text(recipient_id, "You do not have a shop yet.")

        else:
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

            send_text(recipient_id, "Upload a video or image of the item you are selling.", cancel_entry_quick_reply())

        else:
            storefront = Storefront(recipient_id)
            db.session.add(storefront)
            db.session.commit()

            send_text(recipient_id, "Give your shop a name.", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_DELETE_PRODUCT:
        if Product.query.filter(Product.fb_psid == recipient_id).count() == 0:
            send_text(recipient_id, "You do not have an item to sell yet.")
            send_admin_carousel(recipient_id)

        else:
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

            for product in Product.query.filter(Product.fb_psid == recipient_id):
                send_text(recipient_id, "Removing your existing item \"{product_name}\"...".format(product_name=product.display_name_utf8))

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


            product = Product(recipient_id, storefront.id)
            db.session.add(product)
            db.session.commit()
            send_text(recipient_id, "Upload a video or image of the item you are selling.", cancel_entry_quick_reply())

    elif re.search('^VIEW_PRODUCT\-(\d+)$', payload) is not None:
        product_id = re.match(r'^VIEW_PRODUCT\-(?P<product_id>\d+)$', payload).group('product_id')
        product = Product.query.filter(Product.id == product_id).first()
        view_product(recipient_id, product)

    elif payload == Const.PB_PAYLOAD_SUPPORT:
        send_text(recipient_id, "Support for Lemonade:\nprebot.me/support")

    elif payload == Const.PB_PAYLOAD_PURCHASE_POINTS_PAK:
        send_text(recipient_id, "Select a Lmon8 point pack below.", point_pak_quick_replies())
        #send_point_pak_carousel(recipient_id)

    elif re.search('^PURCHASE_POINTS_PAK_(\d+)$', payload) is not None:
        purchase_points_pak(recipient_id, int(re.match(r'^PURCHASE_POINTS_PAK_(?P<amount>\d+)$', payload).group('amount')))

    elif payload == Const.PB_PAYLOAD_CHECKOUT_PRODUCT:
        # try:
        #     conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
        #     with conn:
        #         cur = conn.cursor(mysql.cursors.DictCursor)
        #         cur.execute('SELECT `id` FROM `unlocked_users` WHERE `fb_psid` = %s LIMIT 1;', (recipient_id,))
        #         if cur.fetchone() is None:
        #             send_text(recipient_id, "You are currently not authorized to purchase this item.")
        #             return "OK", 200
        #
        # except mysql.Error, e:
        #     logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))
        #
        # finally:
        #     if conn:
        #         conn.close()

        product = Product.query.filter(Product.id == customer.product_id).first()
        if product is not None:
            send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_CHECKOUT)

    elif payload == Const.PB_PAYLOAD_CHECKOUT_BITCOIN:
        # send_tracker(fb_psid=recipient_id, category="purchase")

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
            send_customer_carousel(recipient_id, product.id)

        else:
            send_text(recipient_id, "Post your Bitcoin wallet's QR code or typein  the address", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_CHECKOUT_CREDIT_CARD:
        # send_tracker(fb_psid=recipient_id, category="purchase")

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
        # send_tracker(fb_psid=recipient_id, category="purchase")

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
            add_points(recipient_id, Const.POINT_AMOUNT_PURCHASE_PRODUCT)

    elif payload == Const.PB_PAYLOAD_CHECKOUT_POINTS:
        # send_tracker(fb_psid=recipient_id, category="purchase")

        product = Product.query.filter(Product.id == customer.product_id).first()
        storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()

        if customer.points >= product.price * Const.POINTS_PER_DOLLAR:
            try:
                Payment.query.filter(Payment.fb_psid == recipient_id).delete()
                db.session.commit()
            except:
                db.session.rollback()

            db.session.add(Payment(recipient_id, Const.PAYMENT_SOURCE_PAYPAL))
            db.session.commit()

            send_text(
                recipient_id=recipient_id,
                message_text="Are you sure you want to use {points} pts for {product_name}".format(points=points_per_dollar(product.price), product_name=product.display_name_utf8),
                quick_replies=[
                    build_quick_reply(Const.KWIK_BTN_TEXT, caption="Confirm", payload=Const.PB_PAYLOAD_PURCHASE_POINTS_YES),
                    build_quick_reply(Const.KWIK_BTN_TEXT, caption="Cancel", payload=Const.PB_PAYLOAD_PURCHASE_POINTS_NO)
                ]
            )

        else:
            send_text(recipient_id, "Sorry, you do not have enough points yet")
            return "OK", 200

            # send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_CHECKOUT)

    elif payload == Const.PB_PAYLOAD_PURCHASE_POINTS_YES:
        product = Product.query.filter(Product.id == customer.product_id).first()

        if product is not None:
            storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()

            if purchase_product(recipient_id, Const.PAYMENT_SOURCE_POINTS):
                logger.info(":::::::TAGS --> %s" % (product.tag_list_utf8,))

                if "bonus-flip" in product.tag_list_utf8:
                    send_mystery_flip_card(recipient_id)

                elif "gamebots-points" in product.tag_list_utf8:
                    send_gamebots_card(recipient_id)

                elif "disneyjp" in product.tag_list_utf8:
                    send_image(recipient_id, "https://i.imgur.com/rsiKG84.gif", "259175247891645")

                else:
                    if customer.trade_url is None:
                        customer.trade_url = "_{PENDING}_"
                        db.session.commit()
                        send_text(customer.fb_psid, "Your account and pts will be verified before your trade is released. Please wait up to 12 hours, keep notifications on.\n\nPlease enter your Steam Trade URL.", cancel_entry_quick_reply())

                    else:
                        send_text(
                            recipient_id=customer.fb_psid,
                            message_text="Confirm your Steam Trade URL:\n\n{trade_url}\n\nWould you like to edit it?".format(trade_url=customer.trade_url),
                            quick_replies=[
                                build_quick_reply(Const.KWIK_BTN_TEXT, "Confirm", payload=Const.PB_PAYLOAD_TRADE_URL_KEEP),
                                build_quick_reply(Const.KWIK_BTN_TEXT, "Edit URL", payload=Const.PB_PAYLOAD_TRADE_URL)
                            ])

                if storefront is not None:
                    send_text(storefront.fb_psid, "Someone has purchased your resell item, here's {points} Pts!".format(points=locale.format('%d', Const.POINT_AMOUNT_RESELL_STOREFRONT, grouping=True)))
                    add_points(storefront.fb_psid, Const.POINT_AMOUNT_RESELL_STOREFRONT)

            else:
                send_text(recipient_id, "Sorry, you do not have enough points yet")
                send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_CHECKOUT)

    elif payload == Const.PB_PAYLOAD_PURCHASE_POINTS_NO:
        send_product_card(recipient_id, customer.product_id, Const.CARD_TYPE_PRODUCT_CHECKOUT)

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
        customer.trade_url = "_{PENDING}_"
        customer.purchase_id = purchase.id
        db.session.commit()

        send_text(recipient_id, "Type your URL here", cancel_entry_quick_reply())

    elif re.search(r'^DM_REQUEST_INVOICE\-(\d+)$', payload) is not None:
        # send_tracker(fb_psid=recipient_id, category="button-dm-request-invoice")
        purchase_id = re.match(r'^DM_REQUEST_INVOICE\-(?P<purchase_id>\d+)$', payload).group('purchase_id')
        customer.purchase_id = purchase_id
        db.session.commit()

        purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
        storefront_query = db.session.query(Storefront.fb_psid).filter(Storefront.id == purchase.storefront_id).subquery('storefront_query')
        storefront_owner = Customer.query.filter(Customer.fb_psid.in_(storefront_query)).first()

        send_product_card(recipient_id, purchase.product_id, Const.CARD_TYPE_PRODUCT_INVOICE_PAYPAL)

    elif re.search(r'^DM_REQUEST_PAYMENT\-(\d+)$', payload) is not None:
        # send_tracker(fb_psid=recipient_id, category="button-dm-request-payment")
        purchase_id = re.match(r'^DM_REQUEST_PAYMENT\-(?P<purchase_id>\d+)$', payload).group('purchase_id')
        purchase = Purchase.query.filter(Purchase.id == purchase_id).first()
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

        customer.storefront_id = None
        customer.product_id = None
        customer.purchase_id = None
        customer.referrer = None
        db.session.commit()

        send_admin_carousel(recipient_id)


    elif payload == Const.PB_PAYLOAD_HOME_CONTENT:
        # send_tracker(fb_psid=recipient_id, category="button-ok")
        send_home_content(recipient_id)

    elif payload == Const.PB_PAYLOAD_RND_STOREFRONT:
        send_tracker(fb_psid=recipient_id, category="flip")
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `id` FROM `products` WHERE `tags` LIKE %s AND `enabled` = 1 ORDER BY RAND() LIMIT 1;', ("%{tag}%".format(tag="autogen-import"),))
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
        pass
        # send_tracker(fb_psid=recipient_id, category="feature-shop")
        # send_text(recipient_id, "Tap here to purchase:\nhttps://paypal.me/gamebotsc/1.99", main_menu_quick_replies(recipient_id))

    elif payload == Const.PB_PAYLOAD_CANCEL_ENTRY_SEQUENCE:
        # send_tracker(fb_psid=recipient_id, category="button-cancel-entry-sequence")

        clear_entry_sequences(recipient_id)
        send_home_content(recipient_id)

    elif payload == Const.PB_PAYLOAD_SHARE_APP:
        # send_tracker(fb_psid=recipient_id, category="button-say-thanks")
        add_points(recipient_id, Const.POINT_AMOUNT_SHARE_APP)
        send_app_card(recipient_id)

    elif re.search(r'^SAY_THANKS\-(.+)$', payload) is not None:
        # send_tracker(fb_psid=recipient_id, category="button-say-thanks")
        send_image(re.match(r'^SAY_THANKS\-(?P<fb_psid>.+)$', payload).group('fb_psid'), Const.IMAGE_URL_SAY_THANKS)

    elif payload == Const.PB_PAYLOAD_SUBMIT_STOREFRONT:
        # send_tracker(fb_psid=recipient_id, category="create-shop")

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

            send_admin_carousel(recipient_id)

            fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
            slack_outbound(
                channel_name=Const.SLACK_ORTHODOX_CHANNEL,
                username=Const.SLACK_ORTHODOX_HANDLE,
                webhook=Const.SLACK_ORTHODOX_WEBHOOK,
                message_text="*{fb_name}* just created a shop named _{storefront_name}_.".format(fb_name=recipient_id if fb_user is None else fb_user.full_name_utf8, storefront_name=storefront.display_name_utf8),
                image_url=storefront.logo_url
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
            # send_text(
            #     recipient_id=recipient_id,
            #     message_text="Is {product_name} a physical or virtual good?".format(product_name=product.display_name_utf8),
            #     quick_replies=[
            #         build_quick_reply(Const.KWIK_BTN_TEXT, "Physical", Const.PB_PAYLOAD_PRODUCT_TYPE_PHYSICAL),
            #         build_quick_reply(Const.KWIK_BTN_TEXT, "Virtual", Const.PB_PAYLOAD_PRODUCT_TYPE_VIRTUAL)
            #     ] + cancel_entry_quick_reply()
            # )

    elif payload == Const.PB_PAYLOAD_PRODUCT_TYPE_GAME_ITEM:
        # send_tracker(fb_psid=recipient_id, category="button-product-physical")

        product = Product.query.filter(Product.fb_psid == recipient_id).filter(Product.creation_state == 4).first()
        if product is not None:
            product.type_id = Const.PRODUCT_TYPE_GAME_ITEM
            product.creation_state = 7
            product.added = int(time.time())
            db.session.commit()

            # send_tracker(fb_psid=recipient_id, category="add-product")
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
                message_text="*{fb_name}* just created a {product_type} product named _{product_name}_ for the shop _{storefront_name}_.".format(fb_name=recipient_id if fb_user is None else fb_user.full_name_utf8, product_type="sticker" if product.type_id == Const.PRODUCT_TYPE_STICKER else "game item", product_name=product.display_name_utf8, storefront_name=storefront.display_name_utf8),
                image_url=product.image_url
            )

            send_admin_carousel(recipient_id)

            # send_image(recipient_id, Const.IMAGE_URL_PRODUCT_CREATED)
            send_text(recipient_id, "You have successfully added {product_name} to {storefront_name}.".format(product_name=product.display_name_utf8, storefront_name=storefront.display_name_utf8))
            send_text(recipient_id, "Tap Share below to share your shop with friends.")
            send_text(
                recipient_id=recipient_id,
                message_text=product.messenger_url,
                quick_replies=main_menu_quick_replies(recipient_id)
            )

    elif payload == Const.PB_PAYLOAD_PRODUCT_TYPE_STICKER:
        # send_tracker(fb_psid=recipient_id, category="button-product-virtual")

        product = Product.query.filter(Product.fb_psid == recipient_id).filter(Product.creation_state == 4).first()
        if product is not None:
            product.type_id = Const.PRODUCT_TYPE_STICKER
            product.creation_state = 7
            product.added = int(time.time())
            db.session.commit()

            # send_tracker(fb_psid=recipient_id, category="add-product")
            add_points(recipient_id, Const.POINT_AMOUNT_SUBMIT_PRODUCT)
            logger.info("INSERT -------->")

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('SELECT * FROM `products` WHERE `name` = %s AND `enabled` = 1;', (product.name,))
                    logger.info("cur.fetchone() is None (%s)", (cur.fetchone() is None,))
                    if cur.fetchone() is None:
                        cur.execute('INSERT INTO `products` (`id`, `storefront_id`, `type`, `name`, `display_name`, `description`, `tags`, `image_url`, `video_url`, `attachment_id`, `price`, `prebot_url`, `physical_url`, `release_date`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s), UTC_TIMESTAMP());', (product.storefront_id, product.type_id, product.name, product.display_name_utf8, product.description or "", "" if product.tags is None else product.tags.encode('utf-8'), product.image_url, product.video_url or "", product.attachment_id or "", product.price, product.prebot_url, product.physical_url or "", product.release_date))
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
                message_text="*{fb_name}* just created a {product_type} product named _{product_name}_ for the shop _{storefront_name}_.".format(fb_name=recipient_id if fb_user is None else fb_user.full_name_utf8, product_type="sticker" if product.type_id == Const.PRODUCT_TYPE_STICKER else "game item", product_name=product.display_name_utf8, storefront_name=storefront.display_name_utf8),
                image_url=product.image_url
            )

            send_admin_carousel(recipient_id)

            # send_image(recipient_id, Const.IMAGE_URL_PRODUCT_CREATED)
            send_text(recipient_id, "You have successfully added {product_name} to {storefront_name}.".format(product_name=product.display_name_utf8, storefront_name=storefront.display_name_utf8))
            send_text(recipient_id, "Tap Share below to share your shop with friends.")
            send_text(
                recipient_id=recipient_id,
                message_text=product.messenger_url,
                quick_replies=main_menu_quick_replies(recipient_id)
            )

    elif payload == Const.PB_PAYLOAD_PRODUCT_TYPE_SKIP:
        # send_tracker(fb_psid=recipient_id, category="button-skip-tags")

        product = Product.query.filter(Product.fb_psid == recipient_id).filter(Product.creation_state == 4).first()
        if product is not None:
            product.type_id = Const.PRODUCT_TYPE_SKIPPED
            product.creation_state = 7
            product.added = int(time.time())
            db.session.commit()

            # send_tracker(fb_psid=recipient_id, category="add-product")
            add_points(recipient_id, Const.POINT_AMOUNT_SUBMIT_PRODUCT)
            logger.info("INSERT -------->")

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('SELECT * FROM `products` WHERE `name` = %s AND `enabled` = 1;', (product.name,))
                    logger.info("cur.fetchone() is None (%s)", (cur.fetchone() is None,))
                    if cur.fetchone() is None:
                        cur.execute('INSERT INTO `products` (`id`, `storefront_id`, `type`, `name`, `display_name`, `description`, `tags`, `image_url`, `video_url`, `attachment_id`, `price`, `prebot_url`, `physical_url`, `release_date`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s), UTC_TIMESTAMP());', (product.storefront_id, product.type_id, product.name, product.display_name_utf8, product.description or "", "" if product.tags is None else product.tags.encode('utf-8'), product.image_url, product.video_url or "", product.attachment_id or "", product.price, product.prebot_url, product.physical_url or "", product.release_date))
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
                message_text="*{fb_name}* just created a product named _{product_name}_ for the shop _{storefront_name}_.".format(fb_name=recipient_id if fb_user is None else fb_user.full_name_utf8, product_name=product.display_name_utf8, storefront_name=storefront.display_name_utf8),
                image_url=product.image_url
            )

            send_admin_carousel(recipient_id)

            # send_image(recipient_id, Const.IMAGE_URL_PRODUCT_CREATED)
            send_text(recipient_id, "You have successfully added {product_name} to {storefront_name}.".format(product_name=product.display_name_utf8, storefront_name=storefront.display_name_utf8))
            send_text(recipient_id, "Tap Share below to share your shop with friends.")
            send_text(
                recipient_id=recipient_id,
                message_text=product.messenger_url,
                quick_replies=main_menu_quick_replies(recipient_id)
            )



    elif payload == Const.PB_PAYLOAD_SUBMIT_PRODUCT:
        # send_tracker(fb_psid=recipient_id, category="add-product")

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
                        cur.execute('INSERT INTO `products` (`id`, `storefront_id`, `type`, `name`, `display_name`, `description`, `tags`, `image_url`, `video_url`, `attachment_id`, `price`, `prebot_url`, `physical_url`, `release_date`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s), UTC_TIMESTAMP());', (product.storefront_id, product.type_id, product.name, product.display_name_utf8, product.description or "", "" if product.tags is None else product.tags.encode('utf-8'), product.image_url, product.video_url or "", product.attachment_id or "", product.price, product.prebot_url, product.physical_url or "", product.release_date))
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
                message_text="*{fb_name}* just created a {product_type} product named _{product_name}_ for the shop _{storefront_name}_.\n{physical_url}".format(fb_name=recipient_id if fb_user is None else fb_user.full_name_utf8, product_type="sticker" if product.type_id == Const.PRODUCT_TYPE_sticker else "game item", product_name=product.display_name_utf8, storefront_name=storefront.display_name_utf8, physical_url=product.physical_url or ""),
                image_url=product.image_url
            )

            send_admin_carousel(recipient_id)

            # send_image(recipient_id, Const.IMAGE_URL_PRODUCT_CREATED)
            send_text(recipient_id, "You have successfully added {product_name} to {storefront_name}.".format(product_name=product.display_name_utf8, storefront_name=storefront.display_name_utf8))
            send_text(recipient_id, "Tap Share below to share your shop with friends.")
            send_text(
                recipient_id=recipient_id,
                message_text=product.messenger_url,
                quick_replies=main_menu_quick_replies(recipient_id)
            )

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
            send_text(recipient_id, "Canceling your {product_name} item creation...".format(product_name=product.display_name_utf8))

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

    elif payload == Const.PB_PAYLOAD_MOD_TASK_YES:
        send_admin_carousel(recipient_id)

    elif payload == Const.PB_PAYLOAD_MOD_TASK_NO:
        send_admin_carousel(recipient_id)

    elif payload == Const.PB_PAYLOAD_TRADE_URL:
        customer.trade_url = "_{PENDING}_"
        db.session.commit()
        send_text(recipient_id, "Please enter your Steam Trade URL.", return_home_quick_reply("Cancel"))


    elif payload == Const.PB_PAYLOAD_TRADE_URL_KEEP:
        # send_tracker(fb_psid=recipient_id, category="trade-url-set", label=customer.trade_url)
        if customer.product_id is not None:
            send_text(recipient_id, "Your purchase has been made. The item and points are being approved and will transfer shortly.\n\nPurchase ID: {purchase_id}".format(purchase_id=customer.purchase_id), main_menu_quick_replies(recipient_id))
            send_customer_carousel(recipient_id, customer.product_id)

        else:
            send_trade_card(recipient_id)

    elif payload == Const.PB_PAYLOAD_ALT_SOCIAL:
        customer.social = "_{PENDING}_"
        db.session.commit()
        send_text(recipient_id, "Please enter your Line ID.", return_home_quick_reply("Cancel"))

    elif payload == Const.PB_PAYLOAD_ALT_SOCIAL_KEEP:
        send_text(recipient_id, "Line ID has been set to “{alt_social}”\n\nInstructions:\n1. Accept friend request from link for profile Lmon8.\n\n2. Wait 6 hours.".format(alt_social=customer.social), main_menu_quick_replies(recipient_id))
        send_customer_carousel(recipient_id, customer.product_id)

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

        customer.paypal_email = "_{PENDING}_"
        db.session.commit()
        send_text(recipient_id, "Enter your PayPal email address", cancel_entry_quick_reply())

    elif payload == Const.PB_PAYLOAD_PAYOUT_BITCOIN:
        # send_tracker(fb_psid=recipient_id, category="button-bitcoin-payout")

        customer.bitcoin_addr = "_{PENDING}_"
        db.session.commit()
        send_text(recipient_id, "Post your Bitcoin wallet's QR code or type in the address", cancel_entry_quick_reply())

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

                # storefront.creation_state = 3
                storefront.logo_url = "http://lmon.us/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
                # db.session.commit()

                # send_text(recipient_id, "Here's what your Shopbot will look like:")
                # send_storefront_card(recipient_id, storefront.id, Const.CARD_TYPE_STOREFRONT_PREVIEW)


                #--- skip preview -- do submit
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

                send_admin_carousel(recipient_id)

                fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
                slack_outbound(
                    channel_name=Const.SLACK_ORTHODOX_CHANNEL,
                    username=Const.SLACK_ORTHODOX_HANDLE,
                    webhook=Const.SLACK_ORTHODOX_WEBHOOK,
                    message_text="*{fb_name}* just created a shop named _{storefront_name}_.".format(fb_name=recipient_id if fb_user is None else fb_user.full_name_utf8, storefront_name=storefront.display_name_utf8),
                    image_url=storefront.logo_url
                )



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

                    send_text(recipient_id, "Give your item a title.", cancel_entry_quick_reply())

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

            send_text(recipient_id, "Give your item a title.", cancel_entry_quick_reply())

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

    #-- show featured shops
    elif message_text == "/featured":
        send_featured_carousel(recipient_id)

    # -- show mysteryflip card
    elif message_text == "/mysteryflip":
        send_mystery_flip_card(recipient_id)

    #-- disney special
    elif message_text.lower() == "tsum tsum":
        customer.product_id = 12901
        db.session.commit()
        send_text(recipient_id, "Please enter passcode.", cancel_entry_quick_reply())
        return "OK", 200


    #-- share referral code
    elif re.search(r'^fb(\d+)$', message_text.lower()) is not None:
        ref_customer = Customer.query.filter(Customer.fb_psid == re.match(r'^fb(?P<fb_psid>\d+)$', message_text.lower()).group('fb_psid')).first()
        if ref_customer is not None:
            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('SELECT `id` FROM `referral_entries` WHERE `source_id` = %s AND `entry_id` = %s LIMIT 1;', (ref_customer.id, customer.id))
                    if cur.fetchone() is None:
                        if customer.fb_psid != ref_customer.fb_psid:
                            cur.execute('INSERT INTO `referral_entries` (`id`, `source_id`, `entry_id`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());', (ref_customer.id, customer.id))
                            conn.commit()
                            add_points(recipient_id, "You added {points} Pts for entering a referral", main_menu_quick_replies(recipient_id))
                            add_points(ref_customer.fb_psid, Const.POINT_AMOUNT_REFFERAL)
                            send_text(recipient_id, "{points} Pts have been added to {message_text}".format(points=Const.POINT_AMOUNT_REFFERAL, message_text=message_text), main_menu_quick_replies(recipient_id))
                            send_text(ref_customer.fb_psid, "{points} Pts have been added because someone entered your referral code!".format(points=Const.POINT_AMOUNT_REFFERAL), main_menu_quick_replies(recipient_id))

                        else:
                            send_text(recipient_id, "You cannot enter your own referral code", main_menu_quick_replies(recipient_id))

                    else:
                        send_text(recipient_id, "You already entered the referral code {message_text}".format(message_text=message_text), main_menu_quick_replies(recipient_id))


            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

        else:
            send_text(recipient_id, "Couldn't locate that referral code, try again", main_menu_quick_replies(recipient_id))


    #-- force referral
    elif message_text.startswith("/"):
        welcome_message(recipient_id, Const.ENTRY_PRODUCT_REFERRAL, message_text)

    #-- protected entry
    elif message_text in Const.RESERVED_PROTECTED_REPLIES.split("|"):
        #send_image(recipient_id, "https://i.imgur.com/rsiKG84.gif", "240305683111935")
        product = Product.query.filter(Product.id == customer.product_id).first()
        if product is not None:
            send_image(recipient_id, "https://i.imgur.com/rsiKG84.gif", "240749559734214")
            if customer.referrer is not None and ("/flip/" in customer.referrer or customer.product_id == 12901):
                flip_product(recipient_id, product)

            view_product(recipient_id, product, False)

        return "OK", 200

    #-- show admin carousel
    elif message_text.lower() in Const.RESERVED_COMMAND_REPLIES.split("|"):
        clear_entry_sequences(recipient_id)
        send_admin_carousel(recipient_id)

    #-- fbpsid reply
    elif message_text.lower() in Const.RESERVED_FBPSID_REPLIES.split("|"):
        send_text(recipient_id, "Share your Lmon8 referral URL with Friends.")
        send_text(recipient_id, "https://m.me/lmon8?ref=/ref/{fb_psid}".format(fb_psid=recipient_id))

    #-- faq reply
    elif message_text.lower() in Const.RESERVED_FAQ_REPLIES.split("|"):
        send_text(recipient_id, "1. Users may wait up to 24 hours to get their items transferred.\n\n2. You may only submit one support request per day.\n\n3. Your trade maybe rejected and or account banned for using multiple Facebook accounts.\n\n4. Your trade maybe rejected and or account banned if found to be aggressively abusing our system.\n\n5. Your trade maybe rejected and or account banned for repeat abuse of our mods, support, and social staff.")
        send_text(recipient_id, "6. Your trade maybe rejected and or account banned for repeat abuse of our social channels including posts, GAs, and more.\n\n7. Your account must have a correct steam Trade URL for your trade to transfer.\n\n8. You can earn more points by being a mod.\n\n9. You can only flip 100 times per day.\n\n10. You must keep notifications on for extra points.", main_menu_quick_replies(recipient_id))

    #-- support replies
    elif message_text.lower() in Const.RESERVED_SUPPORT_REPLIES.split("|"):
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `id` FROM `users` WHERE `fb_psid` = %s AND `support` >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL 24 HOUR) LIMIT 1;', (recipient_id,))
                if cur.fetchone() is None:
                    customer.paypal_name = "__{PENDING}__"
                    db.session.commit()

                    send_text(recipient_id, "Welcome to Lmon8 Support. Your user id has been identified: {fb_psid}".format(fb_psid=recipient_id))
                    send_text(
                        recipient_id=recipient_id,
                        message_text="Please describe your support issue (500 character limit). Include purchase ID for faster look up.",
                        quick_replies=return_home_quick_reply("Cancel"))

                else:
                    send_text(recipient_id, "You can only submit 1 support ticket per 24 hours", main_menu_quick_replies(recipient_id))

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

    #-- steam replies
    elif message_text.lower() in Const.RESERVED_STEAM_REPLIES.split("|"):
        send_steam_card(recipient_id)

    #-- deposit replies
    elif message_text.lower() in Const.RESERVED_DEPOST_REPLIES.split("|"):
        send_trade_card(recipient_id)


    #-- leaderboard replies
    elif message_text.lower() in Const.RESERVED_LEADERBOARD_REPLIES.split("|"):

        leaders = ""
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `users`.`points` AS `points`, `fb_users`.`first_name` AS `first_name`, `fb_users`.`last_name` AS `last_name` FROM `users` INNER JOIN `fb_users` ON `users`.`id` = `fb_users`.`user_id` ORDER BY `points` DESC LIMIT 10;')
                for row in cur.fetchall():
                   leaders = "{leaders}\n\n{f_name} {l_name}. - {points} Pts".format(leaders=leaders, f_name=row['first_name'], l_name=row['last_name'][0], points=locale.format('%d', row['points'], grouping=True))

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(recipient_id, leaders, main_menu_quick_replies(recipient_id))


    #-- trade status replies
    elif message_text.lower() in Const.RESERVED_TRADES_REPLIES.split("|"):
        trades = {
            'open'     : 0,
            'refunded' : 0,
            'banned'   : 0,
            'traded'   : 0
        }
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `claim_state`  FROM `purchases` WHERE `user_id` = %s LIMIT 1;', (customer.id,))

                for row in cur.fetchall():
                    if row['claim_state'] == 0:
                        trades['open'] += 1

                    elif row['claim_state'] == 1:
                        trades['traded'] += 1

                    elif row['claim_state'] == 3:
                        trades['refunded'] += 1

                    elif row['claim_state'] == 5:
                        trades['banned'] += 1

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(recipient_id, "You have {open_total} trade{p1} outstanding, {refund_total} refund{p2}, and {banned_total} rejected.".format(open_total=trades['open'], p1="" if trades['open'] == 1 else "s", refund_total=trades['refunded'], p2="" if trades['refunded'] == 1 else "s", banned_total=trades['banned']))
        send_text(recipient_id, "Trades may be rejected from abuse, spamming the system, or a dramatic change in market place prices.", main_menu_quick_replies(recipient_id))

    #-- moderator reply
    elif message_text.lower() in Const.RESERVED_MODERATOR_REPLIES.split("|"):
        send_text(recipient_id, "You have signed up to be a mod. We will send you details shortly. ", main_menu_quick_replies(recipient_id))

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `id` FROM `moderators` WHERE `fb_psid` = %s LIMIT 1;', (recipient_id,))

                if cur.fetchone() is None:
                    cur.execute('INSERT INTO `moderators` (`id`, `user_id`, `fb_psid`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());', (customer.id, customer.fb_psid))
                    conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


    #-- giveaway reply
    elif message_text.lower() in Const.RESERVED_GIAVEAWAY_REPLIES.split("|"):
        product_name = None
        image_url = None
        total = 0
        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `id` FROM `giveaways` WHERE `fb_psid` = %s AND `added` >= UTC_DATE() LIMIT 1;', (recipient_id,))

                if cur.fetchone() is None:
                    cur.execute('INSERT INTO `giveaways` (`id`, `user_id`, `fb_psid`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());', (customer.id, customer.fb_psid))
                    conn.commit()

                cur.execute('SELECT COUNT(*) AS `total` FROM `giveaways` WHERE `added` >= UTC_DATE() LIMIT 1;')
                total = max(0, cur.fetchone()['total'] - 1)

                with open("/var/www/FacebookBot/FacebookBot/data/txt/giveaways.txt") as fp:
                    for i, line in enumerate(fp):
                        if i == datetime.now().day:
                            product_name = line.split(",")[0]
                            image_url = line.split(",")[-1]
                            break

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_tracker(fb_psid=recipient_id, category="transaction", label="giveaway")
        send_tracker(fb_psid=customer.fb_psid, category="giveaway", label=product_name)
        send_text(recipient_id, "You have completed a giveaway entry with {total} other player{suff}. You will be messaged here when the winner is selected.\n\nToday's extra item is:\n{product_name}".format(total=locale.format('%d', total, grouping=True), suff="" if total == 1 else "s", product_name=product_name), main_menu_quick_replies(recipient_id))
        send_image(customer.fb_psid, image_url, quick_replies=main_menu_quick_replies(recipient_id))

    #-- reserved points reply
    elif message_text.lower() in Const.RESERVED_POINTS_REPLIES.split("|"):
        rank, points = customer_points_rank(recipient_id)
        send_text(recipient_id, "You have {points} Lmon8 Points & are Ranked #{rank}.".format(points=locale.format('%d', points, grouping=True), rank=locale.format('%d', rank, grouping=True)), main_menu_quick_replies(recipient_id))

    #-- appnext reply
    elif message_text.lower() in Const.RESERVED_APPNEXT_REPLIES.split("|"):
        send_text(recipient_id, "Instructions…\n\n1. GO: taps.io/skins\n\n2. OPEN & Screenshot each free game or app you install.\n\n3. SEND screenshots for proof on Twitter.com/gamebotsc \n\nEvery free game or app you install increases your chances of winning.", main_menu_quick_replies(recipient_id))

    # -- kik reply
    elif message_text.lower() in Const.RESERVED_KIK_REPLIES.split("|"):
        customer.kik_name = "_{PENDING}_"
        db.session.commit()
        send_text(recipient_id, "Make a new Kik account so our mods can log into your account and confirm your sends.\n\nEnter your kik username")

    #-- tasks reply
    elif message_text.lower() in Const.RESERVED_ICO_REPLIES.split("|"):
        send_ico_info(recipient_id)

    #-- autogenerate shop
    elif message_text.lower() in Const.RESERVED_BONUS_AUTO_GEN_REPLIES.split("|"):
        storefront, product = autogen_template_storefront(recipient_id, message_text)

        send_text(recipient_id, "Auto generated your shop {storefront_name}.".format(storefront_name=storefront.display_name_utf8))
        send_text(recipient_id, product.messenger_url)
        send_text(recipient_id, "Every 2 {product_name}s you sell you will earn 1 {product_name}.".format(product_name=product.display_name_utf8))
        send_admin_carousel(recipient_id)

    #-- quit message
    elif message_text.lower() in Const.RESERVED_OPTOUT_REPLIES.split("|"):
        clear_entry_sequences(recipient_id)
        send_text(recipient_id, Const.GOODBYE_MESSAGE)


    #-- all others
    else:
        # if customer.fb_name == "_{PENDING}_":
        #     purchase = Purchase.query.filter(Purchase.id == customer.purchase_id).first()
        #     if purchase is not None:
        #         customer.fb_name = message_text
        #         db.session.commit()
        #         route_purchase_dm(recipient_id, purchase, Const.DM_ACTION_SEND, "Contact me directly: https://m.me/{fb_name}".format(fb_name=customer.fb_name))
        #
        #     return "OK", 200


        #-- entered trade url
        if customer.trade_url == "_{PENDING}_":
            if re.search(r'.*steamcommunity\.com\/tradeoffer\/.*$', message_text) is not None:
                customer.trade_url = message_text
                db.session.commit()

                try:
                    conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('UPDATE `users` SET `trade_url` = %s WHERE `id` = %s LIMIT 1;', (message_text, customer.id))
                        conn.commit()

                except mysql.Error, e:
                    logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                finally:
                    if conn:
                        conn.close()

                send_trade_card(recipient_id)

            else:
                send_text(recipient_id, "Invalid URL, try again...", main_menu_quick_replies(recipient_id))
                return "OK", 200


        #-- entered alt social contact
        if customer.social == "_{PENDING}_":
            customer.social = message_text
            db.session.commit()

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('UPDATE `users` SET `social_other` = %s WHERE `id` = %s LIMIT 1;', (message_text, customer.id))
                    conn.commit()

            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

            send_text(recipient_id, "Line ID has been set to “{alt_social}”\n\nInstructions:\n1. Accept friend request from link for profile Lmon8.\n\n2. Wait 6 hours.".format(alt_social=customer.social))
            send_customer_carousel(recipient_id, customer.product_id)
            return "OK", 200

        #-- support
        if customer.paypal_name == "__{PENDING}__":
            customer.paypal_name = None
            db.session.commit()

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('UPDATE `users` SET `support` = UTC_TIMESTAMP() WHERE `id` = %s LIMIT 1;', (customer.id,))
                    conn.commit()

            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

            send_text(recipient_id, "Your message has been sent to support. We have received your support message and will reply as soon as we can. If want to be a support mod you can help speed this up. Note you can only submit 1 support request every 24 hours.", main_menu_quick_replies(recipient_id))

            fb_user = FBUser.query.filter(FBUser.fb_psid == recipient_id).first()
            slack_outbound(
                channel_name="support-001",
                message_text="*Support Request*\n_{full_name} ({fb_psid}) says:_\n{message_text}".format(full_name=fb_user.full_name_utf8, fb_psid=recipient_id, message_text=message_text),
                webhook=Const.SLACK_SUPPORT_WEBHOOK
            )

            return "OK", 200

        #-- kik referral
        if customer.kik_name == "_{PENDING}_":
            customer.kik_name = message_text
            db.session.commit()

            send_text(recipient_id, "Open game.bots on kik and tap the referral url", main_menu_quick_replies(recipient_id))

            payload = {
                'fb_psid'  : recipient_id,
                'kik_name' : customer.kik_name
            }
            response = requests.post("http://api.coolkikapps.pw/whitelist_user.php", data=payload)
            logger.info(":::::::::::::::::::] -QUERY- " % response.json())

            return "OK", 200

        #-- entering paypal payout info
        if customer.paypal_email == "_{PENDING}_":
            customer.paypal_email = message_text
            db.session.commit()
            send_text(
                recipient_id=recipient_id,
                message_text="Are you sure your username is {paypal_email}?".format(paypal_email=customer.paypal_email),
                quick_replies=[
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Yes", Const.PB_PAYLOAD_DISNEY_YES),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "No", Const.PB_PAYLOAD_DISNEY_NO),
                ] + cancel_entry_quick_reply()
            )
            return "OK", 200


        #-- entering bitcoin payout
        if customer.bitcoin_addr == "_{PENDING}_":
            if re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', message_text) is None:
                send_text(recipient_id, "Invalid bitcoin address, it needs to start w/ 1 or 3, and be between 26 & 35 characters long.", quick_replies=cancel_entry_quick_reply())
                return "OK", 200

            else:
                customer.bitcoin_addr = message_text
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

        #-- check for in-progress points convert
        if customer.input_state == 1:
            if re.search('^(\d+)$', message_text) is not None:
                points = min(customer.points, int(re.match(r'^(?P<points>\d+)$', message_text).group('points')))
                customer.input_state = points
                db.session.commit()

                send_text(
                    recipient_id=recipient_id,
                    message_text="Are you sure you want to transfer {points} number of points to reserve {tokens} Lmon8 tokens?".format(points=locale.format('%d', points, grouping=True), tokens=locale.format('%.5f', (points / float(Const.POINTS_PER_DOLLAR)) * Const.TOKENS_PER_DOLLAR, grouping=True)),
                    quick_replies=[
                        build_quick_reply(Const.KWIK_BTN_TEXT, "Yes", Const.PB_PAYLOAD_CONVERT_YES),
                        build_quick_reply(Const.KWIK_BTN_TEXT, "No", Const.PB_PAYLOAD_CONVERT_NO)
                    ]
                )

            else:
                send_text(recipient_id, "Invalid number, try again", cancel_entry_quick_reply())
                
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

                            send_text(recipient_id, "That name is already taken, please choose another" if row is not None else "Enter a price. (example $9.99)", cancel_entry_quick_reply())

                    except mysql.Error, e:
                        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                    finally:
                        if conn:
                            conn.close()


                elif product.creation_state == 2:
                    if re.sub(r'[\$\.,\ ]', "", message_text).isdigit():
                        product.creation_state = 4
                        product.price = round(float(re.sub(r'[\$\.,\ ]', "", message_text)), 2)

                        product.release_date = calendar.timegm((datetime.utcnow() + relativedelta(months=0)).replace(hour=0, minute=0, second=0, microsecond=0).utctimetuple())
                        db.session.commit()

                        send_text(
                            recipient_id=recipient_id,
                            message_text="Are you selling in-game items or stickers?",
                            quick_replies=[
                                build_quick_reply(Const.KWIK_BTN_TEXT, "In-Game", Const.PB_PAYLOAD_PRODUCT_TYPE_GAME_ITEM),
                                build_quick_reply(Const.KWIK_BTN_TEXT, "Stickers", Const.PB_PAYLOAD_PRODUCT_TYPE_STICKER),
                                build_quick_reply(Const.KWIK_BTN_TEXT, "Skip", Const.PB_PAYLOAD_PRODUCT_TYPE_SKIP),
                            ] + cancel_entry_quick_reply()
                        )

                    else:
                        send_text(recipient_id, "Enter a price. (example $9.99)", cancel_entry_quick_reply())

                #-- entered text at wrong step
                else:
                    handle_wrong_reply(recipient_id)

                return "OK", 200


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

                            send_text(recipient_id, "That name is already taken, please choose another" if row is not None else "Give your shop a description.", cancel_entry_quick_reply())

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

                    send_text(recipient_id, "Upload a profile image.", cancel_entry_quick_reply())

                #-- entered text at wrong step
                else:
                    handle_wrong_reply(recipient_id)

                return "OK", 200

            else:
                welcome_message(recipient_id, Const.ENTRY_PRODUCT_REFERRAL, message_text)

    return "OK", 200


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
            send_text(recipient_id, "Give your shop a name.", cancel_entry_quick_reply())

        elif storefront.creation_state == 1:
            send_text(recipient_id, "Give your shop a description.", cancel_entry_quick_reply())

        elif storefront.creation_state == 2:
            send_text(recipient_id, "Upload a profile image.", cancel_entry_quick_reply())

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
                send_text(recipient_id, "Upload a video or image of the item you are selling.", cancel_entry_quick_reply())

            elif product.creation_state == 1:
                send_text(recipient_id, "Give your item a title.", cancel_entry_quick_reply())

            elif product.creation_state == 2:
                send_text(recipient_id, "Enter a price. (example $9.99)".format(product_name=product.display_name_utf8), cancel_entry_quick_reply())

            elif product.creation_state == 3:
                send_text(
                    recipient_id=recipient_id,
                    message_text="Select a date the item will be available.",
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
                    message_text="Are you selling in-game items or stickers?",
                    quick_replies=[
                        build_quick_reply(Const.KWIK_BTN_TEXT, "In-Game", Const.PB_PAYLOAD_PRODUCT_TYPE_GAME_ITEM),
                        build_quick_reply(Const.KWIK_BTN_TEXT, "Stickers", Const.PB_PAYLOAD_PRODUCT_TYPE_STICKER),
                        build_quick_reply(Const.KWIK_BTN_TEXT, "Skip", Const.PB_PAYLOAD_PRODUCT_TYPE_SKIP)
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
                send_text(recipient_id, "Here's what your item will look like:")
                send_product_card(recipient_id, product.id, Const.CARD_TYPE_PRODUCT_PREVIEW)

    return "OK", 200


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


@app.route('/', methods=['POST'])
def webhook():

    #if 'delivery' in request.data or 'read' in request.data or 'optin' in request.data:
    #return "OK", 200

    data = request.get_json()

    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
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

                if sender_id == "1426425780755191" or sender_id == "1513404505377049" or sender_id == "1203828066395166" or sender_id == "1203828066395166":
                    logger.info("-=- BYPASS-USER -=-")
                    return "OK", 200

                if 'echo' in messaging_event:
                    logger.info("-=- MESSAGE-ECHO -=-")
                    return "OK", 200

                if 'delivery' in messaging_event:
                    # logger.info("-=- DELIVERY-CONFIRM -=-")
                    return "OK", 200

                if 'read' in messaging_event:
                    # logger.info("-=- READ-CONFIRM -=- %s" % (recipient_id))
                    # send_tracker(fb_psid=sender_id, category="read-receipt")
                    return "OK", 200

                if 'optin' in messaging_event:
                    # logger.info("-=- OPT-IN -=-")
                    return "OK", 200

                # send_tracker(fb_psid=sender_id, category="active")


                referral = None if 'referral' not in messaging_event else messaging_event['referral']['ref'].encode('ascii', 'ignore')
                if referral is None and 'postback' in messaging_event and 'referral' in messaging_event['postback']:
                    referral = messaging_event['postback']['referral']['ref'].encode('ascii', 'ignore')

                #-- check mysql for user
                customer = sync_user(sender_id, referral)

                #-- entered via url referral
                if referral is not None:
                    entry_type = Const.ENTRY_PRODUCT_REFERRAL
                    if referral[1:] in Const.RESERVED_AUTO_GEN_STOREFRONTS:
                        entry_type = Const.ENTRY_STOREFRONT_AUTO_GEN

                    elif re.search(r'^\/ref\/(\d+)$', referral or "/") is not None:
                        entry_type = Const.ENTRY_USER_REFERRAL

                    elif re.search(r'^\/giveaway((\/twitter)|(\/snapchat)|(\/discord))?$', referral or "/") is not None:
                        entry_type = Const.ENTRY_GIVEAWAY_REFERRAL

                    elif re.search(r'^\/gb\/(.+)$', referral or "/") is not None:
                        entry_type = Const.ENTRY_GAMEBOTS_REFERRAL

                    elif re.search(r'^\/ico$', referral or "/") is not None:
                        entry_type = Const.ENTRY_ICO_REFERRAL

                    welcome_message(customer.fb_psid, entry_type, referral)
                    return "OK", 200


                #-- users data
                logger.info("\n=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
                logger.info("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
                logger.info("CUSTOMER -->%s" % (customer))
                logger.info("FB_USER -->%s" % (FBUser.query.filter(FBUser.fb_psid == customer.fb_psid).all()))
                #logger.info("PURCHASED -->%s" % (Purchase.query.filter(Purchase.customer_id == customer.id).all()))


                logger.info("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
                logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n")


                #-- catch all
                # if customer.fb_psid not in Const.ADMIN_FB_PSIDS:
                #     send_text(customer.fb_psid, "Lmon8 is currently down for maintenance.")
                #     return "OK", 200

                #-- payment response
                if 'payment' in messaging_event:
                    logger.info("-=- PAYMENT -=- (%s)" % (messaging_event['payment']))
                    received_fb_payment(customer, messaging_event['payment'])
                    return "OK", 200

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
        if re.search('^(\d+)\ points\ (\-?\d+)$', request.form['text'].lower()) is not None:
            fb_psid = re.match(r'(?P<fb_psid>\d+)\ points\ (?P<amount>\-?\d+)$', request.form['text'].lower()).group('fb_psid')
            amount = int(re.match(r'(?P<fb_psid>\d+)\ points\ (?P<amount>\-?\d+)$', request.form['text'].lower()).group('amount'))
            add_points(fb_psid, amount)

            if amount > 0:
                send_text(fb_psid,"You have just been rewarded {points} pts!".format(points=locale.format('%d', amount, grouping=True)), main_menu_quick_replies(fb_psid))

        elif re.search('^(\d+)\ close$', request.form['text'].lower()) is not None:
            fb_psid = re.match(r'(?P<fb_psid>\d+)\ close$', request.form['text'].lower()).group('fb_psid')

            customer = Customer.query.filter(Customer.fb_psid == fb_psid).first()
            if customer is not None:
                customer.paypal_name = None
                db.session.commit()

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('UPDATE `users` SET `support` = "0000-00-00 00:00:00" WHERE `fb_psid` = %s LIMIT 1;', (fb_psid,))
                    send_text(fb_psid, "Support ticket closed", main_menu_quick_replies(fb_psid))

            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

        elif re.search('^(\d+)\ unlock$', request.form['text'].lower()) is not None:
            fb_psid = re.match(r'(?P<fb_psid>\d+)\ (?P<message_text>.*)$', request.form['text']).group('fb_psid')

            customer = Customer.query.filter(Customer.fb_psid == fb_psid).first()
            if customer is not None:
                customer.locked = 0
                db.session.commit()

                try:
                    conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('INSERT INTO `unlocked_users` (`id`, `user_id`, `fb_psid`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());', (customer.id, customer.fb_psid))
                        conn.commit()

                except mysql.Error, e:
                    logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

                finally:
                    if conn:
                        conn.close()

            send_text(fb_psid, "Your Lmon8 account has been unlocked!", main_menu_quick_replies(fb_psid))

        elif re.search('^(\d+)\ (.*)$', request.form['text']) is not None:
            fb_psid = re.match(r'(?P<fb_psid>\d+)\ (?P<message_text>.*)$', request.form['text']).group('fb_psid')
            message_text = re.match(r'(?P<fb_psid>\d+)\ (?P<message_text>.*)$', request.form['text']).group('message_text')

            send_text(fb_psid, "Support says:\n{message_text}".format(message_text=message_text), main_menu_quick_replies(fb_psid))

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('UPDATE `users` SET `support` = "0000-00-00 00:00:00" WHERE `fb_psid` = %s LIMIT 1;', (fb_psid,))

            except mysql.Error, e:
                logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

    return "OK", 200


# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


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
                    cur.execute('UPDATE `purchases` SET `paid` = 1 WHERE `id` = %s LIMIT 1;', (purchase.id,))
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
            add_points(customer.fb_psid, product.price * Const.POINTS_PER_DOLLAR)

            slack_outbound(
                channel_name="lemonade-purchases",
                message_text="*{customer}* *({fb_psid})* just purchased _{product_name}_ for ${price:.2f} from _{storefront_name}_ via PayPal.".format(fb_psid=customer.fb_psid, customer=customer.fb_psid if fb_user is None else fb_user.full_name_utf8, product_name=product.display_name_utf8, price=product.price, storefront_name=storefront.display_name_utf8),
                webhook=Const.SLACK_PURCHASES_WEBHOOK
            )

            customer = Customer.query.filter(Customer.id == customer_id).first()
            send_text(customer.fb_psid, "Point Pack purchase completed, you now have a total of {points} pts available.".format(points=locale.format('%d', customer.points, grouping=True)))
            send_product_card(customer.fb_psid, customer.product_id, Const.CARD_TYPE_PRODUCT_CHECKOUT)

    return "OK", 200


# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


@app.route('/steam/', methods=['POST'])
def steam():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/steam/'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.STEAM_TOKEN:
        logger.info("TOKEN VALID!")

        fb_psid = request.form['fb_psid']
        steam_id64 = request.form['steam_id64']

        logger.info("fb_psid=%s, steam_id64=%s" % (fb_psid, steam_id64))
        send_tracker(fb_psid=fb_psid, category="sign-up", label="steam")

        customer = Customer.query.filter(Customer.fb_psid == fb_psid).first()
        if customer is not None:
            customer.steam_id64 = steam_id64

            if customer.trade_url is None:
                customer.trade_url = "_{PENDING}_"
                db.session.commit();

                send_text(fb_psid, "Steam had been connected to your Lmon8 account, enter your trade url now.")

            else:
                send_text(
                    recipient_id=customer.fb_psid,
                    message_text="Steam Trade URL set to {trade_url}\n\nWould you like to change it?".format(trade_url=customer.trade_url),
                    quick_replies=[
                        build_quick_reply(Const.KWIK_BTN_TEXT, "OK", payload=Const.PB_PAYLOAD_TRADE_URL),
                        build_quick_reply(Const.KWIK_BTN_TEXT, "Keep", payload=Const.PB_PAYLOAD_TRADE_URL_KEEP),
                    ]
                )

    return "OK", 200


# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#



@app.route('/trader/', methods=['POST'])
def trader():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/trader/'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.TRADER_TOKEN:
        logger.info("TOKEN VALID!")

        user_id = request.form['user_id']
        item_name = request.form['item_name']
        price = float(request.form['price'])

        logger.info("user_id=%s, item_name=%s, price=%s" % (user_id, item_name, price))

        fb_psid = None

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `fb_psid` FROM `users` WHERE `id` = %s LIMIT 1;', (user_id,))
                row = cur.fetchone()
                if row is not None:
                    fb_psid = row['fb_psid']

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        points = price * Const.POINTS_PER_DOLLAR
        customer = Customer.query.filter(Customer.fb_psid == fb_psid).first()
        if customer is not None:
            customer.input_state = points
            customer.locked = 0
            db.session.commit()

        send_text(
            recipient_id=fb_psid,
            message_text="Received your item {item_name}, you can now purchase items from Lmon8. {points} PTS have been added to your Lmon8 account. Would you like to use these PTS to purchase Lmon8 tokens?".format(item_name=item_name, points=locale.format('%d', points, grouping=True)),
            quick_replies=[
                build_quick_reply(Const.KWIK_BTN_TEXT, "Yes", Const.PB_PAYLOAD_CONVERT_YES),
                build_quick_reply(Const.KWIK_BTN_TEXT, "No", Const.PB_PAYLOAD_CANCEL_ENTRY_SEQUENCE)
            ]
        )
        add_points(fb_psid, points)

        send_tracker(fb_psid=fb_psid, category="transaction", label="deposit")
        # send_tracker(fb_psid=fb_psid, category="trade", label=item_name)
        send_tracker(fb_psid=fb_psid, category="deposit", label=item_name)

    return "OK", 200



# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


@app.route('/giveaway/', methods=['POST'])
def giveaway():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/giveaway/'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.GIVEAWAY_TOKEN:
        logger.info("TOKEN VALID!")

        fb_psid = request.form['fb_psid']
        #send_mystery_flip_card(fb_psid, True)


        # try:
        #     conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
        #     with conn:
        #         cur = conn.cursor(mysql.cursors.DictCursor)
        #         cur.execute('SELECT `id` FROM `giveaways` WHERE `product_id` = 1 AND `added` >= UTC_DATE();')
        #         if cur.fetchone() is None:
        #             with open("/var/www/FacebookBot/FacebookBot/data/txt/giveaways.txt") as fp:
        #                 for i, line in enumerate(fp):
        #                     if i == datetime.now().day:
        #                         product_name = line.split(",")[0]
        #                         image_url = line.split(",")[-1]
        #                         break
        #
        #             cur.execute('SELECT `id` FROM `products` WHERE `display_name` LIKE %s ORDER BY `added` LIMIT 1;', ("%{product_name}%".format(product_name=product_name),))
        #             row = cur.fetchone()
        #             if row is not None:
        #                 product_id = row['id']
        #
        #             cur.execute('SELECT `id`, `fb_psid` FROM `giveaways` WHERE `added` >= UTC_DATE() ORDER BY RAND() LIMIT 1;')
        #             row = cur.fetchone()
        #             if row is not None:
        #                 giveaway_id = row['id']
        #                 fb_psid = row['fb_psid']
        #
        #             cur.execute('UPDATE `giveaways` SET `product_id` = %s WHERE `id` = %s LIMIT 1;', (product_id, giveaway_id))
        #             conn.commit()
        #
        #
        # except mysql.Error, e:
        #     logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))
        #
        # finally:
        #     if conn:
        #         conn.close()

        # send_text(fb_psid, "".format(item_name=item_name, points=locale.format('%d', points, grouping=True)), main_menu_quick_replies(fb_psid))

    return "OK", 200




# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


@app.route('/user-add-points', methods=['POST'])
def user_add_points():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/user-add-points'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.USER_ADD_POINTS_TOKEN:
        logger.info("TOKEN VALID!")
        add_points(request.form['fb_psid'], int(request.form['points']))
        send_text(
            recipient_id=request.form['fb_psid'],
            message_text="You have just been rewarded {points} pts!".format(points=locale.format('%d', int(request.form['points']), grouping=True)),
            quick_replies=main_menu_quick_replies(request.form['fb_psid'])
        )

    return "OK", 200


# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


@app.route('/autogen-storefront', methods=['POST'])
def autogen_storefront():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/autogen-storefront'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.IMPORT_STOREFRONT_TOKEN:
        logger.info("TOKEN VALID!")


        customer = Customer.query.filter(Customer.fb_psid == request.form['fb_psid']).first()
        if customer is None:
            customer = Customer(request.form['fb_psid'])
            db.session.add(customer)
            db.session.commit()


        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `storefront_id` FROM `products` WHERE `tags` LIKE %s AND `enabled` = 1 ORDER BY RAND() LIMIT 1;', ("%{tag}%".format(tag="autogen-import"),))
                row = cur.fetchone()
                if row is not None:
                    storefront, product = clone_storefront(customer.fb_psid, row['storefront_id'])


        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

    return "OK", 200

# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#





@app.route('/import-storefront', methods=['POST'])
def import_storefront():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/import-storefront'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.IMPORT_STOREFRONT_TOKEN:
        logger.info("TOKEN VALID!")

        customer = Customer.query.filter(Customer.fb_psid == request.form['fb_psid']).first()

        if Storefront.query.filter(Storefront.fb_psid == request.form['fb_psid']).count() > 0:
            for storefront in Storefront.query.filter(Storefront.fb_psid == request.form['fb_psid']):
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
                Storefront.query.filter(Storefront.fb_psid == request.form['fb_psid']).delete()
                db.session.commit()
            except:
                db.session.rollback()


        display_name = "{prefix} - {suffix}".format(prefix=request.form['storefront.display_name'], suffix=request.form['fb_psid'][-4:])
        storefront = Storefront(request.form['fb_psid'], Const.STOREFRONT_TYPE_IMPORT_GEN)
        storefront.name = re.sub(Const.IGNORED_NAME_PATTERN, "", display_name.encode('ascii', 'ignore'))
        storefront.display_name = display_name
        storefront.description = request.form['storefront.description']
        storefront.logo_url = request.form['storefront.logo_url']
        storefront.prebot_url = "http://prebot.me/{storefront_name}".format(storefront_name=storefront.name)
        storefront.creation_state = 4
        db.session.add(storefront)
        db.session.commit()

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT * FROM `storefronts` WHERE `name` = %s AND `enabled` = 1;', (storefront.name,))
                if cur.fetchone() is None:
                    cur.execute('INSERT INTO `storefronts` (`id`, `owner_id`, `type`, `name`, `display_name`, `description`, `logo_url`, `prebot_url`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP());', (0 if customer is None else customer.id, storefront.type_id, storefront.name, storefront.display_name_utf8, storefront.description_utf8, storefront.logo_url, storefront.prebot_url))
                    conn.commit()
                    cur.execute('SELECT @@IDENTITY AS `id` FROM `storefronts`;')
                    storefront.id = cur.fetchone()['id']
                    storefront.added = int(time.time())
                    db.session.commit()

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        display_name = "{prefix} - {suffix}".format(prefix=request.form['product.display_name'], suffix=request.form['fb_psid'][-4:])
        product = Product(request.form['fb_psid'], storefront.id)
        product.name = re.sub(Const.IGNORED_NAME_PATTERN, "", display_name.encode('ascii', 'ignore'))
        product.display_name = display_name
        product.release_date = calendar.timegm((datetime.utcnow() + relativedelta(months=0)).replace(hour=0, minute=0, second=0, microsecond=0).utctimetuple())
        product.description = request.form['product.description'] or "For sale starting on {release_date}".format(release_date=datetime.utcfromtimestamp(product.release_date).strftime('%a, %b %-d'))
        product.type_id = Const.PRODUCT_TYPE_GAME_ITEM
        product.image_url = request.form['product.image_url']
        product.video_url = None
        product.attachment_id = None
        product.prebot_url = "http://prebot.me/{product_name}".format(product_name=product.name)
        product.price = request.form['product.price']
        product.tags = "autogen-import"
        product.creation_state = 7
        db.session.add(product)
        db.session.commit()

        try:
            conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT * FROM `products` WHERE `name` = %s AND `enabled` = 1;', (product.name,))
                if cur.fetchone() is None:
                    cur.execute('INSERT INTO `products` (`id`, `storefront_id`, `type`, `name`, `display_name`, `description`, `tags`, `image_url`, `video_url`, `attachment_id`, `price`, `prebot_url`, `physical_url`, `release_date`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s), UTC_TIMESTAMP());', (product.storefront_id, product.type_id, product.name, product.display_name_utf8, product.description, product.tags.encode('utf-8'), product.image_url, product.video_url or "", product.attachment_id or "", product.price, product.prebot_url, "", product.release_date))
                    conn.commit()
                    cur.execute('SELECT @@IDENTITY AS `id` FROM `products`;')
                    product.id = cur.fetchone()['id']
                    product.added = int(time.time())
                    db.session.commit()

        except mysql.Error, e:
            logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


    return "OK", 200


@app.route('/refund', methods=['POST'])
def refund():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/refund'")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.REFUND_TOKEN:
        logger.info("TOKEN VALID!")

        add_points(request.form['fb_psid'], int(request.form['points']))
        send_text(
            recipient_id=request.form['fb_psid'],
            message_text="Your recently purchased of {product_name} ({points} Pts) has been refunded as there has been a change in the market place & the item is no longer at that price.".format(product_name=request.form['product_name'], points=locale.format('%d', int(request.form['points']), grouping=True)),
            quick_replies=main_menu_quick_replies(request.form['fb_psid'])
        )

        try:
            Purchase.query.filter(Purchase.id == request.form['purchase_id']).delete()
            db.session.commit()
        except:
            db.session.rollback()


    return "OK", 200


# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


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
        url="https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN),
        headers={ 'Content-Type' : "application/json" },
        data=payload
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
