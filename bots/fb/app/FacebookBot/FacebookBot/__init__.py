#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import calendar
import hashlib
import json
import locale
import logging
import os
import re
import sqlite3
import subprocess
import threading
import time

from datetime import datetime

import MySQLdb as mysql
import requests
import pytz
import stripe

from dateutil.relativedelta import relativedelta
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
from stripe import CardError

from constants import Const


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data/sqlite3/prebotfb.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

locale.setlocale(locale.LC_ALL, 'en_US.utf8')

# reload(sys)
# sys.setdefaultencoding('utf8')

db = SQLAlchemy(app)
db.text_factory = str

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler("/var/log/FacebookBot.log")
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

stripe.api_key = Const.STRIPE_DEV_API_KEY


#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fb_psid = db.Column(db.String(255))
    fb_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    referrer = db.Column(db.String(255))
    paypal_email = db.Column(db.String(255))
    bitcoin_addr = db.Column(db.String(255))
    stripe_id = db.Column(db.String(255))
    card_id = db.Column(db.String(255))
    bitcoin_id = db.Column(db.String(255))
    storefront_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    purchase_id = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, id, fb_psid, referrer="/"):
        self.id = id
        self.fb_psid = fb_psid
        self.referrer = referrer
        self.added = int(time.time())

    def __repr__(self):
        return "<Customer id=%s, fb_psid=%s, fb_name=%s, email=%s, bitcoin_addr=%s, referrer=%s, paypal_email=%s, storefront_id=%s, product_id=%s, purchase_id=%s, added=%s>" % (self.id, self.fb_psid, self.fb_name, self.email, self.bitcoin_addr, self.referrer, self.paypal_email, self.storefront_id, self.product_id, self.purchase_id, self.added)


class Payment(db.Model):
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
        return "<Payment id=%d, fb_psid=%s, source=%s, email=%s, full_name=%s, acct_number=%s, expiration=%s, cvc=%s, creation_state=%d, added=%d" % (self.id, self.fb_psid, self.source, self.email, self.full_name, self.acct_number, self.expiration, self.cvc, self.creation_state, self.added)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    storefront_id = db.Column(db.Integer)
    creation_state = db.Column(db.Integer)
    name = db.Column(db.String(255))
    display_name = db.Column(db.String(255))
    description = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    broadcast_message = db.Column(db.String(255))
    attachment_id = db.Column(db.String(255))
    price = db.Column(db.Float)
    prebot_url = db.Column(db.String(255))
    views = db.Column(db.String(255))
    avg_rating = db.Column(db.Float)
    release_date = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, storefront_id):
        self.storefront_id = storefront_id
        self.creation_state = 0
        self.price = 1.99
        self.views = 0
        self.avg_rating = 0.0
        self.added = int(time.time())

    @property
    def messenger_url(self):
        return re.sub(r'^.*\/(.*)$', r'm.me/prebotme?ref=/\1', self.prebot_url)

    @property
    def thumb_image_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-256.\2', self.image_url)

    @property
    def landscape_image_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-400.\2', self.image_url)

    @property
    def widescreen_image_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-1280.\2', self.image_url)

    @property
    def portrait_image_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-480.\2', self.image_url)

    def __repr__(self):
        return "<Product id=%d, storefront_id=%d, creation_state=%d, display_name=%s, image_url=%s, video_url=%s, prebot_url=%s, release_date=%s, views=%d, avg_rating=%.2f, added=%d>" % (self.id, self.storefront_id, self.creation_state, self.display_name, self.image_url, self.video_url, self.prebot_url, self.release_date, self.views, self.avg_rating, self.added)


class Purchase(db.Model):
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

    @property
    def messenger_url(self):
        return re.sub(r'^.*\/(.*)$', r'm.me/prebotme?ref=/\1', self.prebot_url)

    def __repr__(self):
        return "<Purchase id=%d, customer_id=%d, storefront_id=%d, product_id=%d, type=%s, charge_id=%s, claim_state=%d, added=%d>" % (self.id, self.customer_id, self.storefront_id, self.product_id, self.type, self.charge_id, self.claim_state, self.added)


class Rating(db.Model):
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
        return "<Rating id=%d, product_id=%d, fb_psid=%s, stars=%d, added=%d>" % (self.id, self.product_id, self.fb_psid, self.stars, self.added)


class Storefront(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.String(255))
    creation_state = db.Column(db.Integer)
    type = db.Column(db.Integer)
    name = db.Column(db.String(255))
    display_name = db.Column(db.String(255))
    description = db.Column(db.String(255))
    logo_url = db.Column(db.String(255))
    video_url = db.Column(db.String(255))
    prebot_url = db.Column(db.String(255))
    giveaway = db.Column(db.Integer)
    views = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, owner_id, type=1):
        self.owner_id = owner_id
        self.creation_state = 0
        self.type = type
        self.giveaway = 0
        self.added = int(time.time())

    @property
    def messenger_url(self):
        return re.sub(r'^.*\/(.*)$', r'm.me/prebotme?ref=/\1', self.prebot_url)

    @property
    def thumb_logo_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-256.\2', self.logo_url)

    @property
    def landscape_logo_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-400.\2', self.logo_url)

    @property
    def widescreen_logo_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-1280.\2', self.logo_url)

    @property
    def protrait_logo_url(self):
        return re.sub(r'^(.*)\.(.{2,})$', r'\1-480.\2', self.image_url)


    def __repr__(self):
        return "<Storefront id=%s, owner_id=%s, creation_state=%s, display_name=%s, logo_url=%s, video_url=%s, prebot_url=%s, giveaway=%s, added=%s>" % (self.id, self.owner_id, self.creation_state, self.display_name, self.logo_url, self.video_url, self.prebot_url, self.giveaway, self.added)


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    storefront_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    customer_id = db.Column(db.Integer)
    enabled = db.Column(db.Integer)
    added = db.Column(db.Integer)

    def __init__(self, storefront_id, product_id, customer_id):
        self.storefront_id = storefront_id
        self.product_id = product_id
        self.customer_id = customer_id
        self.enabled = 1
        self.added = int(time.time())

    def __repr__(self):
        return "<Subscription storefront_id=%d, product_id=%d, customer_id=%d, enabled=%d>" % (self.storefront_id, self.product_id, self.customer_id, self.enabled)


class ImageCopier(threading.Thread):
    def __init__(self, src_url, out_file=None):
        threading.Thread.__init__(self)
        self.src_url = src_url
        self.out_file = out_file

    def run(self):
        os.chdir(os.path.dirname(self.out_file))


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

            out_image = src_image.resize(scale_size, Image.BILINEAR).crop(area)
            os.chdir(os.path.dirname(self.out_file))
            out_image.save("{out_file}".format(out_file=("-{sq}.".format(sq=self.canvas_size[0])).join(self.out_file.split("/")[-1].split("."))))


class VideoImageRenderer(threading.Thread):
    def __init__(self, src_url, out_img, at_sec=3):
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
        stdout, stderr = p.communicate()


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

    connection = sqlite3.connect("{file_path}/data/sqlite3/prebotfb.db".format(file_path=os.path.dirname(os.path.realpath(__file__))))
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

def next_product_id(product=None):
    logger.info("next_product_id(product={product})".format(product=product))

    if product is not None:
        product.id = Product.query.filter(Product.creation_state < 5).order_by(Product.id.desc()).first().id + 1
        db.session.commit()

def next_storefront_id(storefront=None):
    logger.info("next_storefront_id(storefront={storefront})".format(storefront=storefront))

    if storefront is not None:
        storefront.id = Storefront.query.filter(Storefront.creation_state < 4).order_by(Storefront.id.desc()).first().id + 1
        db.session.commit()


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

    if deeplink is None:
        deeplink = "/"

    try:
        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            #-- check db for existing user
            cur.execute('SELECT `id` FROM `users` WHERE `fb_psid` = "{fb_psid}" LIMIT 1;'.format(fb_psid=recipient_id))
            row = cur.fetchone()

            #-- go ahead n' add 'em
            if row is None:
                cur.execute('INSERT INTO `users` (`id`, `fb_psid`, `referrer`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());' % (recipient_id, deeplink))
                conn.commit()
                cur.execute('SELECT `id`, `added` FROM `products` WHERE `id` = @@IDENTITY LIMIT 1;')
                row = cur.fetchone()

                #-- now update sqlite w/ the new guy
                customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
                if customer is None:
                    db.session.add(Customer(id=row['id'], fb_psid=recipient_id, referrer=deeplink))

                else:
                    customer.id = row['id']

            else:
                #-- now update sqlite w/ existing guy
                customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
                if customer is None:
                    db.session.add(Customer(id=row['id'], fb_psid=recipient_id, referrer=deeplink))

                else:
                    customer.id = row['id']

            db.session.commit()


    except mysql.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()


def add_subscription(recipient_id, storefront_id, product_id=0, deeplink="/"):
    logger.info("add_subscription(recipient_id={recipient_id}, storefront_id={storefront_id}, product_id={product_id}, deeplink={deeplink})".format(recipient_id=recipient_id, storefront_id=storefront_id, product_id=product_id, deeplink=deeplink))

    has_subscribed = False
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront = Storefront.query.filter(Storefront.id == storefront_id).first()
    product = Product.query.filter(Product.id == product_id).first()

    try:
        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `subscriptions` WHERE `user_id` = {user_id} AND `storefront_id` = {storefront_id} AND `product_id` = {product_id} LIMIT 1'.format(user_id=customer.id, storefront_id=storefront.id, product_id=product.id))
            row = cur.fetchone()
            has_subscribed = (row is None)

            if row is None:
                send_tracker("user-subscribe", recipient_id, storefront.display_name)

                cur.execute('INSERT INTO `subscriptions` (`id`, `user_id`, `storefront_id`, `product_id`, `deeplink`, `added`) VALUES (NULL, %s, %s, %s, %s, UTC_TIMESTAMP())' % (customer.id, storefront.id, product.id, ("/%s" % (deeplink))))
                conn.commit()

                subscription = Subscription(storefront.id, product.id, customer.id)
                subscription.id = cur.lastrowid
                db.session.add(subscription)

            else:
                subscription = Subscription.query.filter(Subscription.product_id == product.id).filter(Subscription.customer_id == customer.id).first()
                if subscription is None:
                    subscription = Subscription(storefront.id, product.id, customer.id)
                    db.session.add(subscription)

                subscription.id = row['id']
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
    return has_subscribed


def add_cc_payment(recipient_id):
    logger.info("add_cc_payment(recipient_id={recipient_id})".format(recipient_id=recipient_id))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

    payment = Payment.query.filter(Payment.fb_psid == recipient_id).filter(Payment.source == "card").first()
    if payment is None:
        payment = Payment(fb_psid=recipient_id, source="card")
        if customer.email is not None:
            payment.creation_state = 1

        db.session.add(payment)
        db.session.commit()

    logger.info("[:::|:::] CC PAYMENT:\n%s" % (payment))
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
            Payment.query.filter(Payment.id == payment.id).delete()
            db.session.commit()
            return False

        else:
            customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
            customer.stripe_id = stripe_customer.id
            customer.card_id = stripe_customer['sources']['data'][0]['id']
            Payment.query.filter(Payment.id == payment.id).delete()
            db.session.commit()

            try:
                conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('UPDATE `users` SET `email` = "{email}", `stripe_id` = "{stripe_id}", `card_id` = "{card_id}" WHERE `id` = {user_id} LIMIT 1;'.format(email=customer.email, stripe_id=customer.stripe_id, card_id=customer.card_id, user_id=customer.id))
                    conn.commit()

            except mysql.Error, e:
                logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

            finally:
                if conn:
                    conn.close()

            return True
    return False


def purchase_product(recipient_id):
    logger.info("purchase_product(recipient_id={recipient_id})".format(recipient_id=recipient_id))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    if customer is not None:
        storefront = Storefront.query.filter(Storefront.id == customer.storefront_id).first()
        product = Product.query.filter(Product.id == customer.product_id).first()
        stripe_charge = stripe.Charge.create(
            amount = int(product.price * 100),
            currency = "usd",
            customer = customer.stripe_id,
            source = customer.card_id,
            description = "Charge for {fb_psid} - {storefront_name} / {product_name}".format(fb_psid=customer.fb_psid, storefront_name=storefront.display_name, product_name=product.display_name)
        )

        #logger.info(":::::::::] CHARGE RESPONSE [:::::::::::\n%s" % (stripe_charge))

        if stripe_charge['status'] == "succeeded":
            send_tracker("purchase-complete", recipient_id, "")

            purchase = Purchase(customer.id, customer.storefront_id, customer.product_id, 1, stripe_charge.id)
            db.session.add(purchase)
            db.session.commit()

            try:
                conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('INSERT INTO `purchases` (`id`, `user_id`, `product_id`, `type`, `charge_id`, `transaction_id`, `refund_url`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP())' % (customer.id, 1, customer.product_id, purchase.charge_id, stripe_charge['balance_transaction'], stripe_charge['refunds']['url']))
                    conn.commit()
                    cur.execute('SELECT `id`, `added` FROM `products` WHERE `id` = @@IDENTITY LIMIT 1;')
                    row = cur.fetchone()

                    purchase.id = row['id']
                    customer.purchase_id = purchase.id
                    purchase.added = row['added']
                    db.session.commit()

            except mysql.Error, e:
                logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

            finally:
                if conn:
                    conn.close()

            send_text(
                recipient_id = storefront.owner_id,
                message_text = "Purchase complete for %s at %s.\nTo complete this order send the customer the item now.".format(product_name=product.display_name, pacific_time=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%I:%M%P %Z').lstrip("0")),
                quick_replies = [
                    build_quick_reply(Const.KWIK_BTN_TEXT, caption="Message Now", payload="%s-%s".format(payload=Const.PB_PAYLOAD_PURCHASE_MESSAGE, purchase_id=purchase.id)),
                    build_quick_reply(Const.KWIK_BTN_TEXT, caption="Not Now", payload=Const.PB_PAYLOAD_MAIN_MENU)
                ]
            )

            payload = {
                'channel' : "#pre",
                'username' : "fbprebot",
                'icon_url' : "https://scontent.fsnc1-4.fna.fbcdn.net/t39.2081-0/p128x128/15728018_267940103621073_6998097150915641344_n.png",
                'text' : "*{recipient_id}* just purchased {product_name} from _{storefront_name}_.".format(recipient_id=recipient_id, product_name=product.display_name, storefront_name=storefront.display_name),
                'attachments' : [{
                    'image_url' : product.image_url
                }]
            }
            response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })

            return True

        else:
            send_text(recipient_id, "Error making payment:\n{reason}".format(reason=stripe_charge['outcome']['reason']))

    return False



def write_message_log(recipient_id, message_id, message_txt):
    logger.info("write_message_log(recipient_id={recipient_id}, message_id={message_id}, message_txt={message_txt})".format(recipient_id=recipient_id, message_id=message_id, message_txt=message_txt))

    try:
        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('INSERT INTO `chat_logs` (`id`, `fbps_id`, `message_id`, `body`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP())' % (recipient_id, message_id, message_txt))
            conn.commit()

    except mysql.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()



def build_button(btn_type, caption="", url="", payload=""):
    logger.info("build_button(btn_type={btn_type}, caption={caption}, url={url}, payload={payload})".format(btn_type=btn_type, caption=caption, url=url, payload=payload))

    button = None
    if btn_type == Const.CARD_BTN_POSTBACK:
        button = {
            'type'    : Const.CARD_BTN_POSTBACK,
            'payload' : payload,
            'title'   : caption
        }

    elif btn_type == Const.CARD_BTN_URL:
        button = {
            'type'                 : Const.CARD_BTN_URL,
            'url'                  : url,
            'title'                : caption
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


def build_card_element(title, subtitle=None, image_url=None, item_url=None, buttons=None):
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

def build_list_elements(body_elements, header_element=None):
    logger.info("build_list_elements(body_elements={body_elements}, header_element={header_element})".format(body_elements=body_elements, header_element=header_element))

    elements = []
    if header_element is not None:
        elements.append(header_element)

    for element in body_elements:
        elements.append(element)

    return elements


def build_receipt_card(recipient_id, purchase_id):
    logger.info("build_receipt_card(recipient_id={recipient_id}, purchase_id={purchase_id})".format(recipient_id=recipient_id, purchase_id=purchase_id))

    data = None
    purchase_query = Purchase.query.filter(Purchase.id == purchase_id)
    if purchase_query.count() > 0:
        purchase = purchase_query.first()
        customer = Customer.query.filter(Customer.id == purchase.customer_id).first()
        storefront = Storefront.query.filter(Storefront.id == purchase.storefront_id).first()
        product = Product.query.filter(Product.id == purchase.product_id).order_by(Product.added.desc()).first()
        stripe_card = stripe.Customer.retrieve(customer.stripe_id).sources.retrieve(customer.card_id)

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
                        'merchant_name'  : storefront.display_name,
                        'order_number'   : "{order_id}".format(order_id=purchase.id),
                        "currency"       : "USD",
                        'payment_method' : "{cc_brand} · {cc_suffix}".format(cc_brand=stripe_card['brand'], cc_suffix=stripe_card['last4']),
                        'order_url'      : "http://prebot.me/orders/{order_id}".format(order_id=purchase.id),
                        'timestamp'      : "{timestamp}".format(timestamp=purchase.added),
                        'elements'       : [{
                            'title'     : product.display_name,
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
    logger.info("build_list_card(recipient_id={recipient_id}, body_elements={body_elements}, header_element={header_element}, buttons={buttons}, quick_replies={quick_replies})".format(recipient_id=recipient_id, body_elements=body_elements, header_element=header_element, buttons=buttons, quick_replies=quick_replies))

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type'    : "template",
                'payload' : {
                    'template_type'     : "list",
                    'top_element_style' : "large",
                    'elements'          : build_list_elements(body_elements, header_element)
                }
            }
        }
    }

    if buttons is not None:
        data['message']['attachment']['payload']['buttons'] = buttons

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    return data


def build_content_card(recipient_id, title, subtitle, image_url, item_url, buttons=None, quick_replies=None):
    logger.info("build_content_card(recipient_id={recipient_id}, title={title}, subtitle={subtitle}, image_url={image_url}, item_url={item_url}, buttons={buttons}, quick_replies={quick_replies})".format(recipient_id=recipient_id, title=title, subtitle=subtitle, image_url=image_url, item_url=item_url, buttons=buttons, quick_replies=quick_replies))

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


def main_menu_quick_replies(fb_psid):
    logger.info("main_menu_quick_replies(fb_psid={fb_psid})".format(fb_psid=fb_psid))

    storefront_query = db.session.query(Storefront.id).filter(Storefront.owner_id == fb_psid).filter(Storefront.creation_state == 4).order_by(Storefront.added.desc()).subquery('storefront_query')
    product = Product.query.filter(Product.storefront_id.in_(storefront_query)).filter(Product.creation_state == 5).first()

    quick_replies = [
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Menu", payload=Const.PB_PAYLOAD_MAIN_MENU),
    ]

    if product is not None:
        quick_replies.append(build_quick_reply(Const.KWIK_BTN_TEXT, caption=product.messenger_url, payload=Const.PB_PAYLOAD_PREBOT_URL))

    return quick_replies

def cancel_entry_quick_reply():
    logger.info("cancel_entry_quick_reply()")

    return [
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Cancel", payload=Const.PB_PAYLOAD_CANCEL_ENTRY_SEQUENCE)
    ]

def cancel_payment_quick_reply():
    logger.info("cancel_payment_quick_reply()")

    return [
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Cancel Purchase", payload=Const.PB_PAYLOAD_PAYMENT_CANCEL)
    ]

def dm_quick_replies(recipient_id, purchase):
    logger.info("dm_quick_replies(recipient_id={recipient_id}, purchase={purchase})".format(recipient_id=recipient_id, purchase=purchase))

    if recipient_id == purchase.customer_id:
        payload = Const.PB_PAYLOAD_DM_STOREFRONT_OWNER

    else:
        payload = Const.PB_PAYLOAD_DM_CUSTOMER

    quick_replies = [
        build_quick_reply(Const.KWIK_BTN_TEXT, caption="Reply", payload=payload)
    ]

    if purchase.claim_state == 3 or purchase.claim_state == 4:
        quick_replies.append(build_quick_reply(Const.KWIK_BTN_TEXT, caption="Close DM", payload=Const.PB_PAYLOAD_DM_CLOSE))

    return quick_replies + cancel_entry_quick_reply()


def welcome_message(recipient_id, entry_type, deeplink=""):
    logger.info("welcome_message(recipient_id={recipient_id}, entry_type={entry_type}, deeplink={deeplink})".format(recipient_id=recipient_id, entry_type=entry_type, deeplink=deeplink))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

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

        product = Product.query.filter(Product.name == deeplink.split("/")[-1]).filter(Product.creation_state == 5).first()
        if product is not None:
            product.views += 1
            customer.product_id = product.id

            if product.video_url is not None and product.video_url != "":
                send_video(recipient_id, product.video_url)

            else:
                if product.image_url is not None:
                    send_image(recipient_id, product.image_url)

            try:
                conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('UPDATE `products` SET `views` = `views` + 1 WHERE `id` = {product_id} LIMIT 1;)'.format(product_id=product.id))
                    conn.commit()

            except mysql.Error, e:
                logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

            finally:
                if conn:
                    conn.close()

            storefront = Storefront.query.filter(Storefront.id == product.storefront_id).filter(Storefront.creation_state == 4).first()
            if storefront is not None:
                storefront.views += 1
                customer.storefront_id = storefront.id

                try:
                    conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('UPDATE `storefronts` SET `views` = `views` + 1 WHERE `id` = {storefront_id} LIMIT 1;)'.format(storefront_id=storefront.id))
                        conn.commit()

                except mysql.Error, e:
                    logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                finally:
                    if conn:
                        conn.close()

            db.session.commit()


        if product is not None and storefront is not None:
            if add_subscription(recipient_id, storefront.id, product.id, deeplink):
                send_text(recipient_id, "Welcome to {storefront_name}'s Shop Bot on Lemonade. You have been subscribed to {storefront_name} updates.".format(storefront_name=storefront.display_name))

            else:
                send_text(recipient_id, "Welcome to {storefront_name}'s Shop Bot on Lemonade. You are already subscribed to {storefront_name} updates.".format(storefront_name=storefront.display_name))

            send_product_card(recipient_id, product.id, product.storefront_id, Const.CARD_TYPE_PRODUCT_PURCHASE)

            # if customer.stripe_id is not None and customer.card_id is not None:
            #     if Purchase.query.filter(Purchase.customer_id == customer.id).filter(Purchase.product_id == product.id).count() > 0:
            #         send_product_card(recipient_id, product.id, product.storefront_id, Const.CARD_TYPE_PRODUCT_PURCHASED)
            #
            #     else:
            #         send_product_card(recipient_id, product.id, product.storefront_id, Const.CARD_TYPE_PRODUCT_CHECKOUT)
            #
            # else:
            #     send_product_card(recipient_id, product.id, product.storefront_id, Const.CARD_TYPE_PRODUCT_PURCHASE)

        else:
            send_text(recipient_id, Const.ORTHODOX_GREETING)
            send_admin_carousel(recipient_id)



def send_admin_carousel(recipient_id):
    logger.info("send_admin_carousel(recipient_id={recipient_id})".format(recipient_id=recipient_id))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront = None

    #-- look for created storefront
    storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id)
    cards = []

    if storefront_query.count() == 0:
        cards.append(
            build_card_element(
                title = "Create Shop",
                subtitle = "Tap Button Below",
                image_url = Const.IMAGE_URL_CREATE_STOREFRONT,
                item_url = None,
                buttons = [
                    build_button(Const.CARD_BTN_POSTBACK, caption="Create Shop", payload=Const.PB_PAYLOAD_CREATE_STOREFRONT)
                ]
            )
        )

    else:
        storefront = storefront_query.order_by(Storefront.added.desc()).first()

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
                    title = "Add Item",
                    subtitle = "Tap Button Below",
                    image_url = Const.IMAGE_URL_ADD_PRODUCT,
                    item_url = None,
                    buttons = [
                        build_button(Const.CARD_BTN_POSTBACK, caption="Add Item", payload=Const.PB_PAYLOAD_ADD_PRODUCT)
                    ]
                )
            )

        else:
            product = product_query.order_by(Product.added.desc()).first()

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
                        title = "Message Subscribers",
                        subtitle =  "Notify your 1 subscriber",
                        image_url = Const.IMAGE_URL_NOTIFY_SUBSCRIBERS,
                        item_url = None,
                        buttons = [
                            build_button(Const.CARD_BTN_POSTBACK, caption="Message Subscriber", payload=Const.PB_PAYLOAD_NOTIFY_SUBSCRIBERS)
                        ]
                    )
                )

            elif subscriber_query.count() > 1:
                cards.append(
                    build_card_element(
                        title = "Message Subscribers",
                        subtitle =  "Notify your {total} subscribers.".format(total=subscriber_query.count()),
                        image_url = Const.IMAGE_URL_NOTIFY_SUBSCRIBERS,
                        item_url = None,
                        buttons = [
                            build_button(Const.CARD_BTN_POSTBACK, caption="Message Subscribers", payload=Const.PB_PAYLOAD_NOTIFY_SUBSCRIBERS)
                        ]
                    )
                )

            purchases = []
            for storefront in Storefront.query.filter(Storefront.owner_id == recipient_id):
                for purchase in Purchase.query.filter(Purchase.storefront_id == storefront.id):
                    purchases.append(purchase)

            if len(purchases) > 0:
                if len(purchases) == 1:
                    subtitle = "1 Purchase"

                else:
                    subtitle = "{total} Purchases".format(total=len(purchases))

                cards.append(
                    build_card_element(
                        title = "Purchases",
                        subtitle = subtitle,
                        image_url = Const.IMAGE_URL_PURCHASES,
                        buttons = [
                            build_button(Const.CARD_BTN_URL_COMPACT, caption="View Purchases", url="http://prebot.me/purchases/stores/{user_id}".format(user_id=customer.id)),
                            build_button(Const.CARD_BTN_POSTBACK, caption="Message", payload=Const.PB_PAYLOAD_MESSAGE_CUSTOMERS),
                            # build_button(Const.CARD_BTN_POSTBACK, caption="Payout via Bitcoin", payload=Const.PB_PAYLOAD_PAYOUT_BITCOIN),
                            build_button(Const.CARD_BTN_POSTBACK, caption="Payout via PayPal", payload=Const.PB_PAYLOAD_PAYOUT_PAYPAL)
                        ]
                    )
                )

            cards.append(
                build_card_element(
                    title = product.display_name,
                    subtitle = "{description} — ${price:.2f}".format(description=product.description, price=product.price),
                    image_url = product.image_url,
                    item_url = product.video_url,
                    buttons = [
                        build_button(Const.CARD_BTN_POSTBACK, caption="Replace Item", payload=Const.PB_PAYLOAD_DELETE_PRODUCT)
                    ]
                )
            )

            if product.creation_state == 5:
                cards.append(
                    build_card_element(
                        title = "Share on Messenger",
                        subtitle = "",
                        image_url = Const.IMAGE_URL_SHARE_MESSENGER,
                        item_url = None,
                        buttons = [
                            build_button(Const.CARD_BTN_POSTBACK, caption="Share on Messenger", payload=Const.PB_PAYLOAD_SHARE_PRODUCT)
                        ]
                    )
                )

                cards.append(
                    build_card_element(
                        title = "Share Shop Bot",
                        subtitle = "",
                        image_url = Const.IMAGE_URL_SHARE_STOREFRONT,
                        item_url = None,
                        buttons = [
                            build_button(Const.CARD_BTN_URL_COMPACT, caption="Share Shop Bot", url="http://prebot.me/share/{product_id}".format(product_id=product.id))
                            #build_button(Const.CARD_BTN_POSTBACK, caption="Share on Messenger", payload=Const.PB_PAYLOAD_SHARE_PRODUCT)
                        ]
                    )
                )


# cards.append(
    #     build_card_element
    #         title = "View Shops",
    #         subtitle = "",
    #         image_url = Const.IMAGE_URL_MARKETPLACE,
    #         item_url = None,
    #         buttons = [
    #             build_button(Const.CARD_BTN_URL_COMPACT, caption="View Shops", url="http://prebot.me/shops")
    #         ]
    #     )
    # )

    if storefront_query.count() > 0:
        storefront = storefront_query.first()
        if storefront.giveaway == 0:
            cards.append(
                build_card_element(
                    title = "Add Giveaway",
                    subtitle = "",
                    image_url = Const.IMAGE_URL_GIVEAWAYS,
                    item_url = None,
                    buttons = [
                        build_button(Const.CARD_BTN_POSTBACK, caption="Add Giveaway", payload=Const.PB_PAYLOAD_ADD_GIVEAWAYS)
                    ]
                )
            )

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

    if storefront is None:
        quick_replies = main_menu_quick_replies(recipient_id)

    data = build_carousel(
        recipient_id = recipient_id,
        cards = cards,
        quick_replies = main_menu_quick_replies(recipient_id)
    )

    send_message(json.dumps(data))


def send_customer_carousel(recipient_id, storefront_id):
    logger.info("send_customer_carousel(recipient_id={recipient_id}, storefront_id={storefront_id})".format(recipient_id=recipient_id, storefront_id=storefront_id))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront = None

    elements = []

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
            product = query.order_by(Product.added.desc()).first()

            if Purchase.query.filter(Purchase.customer_id == customer.id).filter(Purchase.product_id == product.id).count() > 0:
                elements.append(
                    build_card_element(
                        title = "You have pre-ordered {product_name}".format(product_name=product.display_name),
                        subtitle = product.description,
                        image_url = product.image_url,
                        item_url = None,
                        buttons = [
                            build_button(Const.CARD_BTN_POSTBACK, caption="Message Owner", payload=Const.PB_PAYLOAD_NOTIFY_STOREFRONT_OWNER),
                            build_button(Const.CARD_BTN_POSTBACK, caption="Rate", payload=Const.PB_PAYLOAD_RATE_STOREFRONT)
                        ]
                    )
                )

            else:
                elements.append(
                    build_card_element(
                        title = product.display_name,
                        subtitle = "{description} — ${price:.2f}".format(description=product.description, price=product.price),
                        image_url = product.image_url,
                        item_url = None,
                        buttons = [
                            build_button(Const.CARD_BTN_POSTBACK, caption="Pre-Order", payload=Const.PB_PAYLOAD_RESERVE_PRODUCT)
                        ]
                    )
                )


            purchase_query = Purchase.query.filter(Purchase.customer_id == customer.id)
            if purchase_query.count() > 0:
                if purchase_query.count() == 1:
                    subtitle = "1 item"

                else:
                    subtitle = "{total} items".format(total=purchase_query.count())

                elements.append(
                    build_card_element(
                        title = "Purchases",
                        subtitle = subtitle,
                        image_url = Const.IMAGE_URL_PURCHASES,
                        buttons = [
                            build_button(Const.CARD_BTN_URL_COMPACT, caption="View Purchases", url="http://prebot.me/purchases/{user_id}".format(user_id=customer.id))
                        ]
                    )
                )


            title = product.display_name
            # if Purchase.query.filter(Purchase.customer_id == customer.id).filter(Purchase.product_id == product.id).count() > 0:
            #     title = "I Pre-ordered {product_name}".format(product_name=product.display_name)

            elements.append(
                build_card_element(
                    title = title,
                    subtitle = "View Shopbot",
                    image_url = product.image_url,
                    item_url = product.messenger_url,
                    buttons = [
                        build_button(Const.CARD_BTN_URL, caption="View Shopbot", url=product.messenger_url),
                        build_button(Const.CARD_BTN_INVITE)
                    ]
                )
            )

            data = build_carousel(
                recipient_id = recipient_id,
                cards = elements,
                quick_replies = main_menu_quick_replies(recipient_id)
            )

            send_message(json.dumps(data))


def send_storefront_card(recipient_id, storefront_id, card_type=Const.CARD_TYPE_STOREFRONT):
    logger.info("send_storefront_card(recipient_id={recipient_id}, storefront_id={storefront_id}, card_type={card_type})".format(recipient_id=recipient_id, storefront_id=storefront_id, card_type=card_type))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

    query = Storefront.query.filter(Storefront.id == storefront_id)
    product = Product.query.filter(Product.storefront_id == storefront_id).order_by(Product.added.desc()).first()
    storefront = None

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
                    build_button(Const.CARD_BTN_URL, caption="View Shopbot", url=storefront.messenger_url),
                    build_button(Const.CARD_BTN_INVITE)
                ]
            )

        elif card_type == Const.CARD_TYPE_STOREFRONT_PREVIEW:
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

        elif card_type == Const.CARD_TYPE_STOREFRONT_SHARE:
            title = storefront.display_name
            # if Purchase.query.filter(Purchase.customer_id == customer.id).filter(Purchase.product_id == product.id).count() > 0:
            #     title = "I Pre-ordered from {storefront_name}".format(storefront_name=storefront.display_name)

            data = build_content_card(
                recipient_id = recipient_id,
                title = title,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.messenger_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="View Shopbot", url=storefront.messenger_url),
                    build_button(Const.CARD_BTN_INVITE)
                ],
                quick_replies = main_menu_quick_replies(recipient_id)
            )

        else:
            title = storefront.display_name
            # if Purchase.query.filter(Purchase.customer_id == customer.id).filter(Purchase.product_id == product.id).count() > 0:
            #     title = "I Pre-ordered from {storefront_name}".format(storefront_name=storefront.display_name)

            data = build_content_card(
                recipient_id = recipient_id,
                title = title,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.messenger_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="View Shopbot", url=storefront.messenger_url),
                    build_button(Const.CARD_BTN_INVITE)
                ]
            )

        send_message(json.dumps(data))


def send_product_card(recipient_id, product_id, storefront_id=None, card_type=Const.CARD_TYPE_PRODUCT):
    logger.info("send_product_card(recipient_id={recipient_id}, product_id={product_id}, card_type={card_type})".format(recipient_id=recipient_id, product_id=product_id, card_type=card_type))
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront = None

    data = None
    query = Product.query.filter(Product.id == product_id)
    if query.count() > 0:
        product = query.order_by(Product.added.desc()).first()
        storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()

        if product.image_url is None:
            product.image_url = Const.IMAGE_URL_ADD_PRODUCT

        if card_type == Const.CARD_TYPE_PRODUCT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
                subtitle = "{description} — ${price:.2f}".format(description=product.description, price=product.price),
                image_url = product.image_url,
                item_url = None,
                buttons = [
                    build_button(Const.CARD_BTN_URL_COMPACT, caption="Tap to Reserve", url="http://prebot.me/reserve/{product_id}/{recipient_id}".format(product_id=product_id, recipient_id=recipient_id))
                ]
            )

        elif card_type == Const.CARD_TYPE_PRODUCT_PREVIEW:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
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
            title = product.display_name
            if Purchase.query.filter(Purchase.customer_id == customer.id).filter(Purchase.product_id == product.id).count() > 0:
                title = "I pre-ordered {product_name}".format(product_name=product.display_name)

            data = build_content_card(
                recipient_id = recipient_id,
                title = title,
                subtitle = "View Shopbot",
                image_url = product.image_url,
                item_url = product.messenger_url,
                buttons = [
                    build_button(Const.CARD_BTN_URL, caption="View Shopbot", url=product.messenger_url),
                    build_button(Const.CARD_BTN_INVITE)
                ],
                quick_replies = main_menu_quick_replies(recipient_id)
            )

        elif card_type == Const.CARD_TYPE_PRODUCT_PURCHASE:
            query = Storefront.query.filter(Storefront.id == storefront_id)
            if query.count() > 0:
                storefront = query.first()

                data = build_list_card(
                    recipient_id = recipient_id,
                    body_elements = [
                        build_card_element(
                            title = product.display_name,
                            subtitle = "${price:.2f}".format(price=product.price),
                            image_url = product.image_url,
                            item_url = product.messenger_url,
                            buttons = [
                                build_button(Const.CARD_BTN_POSTBACK, caption="Pay via PayPal", payload=Const.PB_PAYLOAD_CHECKOUT_PAYPAL)

                            ]
                        ),
                        build_card_element(
                            title = product.display_name,
                            subtitle = "${price:.2f}".format(price=product.price),
                            image_url = product.image_url,
                            item_url = product.messenger_url,
                            buttons = [
                                build_button(Const.CARD_BTN_POSTBACK, caption="Pay via Bitcoin", payload=Const.PB_PAYLOAD_CHECKOUT_BITCOIN)
                            ]
                        ),
                        build_card_element(
                            title = product.display_name,
                            subtitle = "${price:.2f}".format(price=product.price),
                            image_url = product.image_url,
                            item_url = product.messenger_url,
                            buttons = [
                                build_button(Const.CARD_BTN_POSTBACK, caption="Pay via Stripe", payload=Const.PB_PAYLOAD_CHECKOUT_CC_CARD)
                            ]
                        )
                    ],
                    header_element = build_card_element(
                        title = storefront.display_name,
                        subtitle = storefront.description,
                        image_url = storefront.logo_url,
                        item_url = None
                    ),
                    quick_replies = main_menu_quick_replies(recipient_id)
                )

        elif card_type == Const.CARD_TYPE_PRODUCT_CHECKOUT:
            storefront_query = Storefront.query.filter(Storefront.id == storefront_id)
            if storefront_query.count() > 0:
                storefront = storefront_query.first()

                customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
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
                        title = product.display_name,
                        subtitle = "{product_description} - from {storefront_name}".format(product_description=product.description, storefront_name=storefront.display_name),
                        image_url = product.image_url,
                        item_url = None
                    ),
                    buttons = [
                        build_button(Const.CARD_BTN_POSTBACK, caption="Pay", payload=Const.PB_PAYLOAD_PURCHASE_PRODUCT)
                    ]
                )

        elif card_type == Const.CARD_TYPE_PRODUCT_RECEIPT:
            customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
            data = build_receipt_card(recipient_id, customer.purchase_id)

        elif card_type == Const.CARD_TYPE_PRODUCT_PURCHASED:
            customer_query = db.session.query(Customer.purchase_id).filter(Customer.fb_psid == recipient_id).order_by(Purchase.added.desc()).subquery('customer_query')
            purchase = Purchase.query.filter(Purchase.id.in_(customer_query)).first()

            data = build_content_card(
                recipient_id = recipient_id,
                title = "You purchased {product_name} on {purchase_date}".format(product_name=product.display_name, purchase_date=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%b %d @ %I:%M%P %Z').lstrip("0")),
                subtitle = product.description,
                image_url = product.image_url,
                item_url = None,
                buttons = [
                    build_button(Const.CARD_BTN_POSTBACK, caption="Message Owner", payload=Const.PB_PAYLOAD_NOTIFY_STOREFRONT_OWNER),
                    build_button(Const.CARD_BTN_POSTBACK, caption="Rate", payload=Const.PB_PAYLOAD_RATE_PRODUCT)
                ],
                quick_replies = main_menu_quick_replies(recipient_id)
            )


        elif card_type == Const.CARD_TYPE_PRODUCT_RATE:
            rate_buttons = [
                build_button(Const.KWIK_BTN_TEXT, caption=(Const.RATE_GLYPH * 1), payload=Const.PB_PAYLOAD_PRODUCT_RATE_1_STAR),
                build_button(Const.KWIK_BTN_TEXT, caption=(Const.RATE_GLYPH * 2), payload=Const.PB_PAYLOAD_PRODUCT_RATE_2_STAR),
                build_button(Const.KWIK_BTN_TEXT, caption=(Const.RATE_GLYPH * 3), payload=Const.PB_PAYLOAD_PRODUCT_RATE_3_STAR),
                build_button(Const.KWIK_BTN_TEXT, caption=(Const.RATE_GLYPH * 4), payload=Const.PB_PAYLOAD_PRODUCT_RATE_4_STAR),
                build_button(Const.KWIK_BTN_TEXT, caption=(Const.RATE_GLYPH * 5), payload=Const.PB_PAYLOAD_PRODUCT_RATE_5_STAR)
            ]

            data = build_content_card(
                recipient_id = recipient_id,
                title = "Rate {product_name}".format(product_name=product.display_name),
                subtitle = "Average Rating: {stars}".format(stars=(Const.RATE_GLYPH * int(round(round(product.avg_rating, 2))))),
                image_url = product.image_url,
                item_url = None,
                quick_replies = rate_buttons + cancel_entry_quick_reply()
            )


        else:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
                subtitle = "{description} — ${price:.2f}".format(description=product.description, price=product.price),
                image_url = product.image_url,
                item_url = None,
                buttons = [
                    build_button(Const.CARD_BTN_URL_COMPACT, caption="Tap to Reserve", url="http://prebot.me/reserve/{product_id}/{recipient_id}".format(product_id=product_id, recipient_id=recipient_id))
                ]
            )

        send_message(json.dumps(data))


def send_purchases_list_card(recipient_id, card_type=Const.CARD_TYPE_PRODUCT_PURCHASES):
    logger.info("send_purchases_list_card(recipient_id={recipient_id}, card_type={card_type})".format(recipient_id=recipient_id, card_type=card_type))

    product = None
    storefront = None

    elements = []

    if card_type == Const.CARD_TYPE_PRODUCT_PURCHASES:
        for storefront in Storefront.query.filter(Storefront.owner_id == recipient_id):
            for purchase in Purchase.query.filter(Purchase.storefront_id == storefront.id):
                product = Product.query.filter(Product.id == purchase.product_id).first()
                customer = Customer.query.filter(Customer.id == purchase.customer_id).first()

                elements.append(
                    build_card_element(
                        title = "{product_name} - ${price:.2f}".format(product_name=product.display_name, price=product.price),
                        subtitle = customer.email,
                        image_url = product.image_url,
                        item_url = None,
                        buttons = [
                            build_button(Const.CARD_BTN_POSTBACK, caption="Message", payload="{payload}-{purchase_id}".format(payload=Const.PB_PAYLOAD_PURCHASE_MESSAGE, purchase_id=purchase.id))
                        ]
                    )
                )

    elif card_type == Const.CARD_TYPE_CUSTOMER_PURCHASES:
        pass

    else:
        pass

    send_message(json.dumps(
        build_list_card(
            recipient_id = recipient_id,
            body_elements = elements,
            quick_replies = main_menu_quick_replies(recipient_id)
        )
    ))



#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


def received_quick_reply(recipient_id, quick_reply):
    logger.info("received_quick_reply(recipient_id={recipient_id}, quick_reply={quick_reply})".format(recipient_id=recipient_id, quick_reply=quick_reply))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

    if quick_reply == Const.PB_PAYLOAD_CANCEL_ENTRY_SEQUENCE:
        send_tracker("button-cancel-entry-sequence", recipient_id, "")

        clear_entry_sequences(recipient_id)

        if Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4).first() is not None or customer is None:
            send_admin_carousel(recipient_id)

        else:
            send_customer_carousel(recipient_id, customer.storefront_id)


    elif quick_reply == Const.PB_PAYLOAD_SUBMIT_STOREFRONT:
        send_tracker("button-submit-store", recipient_id, "")

        users_query = Customer.query.filter(Customer.fb_psid == recipient_id)
        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 3)
        if storefront_query.count() > 0:
            storefront = storefront_query.first()
            storefront.creation_state = 4
            storefront.added = int(time.time())
            db.session.commit()

            try:
                conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('INSERT INTO `storefronts` (`id`, `owner_id`, `name`, `display_name`, `description`, `logo_url`, `prebot_url`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP())' % (users_query.first().id, storefront.name, storefront.display_name, storefront.description, storefront.logo_url, storefront.prebot_url))
                    conn.commit()
                    storefront.id = cur.lastrowid
                    db.session.commit()

            except mysql.Error, e:
                logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

            finally:
                if conn:
                    conn.close()


            send_text(recipient_id, "Great! You have created {storefront_name}. Now add an item to sell.".format(storefront_name=storefront.display_name))
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

        storefront = Storefront(recipient_id)
        db.session.add(storefront)
        db.session.commit()
        next_storefront_id(storefront)

        send_text(recipient_id, "Give your Lemonade Shop Bot a name.")

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
        match = re.match(r'PRODUCT_RELEASE_(?P<days>\d+)_DAYS', quick_reply)
        send_tracker("button-product-release-{days}-days-store".format(days=match.group('days')), recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)
        product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 3)
        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).first()
            product.release_date = calendar.timegm((datetime.utcnow() + relativedelta(months=int(int(match.group('days')) / 30))).replace(hour=0, minute=0, second=0, microsecond=0).utctimetuple())
            product.description = "Pre-release ends {release_date}".format(release_date=datetime.utcfromtimestamp(product.release_date).strftime('%a, %b %-d'))
            product.creation_state = 4
            db.session.commit()

            if int(match.group('days')) < 30:
                send_text(recipient_id, "This item will be available today")
            else:
                send_text(recipient_id, "This item will be available {release_date}".format(release_date=datetime.utcfromtimestamp(product.release_date).strftime('%A, %b %-d')))

            send_text(recipient_id, "Here's what your product will look like:")
            send_product_card(recipient_id=recipient_id, product_id=product.id, card_type=Const.CARD_TYPE_PRODUCT_PREVIEW)

    elif quick_reply == Const.PB_PAYLOAD_SUBMIT_PRODUCT:
        send_tracker("button-submit-product", recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)
        product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 4)
        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).first()
            product.creation_state = 5
            product.added = int(time.time())
            db.session.commit()

            try:
                conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('INSERT INTO `products` (`id`, `storefront_id`, `name`, `display_name`, `description`, `image_url`, `video_url`, `attachment_id`, `price`, `prebot_url`, `release_date`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s), UTC_TIMESTAMP())'.format(product.storefront_id, product.name, product.display_name, product.description, product.image_url, product.video_url, product.attachment_id, product.price, product.prebot_url, product.release_date))
                    conn.commit()
                    product.id = cur.lastrowid
                    db.session.commit()

            except mysql.Error, e:
                logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

            finally:
                if conn:
                    conn.close()


            storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()
            send_admin_carousel(recipient_id)
            send_text(
                recipient_id = recipient_id,
                message_text = "You have successfully added Jdjdkd to Misty.\n\nShare Jdjdkd's card with your customers now.\n\n{product_url}\n\nTap Menu then Share on Messenger.".format(product_name=product.display_name, storefront_name=storefront.display_name, product_url=product.messenger_url),
                quick_replies= main_menu_quick_replies(recipient_id)
            )

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
            product = product_query.order_by(Product.added.desc()).first()
            Product.query.filter(Product.storefront_id == storefront_query.first().id).delete()

        product = Product(storefront_query.first().id)
        db.session.add(product)
        db.session.commit()
        next_product_id(product)

        send_text(recipient_id, "Upload a photo or video of what you are selling.")

    elif quick_reply == Const.PB_PAYLOAD_CANCEL_PRODUCT:
        send_tracker("button-undo-product", recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)
        product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id)
        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).first()
            send_text(recipient_id, "Canceling your {product_name} product creation...".format(product_name=product.display_name))

            Product.query.filter(Product.storefront_id == storefront_query.first().id).delete()
            db.session.commit()

        send_admin_carousel(recipient_id)

    elif quick_reply == Const.PB_PAYLOAD_AFFILIATE_GIVEAWAY:
        send_tracker("button-givaway", recipient_id, "")
        send_text(recipient_id, "Win CS:GO items by playing flip coin with Lemonade! Details coming soon.", quick_replies=[build_quick_reply(Const.KWIK_BTN_TEXT, caption="Menu", payload=Const.PB_PAYLOAD_MAIN_MENU)])

    elif quick_reply == Const.PB_PAYLOAD_MAIN_MENU:
        send_tracker("button-menu", recipient_id, "")

        storefront = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4).first()
        if storefront is not None and customer.storefront_id is None:
            send_admin_carousel(recipient_id)

        else:
            send_customer_carousel(recipient_id, customer.storefront_id)

    elif quick_reply == Const.PB_PAYLOAD_PREBOT_URL:
        send_tracker("button-url", recipient_id, "")

        storefront_query = db.session.query(Storefront.id).filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4).order_by(Storefront.added.desc()).subquery('storefront_query')
        product = Product.query.filter(Product.storefront_id.in_(storefront_query)).filter(Product.creation_state == 5).first()

        storefront = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4).first()
        if storefront is not None and product is not None:
            send_text(recipient_id, "http://{messenger_url}".format(messenger_url=product.messenger_url), main_menu_quick_replies(recipient_id))
            send_text(recipient_id, "Tap, hold, then share {storefront_name}'s shop link above.".format(storefront_name=storefront.display_name), main_menu_quick_replies(recipient_id))

        else:
            send_text(recipient_id, "Couldn't locate your shop!", main_menu_quick_replies(recipient_id))


    elif quick_reply == Const.PB_PAYLOAD_GIVEAWAYS_YES:
        send_tracker("button-giveaways-yes", recipient_id, "")

        storefront = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4).first()
        storefront.giveaway = 1
        db.session.commit()

        try:
            conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('UPDATE `storefronts` SET `giveaway` = 1 WHERE `id` = {storefront_id};'.format(storefront_id=storefront.id))
                conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

        finally:
            if conn:
                conn.close()

        product_query = Product.query.filter(Product.storefront_id == storefront.id)
        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).first()
            subscriber_query = Subscription.query.filter(Subscription.product_id == product.id).filter(Subscription.enabled == 1)
            if subscriber_query.count() < 20:
                send_text(recipient_id, "Great! Once you have 20 customers subscribed to {storefront_name} item giveaways will unlock.".format(storefront_name=storefront.display_name), [build_quick_reply(Const.KWIK_BTN_TEXT, caption="Menu", payload=Const.PB_PAYLOAD_MAIN_MENU)])

            else:
                send_text(recipient_id, "Great! Item giveaways will now be unlocked for {storefront_name}.".format(storefront_name=storefront.display_name), [build_quick_reply(Const.KWIK_BTN_TEXT, caption="Menu", payload=Const.PB_PAYLOAD_MAIN_MENU)])

        else:
            send_text(recipient_id, "Great! Once you have 20 customers subscribed to {storefront_name} item giveaways will unlock.".format(storefront_name=storefront.display_name), [build_quick_reply(Const.KWIK_BTN_TEXT, caption="Menu", payload=Const.PB_PAYLOAD_MAIN_MENU)])


    elif quick_reply == Const.PB_PAYLOAD_GIVEAWAYS_NO:
        send_tracker("button-giveaways-no", recipient_id, "")
        send_admin_carousel(recipient_id)

    elif quick_reply == Const.PB_PAYLOAD_PAYMENT_YES:
        send_tracker("button-payment-yes", recipient_id, "")
        payment = Payment.query.filter(Payment.fb_psid == recipient_id).filter(Payment.source == "card").first()

        if payment is not None and payment.creation_state == 5:
            payment.creation_state = 6
            db.session.commit()

            if add_cc_payment(recipient_id):
                send_product_card(recipient_id=recipient_id, product_id=customer.product_id, storefront_id=customer.storefront_id, card_type=Const.CARD_TYPE_PRODUCT_CHECKOUT)

            else:
                send_product_card(recipient_id=recipient_id, product_id=customer.product_id, storefront_id=customer.storefront_id, card_type=Const.CARD_TYPE_PRODUCT_PURCHASE)

    elif quick_reply == Const.PB_PAYLOAD_PAYMENT_NO:
        send_tracker("button-payment-no", recipient_id, "")
        Payment.query.filter(Payment.fb_psid == recipient_id).delete()
        db.session.commit()
        add_cc_payment(recipient_id)

    elif quick_reply == Const.PB_PAYLOAD_PAYMENT_CANCEL:
        send_tracker("button-payment-cancel", recipient_id, "")
        Payment.query.filter(Payment.fb_psid == recipient_id).delete()
        db.session.commit()

        send_product_card(recipient_id, customer.product_id, customer.storefront_id, Const.CARD_TYPE_PRODUCT_PURCHASE)
        # send_customer_carousel(recipient_id, customer.storefront_id)


def received_payload_button(recipient_id, payload, referral=None):
    logger.info("received_payload_button(recipient_id={recipient_id}, payload={payload}, referral={referral})".format(recipient_id=recipient_id, payload=payload, referral=referral))

    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
    storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)

    if payload == Const.PB_PAYLOAD_GREETING:
        logger.info("----------=BOT GREETING @({timestamp})=----------".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))

        if referral is None:
            send_image(recipient_id, Const.IMAGE_URL_GREETING)
            welcome_message(recipient_id, Const.MARKETPLACE_GREETING)
            return "OK", 200

    elif payload == Const.PB_PAYLOAD_CREATE_STOREFRONT:
        send_tracker("button-create-shop", recipient_id, "")

        query = Storefront.query.filter(Storefront.owner_id == recipient_id)
        if query.count() > 0:
            try:
                query.delete()
                db.session.commit()
            except:
                db.session.rollback()

        storefront = Storefront(recipient_id)
        db.session.add(storefront)
        db.session.commit()
        next_storefront_id(storefront)

        send_text(recipient_id, "Give your Shopbot a name.")

    elif payload == Const.PB_PAYLOAD_DELETE_STOREFRONT:
        send_tracker("button-delete-shop", recipient_id, "")

        for storefront in Storefront.query.filter(Storefront.owner_id == recipient_id):
            send_text(recipient_id, "{storefront_name} has been removed.".format(storefront_name=storefront.display_name))
            Product.query.filter(Product.storefront_id == storefront.id).delete()

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

        Storefront.query.filter(Storefront.owner_id == recipient_id).delete()
        db.session.commit()

        send_admin_carousel(recipient_id)


    elif payload == Const.PB_PAYLOAD_ADD_PRODUCT:
        send_tracker("button-add-item", recipient_id, "")

        try:
            conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('SELECT `id` FROM `storefronts` WHERE `name` = "{storefront_name}" LIMIT 1;'.format(storefront_name=storefront_query.first().name))
                row = cur.fetchone()
                logger.info("ADD PRODUCT TO STORE: %s" % (row))
                if row is not None:
                    product = Product(row['id'])
                    db.session.add(product)

                else:
                    product = Product(storefront_query.first().id)
                    db.session.add(product)
                db.session.commit()
                next_product_id(product)

        except mysql.Error, e:
            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(recipient_id, "Upload a photo or video of what you are selling.")


    elif payload == Const.PB_PAYLOAD_DELETE_PRODUCT:
        send_tracker("button-delete-item", recipient_id, "")

        storefront = storefront_query.first()
        for product in Product.query.filter(Product.storefront_id == storefront.id):
            send_text(recipient_id, "Removing your existing product \"{product_name}\"...".format(product_name=product.display_name))
            Subscription.query.filter(Subscription.product_id == product.id)
            Product.query.filter(product.storefront_id == storefront.id).delete()
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

        product = Product(storefront.id)
        db.session.add(product)
        db.session.commit()
        next_product_id(product)
        send_text(recipient_id, "Upload a photo or video of what you are selling.")

    elif payload == Const.PB_PAYLOAD_SHARE_STOREFRONT:
        send_tracker("button-share", recipient_id, "")
        send_text(recipient_id, "Share your Shopbot with your friends on messenger")
        send_storefront_card(recipient_id, storefront_query.first().id, Const.CARD_TYPE_STOREFRONT_SHARE)


    elif payload == Const.PB_PAYLOAD_SHARE_PRODUCT:
        send_tracker("button-share", recipient_id, "")
        send_text(recipient_id, "Share your Shopbot with your friends on messenger")

        storefront_query = db.session.query(Storefront.id).filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4).order_by(Storefront.added.desc()).subquery('storefront_query')
        product = Product.query.filter(Product.storefront_id.in_(storefront_query)).filter(Product.creation_state == 5).first()

        if product is not None:
            send_product_card(recipient_id=recipient_id, product_id=product.id, card_type=Const.CARD_TYPE_PRODUCT_SHARE)


    elif payload == Const.PB_PAYLOAD_SUPPORT:
        send_tracker("button-support", recipient_id, "")
        send_text(recipient_id, "Support for Lemonade:\nprebot.me/support")


    elif payload == Const.PB_PAYLOAD_RESERVE_PRODUCT:
        send_tracker("button-reserve", recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.id == customer.storefront_id)
        product_query = Product.query.filter(Product.id == customer.product_id)
        if storefront_query.count() > 0 and product_query.count() > 0:
            storefront = storefront_query.first()
            product = product_query.first()
            send_product_card(recipient_id=recipient_id, product_id=product.id, storefront_id=storefront.id, card_type=Const.CARD_TYPE_PRODUCT_PURCHASE)

    elif payload == Const.PB_PAYLOAD_CHECKOUT_BITCOIN:
        send_tracker("button-payment-bitcoin", recipient_id, "")

        db.session.add(Payment(fb_psid=recipient_id, source="btc"))
        db.session.commit()

        send_text(recipient_id, "Enter your Bitcoin address")

    elif payload == Const.PB_PAYLOAD_CHECKOUT_CC_CARD:
        send_tracker("button-checkout", recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.id == customer.storefront_id)
        product_query = Product.query.filter(Product.id == customer.product_id)

        if product_query.count() > 0:
            storefront = storefront_query.first()
            product = product_query.order_by(Product.added.desc()).first()

            if customer.stripe_id is None or customer.card_id is None:
                try:
                    conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('SELECT `stripe_id`, `card_id` FROM `users` WHERE `id` = {user_id} AND `stripe_id` != "" AND `card_id` != "" LIMIT 1;'.format(user_id=customer.id))
                        row = cur.fetchone()

                        if row is not None:
                            customer.stripe_id = row['stripe_id']
                            customer.card_id = row['card_id']
                            db.session.commit()

                except mysql.Error, e:
                    logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                finally:
                    if conn:
                        conn.close()


            if customer.stripe_id is not None and customer.card_id is not None:
                send_product_card(recipient_id=recipient_id, product_id=product.id, storefront_id=storefront.id, card_type=Const.CARD_TYPE_PRODUCT_CHECKOUT)

            else:
                add_cc_payment(recipient_id)


    elif payload == Const.PB_PAYLOAD_CHECKOUT_PAYPAL:
        send_tracker("button-payment-bitcoin", recipient_id, "")
        db.session.add(Payment(recipient_id, "paypal"))
        db.session.commit()

        send_text(recipient_id, "Enter your PayPal email address")


    elif payload == Const.PB_PAYLOAD_PURCHASE_PRODUCT:
        send_tracker("button-purchase", recipient_id, "")

        storefront_query = Storefront.query.filter(Storefront.id == customer.storefront_id)
        product_query = Product.query.filter(Product.id == customer.product_id)

        if product_query.count() > 0:
            storefront = storefront_query.first()
            product = product_query.order_by(Product.added.desc()).first()

            send_text(recipient_id, "Completing your purchase…")
            if purchase_product(recipient_id):
                send_product_card(recipient_id, product.id, storefront.id, Const.CARD_TYPE_PRODUCT_RECEIPT)
            else:
                pass

            send_customer_carousel(recipient_id, storefront.id)


    elif payload == Const.PB_PAYLOAD_ADD_GIVEAWAYS:
        send_tracker("button-add-giveaways", recipient_id, "")
        if storefront_query.count() > 0:
            storefront = storefront_query.first()

            if storefront.giveaway == 0:
                send_text(recipient_id, "Do you want to offer your customers the ability to win Steam in-game items?", [
                    build_quick_reply(Const.KWIK_BTN_TEXT, caption="Yes", payload=Const.PB_PAYLOAD_GIVEAWAYS_YES),
                    build_quick_reply(Const.KWIK_BTN_TEXT, caption="No", payload=Const.PB_PAYLOAD_GIVEAWAYS_NO),
                ])


    elif payload == Const.PB_PAYLOAD_RATE_STOREFRONT:
        send_tracker("button-rate-storefront", recipient_id, "")


    elif payload == Const.PB_PAYLOAD_PRODUCT_VIDEO:
        send_tracker("button-view-video", recipient_id, "")

        product_query = Product.query.filter(Product.id == customer.product_id)
        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).first()
            send_video(recipient_id, product.video_url)


    elif payload == Const.PB_PAYLOAD_NOTIFY_SUBSCRIBERS:
        if storefront_query.count() > 0:
            storefront = storefront_query.first()
            send_tracker("shop-send-message", recipient_id, storefront.display_name)

            product_query = Product.query.filter(Product.storefront_id == storefront.id)
            if product_query.count() > 0:
                product = product_query.order_by(Product.added.desc()).first()
                product.broadcast_message = "_{PENDING}_"
                db.session.commit()

                send_text(recipient_id, "Send a message or video to your Lemonade subscribers.")

    elif payload == Const.PB_PAYLOAD_MESSAGE_CUSTOMERS:
        send_tracker("button-message-customers", recipient_id, "")
        send_purchases_list_card(recipient_id, Const.CARD_TYPE_PRODUCT_PURCHASES)

    elif re.search('PURCHASE_MESSAGE\-(\d+)', payload) is not None:
        send_tracker("button-message-customer", recipient_id, "")
        match = re.match(r'PURCHASE_MESSAGE\-(?P<purchase_id>\d+)', payload)
        purchase = Purchase.query.filter(Purchase.id == match.group('purchase_id')).first()

        if purchase is not None:
            customer = Customer.query.filter(Customer.id == purchase.customer_id).first()
            purchase.claim_state = 1
            db.session.commit()

            send_text(recipient_id, "Enter your message to {customer_email}".format(customer_email=customer.email))

    elif payload == Const.PB_PAYLOAD_PAYOUT_PAYPAL:
        send_tracker("button-paypal-payout", recipient_id, "")

        storefront = storefront_query.first()
        storefront.video_url = "_{PAYPAL}_"
        db.session.commit()

        send_text(recipient_id, "Enter your PayPal email address")

    elif payload == Const.PB_PAYLOAD_PAYOUT_BITCOIN:
        send_tracker("button-bitcoin-payout", recipient_id, "")

        storefront = storefront_query.first()
        storefront.video_url = "_{BITCOIN}_"
        db.session.commit()

        send_text(recipient_id, "Enter your Bitcoin address")

    elif payload == Const.PB_PAYLOAD_NOTIFY_STOREFRONT_OWNER:
        send_tracker("button-message-owner", recipient_id, "")

        storefront = Storefront.query.filter(Storefront.id == customer.storefront_id).first()
        send_text(recipient_id, "Notifying {storefront_name}…".format(storefront_name=storefront.display_name))
        send_customer_carousel(recipient_id, customer.storefront_id)

    elif payload == Const.PB_PAYLOAD_FLIP_COIN_NEXT_ITEM:
        send_tracker("button-flip-next-item", recipient_id, "")

        payload = {
            'action'    : "NEXT_ITEM",
            'social_id' : recipient_id
        }
        response = requests.post("{api_url}?token={timestamp}".format(api_url=Const.COIN_FLIP_API, timestamp=int(time.time())), data=payload)

    elif payload == Const.PB_PAYLOAD_FLIP_COIN_DO_FLIP:
        send_tracker("button-flip-next-item", recipient_id, "")

        payload = {
            'action'    : "FLIP_ITEM",
            'social_id' : recipient_id
        }
        response = requests.post("{api_url}?token={timestamp}".format(api_url=Const.COIN_FLIP_API, timestamp=int(time.time())), data=payload)

        payload = {
            'action'    : "FLIP_RESULT",
            'social_id' : recipient_id
        }
        response = requests.post("{api_url}?token={timestamp}".format(api_url=Const.COIN_FLIP_API, timestamp=int(time.time())), data=payload)

    else:
        send_tracker("unknown-button", recipient_id, "")
        send_text(recipient_id, "Button not recognized!")


def recieved_attachment(recipient_id, attachment_type, payload):
    logger.info("recieved_attachment(recipient_id={recipient_id}, attachment_type={attachment_type}, payload={payload})".format(recipient_id=recipient_id, attachment_type=attachment_type, payload=payload))

    #return "OK", 200


    #------- URL BUTTON
    if attachment_type == "fallback" and 'quick_reply' in payload:
        received_quick_reply(recipient_id, payload['quick_reply'])
        return "OK", 200


    #------- IMAGE MESSAGE
    if attachment_type == "image":
        logger.info("IMAGE: %s" % (payload))
        query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 2)
        if query.count() > 0:
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

            storefront = query.first()
            storefront.creation_state = 3
            storefront.logo_url = "http://prebot.me/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
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


        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)
        if storefront_query.count() > 0:
            query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 0)
            if query.count() > 0:
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

                product = query.order_by(Product.added.desc()).first()
                product.creation_state = 1
                product.image_url = "http://prebot.me/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
                product.video_url = ""
                db.session.commit()

                image_sizer_sq = ImageSizer(in_file=image_file, out_file=None)
                image_sizer_sq.start()

                image_sizer_ls = ImageSizer(in_file=image_file, out_file=None, canvas_size=(400, 300))
                image_sizer_ls.start()

                image_sizer_pt = ImageSizer(in_file=image_file, out_file=None, canvas_size=(480, 640))
                image_sizer_pt.start()

                image_sizer_ws = ImageSizer(in_file=image_file, canvas_size=(1280, 720))
                image_sizer_ws.start()

                send_text(recipient_id, "Give your product a title.")

                return "OK", 200

            else:
                handle_wrong_reply(recipient_id)

        else:
            handle_wrong_reply(recipient_id)


    #------- VIDEO MESSAGE
    elif attachment_type == "video":
        logger.info("VIDEO: %s" % (payload['url']))

        if Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state < 4).count() > 0:
            handle_wrong_reply(recipient_id)

        storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)
        if storefront_query.count() > 0:
            query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 0)
            if query.count() > 0:
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

                image_sizer_sq = ImageSizer(image_file)
                image_sizer_sq.start()

                image_sizer_banner = ImageSizer(in_file=image_file, canvas_size=(800, 240))
                image_sizer_banner.start()

                product = query.order_by(Product.added.desc()).first()
                product.creation_state = 1
                product.image_url = "http://prebot.me/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
                product.video_url = "http://prebot.me/videos/{timestamp}.mp4".format(timestamp=timestamp)
                db.session.commit()

                send_text(recipient_id, "Give your product a title.")

            else:
                handle_wrong_reply(recipient_id)
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
                copy_thread.join()

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

                send_text(recipient_id, "Great! Your message will be sent to your customers shortly.")
                send_admin_carousel(recipient_id)

    else:
        send_admin_carousel(recipient_id)

    return "OK", 200


def received_text_response(recipient_id, message_text):
    logger.info("received_text_response(recipient_id={recipient_id}, message_text={message_text})".format(recipient_id=recipient_id, message_text=message_text))
    storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4)
    customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()

    #-- purge sqlite db
    if message_text == "/:flush_sqlite:/":
        drop_sqlite()
        send_text(recipient_id, "Purged sqlite db")
        send_admin_carousel(recipient_id)

    elif message_text == "/:drop_payment:/":
        customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
        customer.email = None
        customer.stripe_id = None
        customer.card_id = None
        Payment.query.filter(Payment.fb_psid == recipient_id).delete()
        db.session.commit()

        try:
            conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('UPDATE `users` SET `email` = "", `stripe_id` = "", `card_id` = "" WHERE `id` = {user_id} LIMIT 1;'.format(user_id=customer.id))
                conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(recipient_id, "Removed payment details")

    elif message_text.startswith("/:db_addcol"):
        comp = message_text.split(" ")

        if len(comp) == 4:
            add_column(comp[1], comp[2], comp[3])


    #-- force referral
    elif message_text.startswith("/"):
        welcome_message(recipient_id, Const.CUSTOMER_REFERRAL, message_text[1:])


    #-- show admin carousel
    elif message_text.lower() in Const.RESERVED_ADMIN_REPLIES:
        if storefront_query.count() > 0:
            product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 5)
            if product_query.count() > 0:
                Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 5).delete()

        Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state < 4).delete()
        db.session.commit()

        send_admin_carousel(recipient_id)


    #-- show storefront carousel
    elif message_text.lower() in Const.RESERVED_CUSTOMER_REPLIES:
        product = Product.query.filter(Product.id == customer.product_id).first()
        storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()

        Payment.query.filter(Payment.fb_psid == recipient_id).delete()
        db.session.commit()

        send_customer_carousel(recipient_id, storefront.id)


    #-- show admin carousel if not deeplinked
    elif message_text.lower() in Const.RESERVED_SUPPORT_REPLIES:
        if customer.storefront_id is not None and customer.product_id is not None:
            send_product_card(recipient_id, customer.product_id, customer.storefront_id, Const.CARD_TYPE_PRODUCT_PURCHASE)

        else:
            send_admin_carousel(recipient_id)


    #-- quit message
    elif message_text.lower() in Const.RESERVED_STOP_REPLIES:
        Payment.query.filter(Payment.fb_psid == recipient_id).delete()

        if storefront_query.count() > 0:
            product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 5)
            if product_query.count() > 0:
                Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 5).delete()

        Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state < 4).delete()
        db.session.commit()

        send_text(recipient_id, Const.GOODBYE_MESSAGE)

    else:
        #-- entering paypal payout info
        if Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.video_url == "_{PAYPAL}_").count() > 0:
            if re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', message_text) is None:
                send_text(recipient_id, "Invalid email address, try again")

            else:
                for storefront in Storefront.query.filter(Storefront.owner_id == recipient_id):
                    storefront.video_url = None

                try:
                    conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('SELECT `id` FROM `payout` = 2 WHERE `user_id` = {user_id} LIMIT 1;'.format(user_id=customer.id))
                        row = cur.fetchone()
                        if row is None:
                            cur.execute('INSERT INTO `payout` (`id`, `user_id`, `paypal`, `updated`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP(), UTC_TIMESTAMP())' % (customer.id, message_text))
                        else:
                            cur.execute('UPDATE `payout` SET `paypal` = "{paypal}", `updated` = UTC_TIMESTAMP() WHERE `id` = {payout_id} LIMIT 1;'.format(paypal=message_text, payout_id=row['id']))
                        conn.commit()

                except mysql.Error, e:
                    logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                finally:
                    if conn:
                        conn.close()

                send_text(recipient_id, "PayPal email address set", main_menu_quick_replies(recipient_id))
            return "OK", 200


        #-- entering bitcoin payout
        elif Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.video_url == "_{BITCOIN}_").count() > 0:
            if re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', message_text) is None:
                send_text(recipient_id, "Invalid bitcoin address, it needs to start w/ 1 or 3, and be between 26 & 35 characters long.", quick_replies=cancel_entry_quick_reply())
                return "OK", 200

            else:
                for storefront in Storefront.query.filter(Storefront.owner_id == recipient_id):
                    storefront.video_url = None

                try:
                    conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('SELECT `id` FROM `payout` = 2 WHERE `user_id` = {user_id} LIMIT 1;'.format(user_id=customer.id))
                        row = cur.fetchone()
                        if row is None:
                            cur.execute('INSERT INTO `payout` (`id`, `user_id`, `bitcoin`, `updated`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP(), UTC_TIMESTAMP())' % (customer.id, message_text))
                        else:
                            cur.execute('UPDATE `payout` SET `bitcoin` = "{bitcoin}", `updated` = UTC_TIMESTAMP() WHERE `id` = {payout_id} LIMIT 1;'.format(bitcoin=message_text, payout_id=row['id']))
                        conn.commit()

                except mysql.Error, e:
                    logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                finally:
                    if conn:
                        conn.close()

                send_text(recipient_id, "Bitcoin payout address set", main_menu_quick_replies(recipient_id))
            return "OK", 200



        #-- check for message to customer
        purchase = None
        for storefront in Storefront.query.filter(Storefront.owner_id == recipient_id):
            purchase = Purchase.query.filter(Purchase.storefront_id == storefront.id).filter(Purchase.claim_state == 1).first()

            if purchase is not None:
                customer = Customer.query.filter(Customer.id == purchase.customer_id).first()
                purchase.claim_state = 2
                db.session.commit()

                try:
                    conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('UPDATE `purchases` SET `claim_state` = 2 WHERE `id` = {purchase_id};'.format(purchase_id=purchase.id))
                        conn.commit()

                except mysql.Error, e:
                    logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                finally:
                    if conn:
                        conn.close()


                send_text(customer.fb_psid, "{storefront_name} says:\n{message}".format(storefront_name=storefront.display_name, message=message_text))
                send_text(recipient_id, "Message sent to {customer_email}".format(customer_email=customer.email), quick_replies=(storefront.messenger_url))
                return "OK", 200


        #-- check for in-progress payment
        payment = Payment.query.filter(Payment.fb_psid == recipient_id).first()
        if payment is not None:
            product = Product.query.filter(Product.id == customer.product_id).first()
            storefront = Storefront.query.filter(Storefront.id == product.storefront_id).first()

            if payment.source == "card":
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

                        customer = Customer.query.filter(Customer.fb_psid == recipient_id).first()
                        send_text(
                            recipient_id = recipient_id,
                            message_text= "Are these details correct?\nEmail: {email}\nName: {full_name}\nCard #: {acct_number}\nExpiration: {expiration:%m/%Y}\nCVC / CVV2: {cvc}".format(email=payment.email, full_name=payment.full_name, acct_number=(re.sub(r'\d', "*", payment.acct_number)[:-4] + payment.acct_number[-4:]), expiration=payment.expiration, cvc=payment.cvc),
                            quick_replies = [
                                build_quick_reply(Const.KWIK_BTN_TEXT, "Yes", Const.PB_PAYLOAD_PAYMENT_YES),
                                build_quick_reply(Const.KWIK_BTN_TEXT, "No", Const.PB_PAYLOAD_PAYMENT_NO),
                            ] + cancel_entry_quick_reply()
                        )

            elif payment.source == "btc":
                if re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$', message_text) is None:
                    send_text(recipient_id, "Invalid bitcoin address, it needs to start w/ 1 or 3, and be between 26 & 35 characters long.", quick_replies=cancel_entry_quick_reply())

                else:
                    Payment.query.filter(Payment.fb_psid == recipient_id).delete()

                    customer.bitcoin_addr = message_text
                    purchase = Purchase(customer.id, storefront.id, product.id, 2)

                    try:
                        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('UPDATE `users` SET `bitcoin_addr` = "{bitcoin_addr}" WHERE `id` = {user_id} AND `bitcoin_addr` != "{bitcoin_addr}" LIMIT 1;'.format(bitcoin_addr=message_text, user_id=customer.id))
                            cur.execute('INSERT INTO `purchases` (`id`, `user_id`, `product_id`, `type`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP())' % (customer.id, product.id, 2))
                            conn.commit()

                            cur.execute('SELECT `id`, `added` FROM `purchases` WHERE `id` = @@IDENTITY LIMIT 1;')
                            row = cur.fetchone()

                            purchase.id = row['id']
                            customer.purchase_id = row['id']

                    except mysql.Error as e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()

                    db.session.add(purchase)
                    db.session.commit()
                    send_text(recipient_id, "Bitcoin address set, notifying the shop owner for your invoicce", main_menu_quick_replies(recipient_id))
                    send_text(
                        recipient_id = storefront.owner_id,
                        message_text = "Purchase complete for {product_name} at {pacific_time}.\nTo complete this order send the customer w/ bitcoin address {bitcoin_addr} a PayPal invoice now.".format(product_name=product.display_name, pacific_time=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%I:%M%P %Z').lstrip("0"), bitcoin_addr=message_text),
                        quick_replies = [
                            # build_quick_reply(Const.KWIK_BTN_TEXT, caption="Message Now", payload="%s-%s".format(payload=Const.PB_PAYLOAD_PURCHASE_MESSAGE, purchase_id=purchase.id)),
                            build_quick_reply(Const.KWIK_BTN_TEXT, caption="OK", payload=Const.PB_PAYLOAD_MAIN_MENU)
                        ]
                    )

            elif payment.source == "paypal":
                if re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', message_text) is None:
                    send_text(recipient_id, "Invalid email address, try again")

                else:
                    Payment.query.filter(Payment.fb_psid == recipient_id).delete()

                    customer.paypal_email = message_text
                    purchase = Purchase(customer.id, storefront.id, product.id, 3)

                    try:
                        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('UPDATE `users` SET `bitcoin_addr` = "{bitcoin_addr}" WHERE `id` = {user_id} AND `bitcoin_addr` != "{bitcoin_addr}" LIMIT 1;'.format(bitcoin_addr=message_text, user_id=customer.id))
                            cur.execute('INSERT INTO `purchases` (`id`, `user_id`, `product_id`, `type`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP())' % (customer.id, product.id, 3))
                            conn.commit()

                            cur.execute('SELECT `id`, `added` FROM `purchases` WHERE `id` = @@IDENTITY LIMIT 1;')
                            row = cur.fetchone()

                            purchase.id = row['id']
                            customer.purchase_id = row['id']

                    except mysql.Error as e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()

                    db.session.add(purchase)
                    db.session.commit()

                    send_text(recipient_id, "Paypal address set, notifying the shop owner for your invoice", main_menu_quick_replies(recipient_id))
                    send_text(
                        recipient_id = storefront.owner_id,
                        message_text = "Purchase complete for {product_name} at {pacific_time}.\nTo complete this order send the customer ({customer_email}) a PayPal invoice now.".format(product_name=product.display_name, pacific_time=datetime.utcfromtimestamp(purchase.added).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(Const.PACIFIC_TIMEZONE)).strftime('%I:%M%P %Z').lstrip("0"), customer_email=message_text),
                        quick_replies = [
                            # build_quick_reply(Const.KWIK_BTN_TEXT, caption="Message Now", payload="%s-%s".format(payload=Const.PB_PAYLOAD_PURCHASE_MESSAGE, purchase_id=purchase.id)),
                            build_quick_reply(Const.KWIK_BTN_TEXT, caption="OK", payload=Const.PB_PAYLOAD_MAIN_MENU)
                        ]
                    )

            db.session.commit()
            return "OK", 200


        #-- has active storefront
        if storefront_query.count() > 0:
            #-- look for in-progress product creation
            product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 5)
            if product_query.count() > 0:
                product = product_query.order_by(Product.added.desc()).first()

                #-- name submitted
                if product.creation_state == 1:
                    try:
                        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('SELECT `id` FROM `products` WHERE `display_name` = "{product_name}" ;'.format(product_name=message_text))
                            row = cur.fetchone()

                            if row is None:
                                product.creation_state = 2
                                product.display_name = message_text
                                product.name = re.sub(Const.IGNORED_NAME_PATTERN, "", message_text)
                                product.prebot_url = "http://prebot.me/{product_name}".format(product_name=product.name)
                                db.session.commit()

                                send_text(recipient_id, "Enter the price of {product_name} in USD. (example 78.00)".format(product_name=product.display_name))

                            else:
                                send_text(recipient_id, "That name is already taken, please choose another")

                    except mysql.Error, e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()


                elif product.creation_state == 2:
                    if message_text.replace(".", "", 1).isdigit():
                        product.creation_state = 3
                        product.price = round(float(message_text), 2)
                        db.session.commit()

                        send_text(recipient_id = recipient_id, message_text = "Select a date the product will be available.", quick_replies = [
                            build_quick_reply(Const.KWIK_BTN_TEXT, "Right Now", Const.PB_PAYLOAD_PRODUCT_RELEASE_NOW),
                            build_quick_reply(Const.KWIK_BTN_TEXT, "Next Month", Const.PB_PAYLOAD_PRODUCT_RELEASE_30_DAYS),
                            build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=2)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_60_DAYS),
                            build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=3)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_90_DAYS),
                            build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=4)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_120_DAYS)
                        ])

                    else:
                        send_text(recipient_id = recipient_id, message_text = "Enter a valid price in USD (example 78.00)")

                #-- entered text at wrong step
                else:
                    handle_wrong_reply(recipient_id)

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

                    send_text(recipient_id, "Great! Your message will be sent to your customers shortly.")
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
                    try:
                        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('SELECT `id` FROM `storefronts` WHERE `display_name` = "{storefront_name}" ;'.format(storefront_name=message_text))
                            row = cur.fetchone()

                            if row is None:
                                storefront.creation_state = 1
                                storefront.display_name = message_text
                                storefront.name = re.sub(Const.IGNORED_NAME_PATTERN, "", message_text)
                                storefront.prebot_url = "http://prebot.me/{storefront_name}".format(storefront_name=storefront.name)
                                db.session.commit()
                                send_text(recipient_id, "Explain what you are making or selling.")

                            else:
                                send_text(recipient_id, "That name is already taken, please choose another")

                    except mysql.Error, e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()


                #-- description entered
                elif storefront.creation_state == 1:
                    storefront.creation_state = 2
                    storefront.description = message_text
                    db.session.commit()

                    send_text(recipient_id, "Upload a Shopbot profile image.")

                #-- entered text at wrong step
                else:
                    handle_wrong_reply(recipient_id)

                return "OK", 200

            else:
                welcome_message(recipient_id, Const.CUSTOMER_REFERRAL, message_text)


def handle_wrong_reply(recipient_id):
    logger.info("handle_wrong_reply(recipient_id={recipient_id})".format(recipient_id=recipient_id))

    #-- customer message
    purchase = None
    for storefront in Storefront.query.filter(Storefront.owner_id == recipient_id):
        purchase = Purchase.query.filter(Purchase.storefront_id == storefront.id).filter(Purchase.claim_state == 1).first()

        if purchase is not None:
            customer = Customer.query.filter(Customer.id == purchase.customer_id).first()
            send_text(recipient_id, "Enter your message to {customer_email}".format(customer_email=customer.email))
            return "OK", 200

    #-- payment creation in-progress
    payment = Payment.query.filter(Payment.fb_psid == recipient_id).first()
    if payment is not None:
        if payment.source == "card" and payment.creation_state < 6:
            add_cc_payment(recipient_id)

        elif payment.source == "btc":
            send_text(recipient_id, "Invalid bitcoin address, it needs to start w/ 1 or 3, and be between 25 & 34 characters long.", quick_replies=cancel_entry_quick_reply())

        elif payment.source == "paypal":
            send_text(recipient_id, "Invalid email address, try again")

        return "OK", 200

    #-- storefront creation in-progress
    query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state < 4)
    if query.count() > 0:
        storefront = query.first()

        send_text(recipient_id, "Incorrect response!")
        if storefront.creation_state == 0:
            send_text(recipient_id, "Give your Shopbot a name.")

        elif storefront.creation_state == 1:
            send_text(recipient_id, "Explain what you are making or selling.")

        elif storefront.creation_state == 2:
            send_text(recipient_id, "Upload a Shopbot profile image.")

        elif storefront.creation_state == 3:
            send_text(recipient_id, "Here's what your Shopbot will look like:")
            send_storefront_card(recipient_id, storefront.id, Const.CARD_TYPE_STOREFRONT_PREVIEW)

    #-- product creation in progress
    else:
        storefront = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 4).first()

        if storefront is None:
            send_admin_carousel(recipient_id)
            return "OK", 200

        query = Product.query.filter(Product.storefront_id == storefront.id).filter(Product.creation_state < 5)
        if query.count() > 0:
            product = query.order_by(Product.added.desc()).first()
            send_text(recipient_id, "Incorrect response!")
            if product.creation_state == 0:
                send_text(recipient_id, "Upload a photo or video of what you are selling.")

            elif product.creation_state == 1:
                send_text(recipient_id, "Give your product a title.")

            elif product.creation_state == 2:
                send_text(recipient_id, "Enter the price of {product_name} in USD. (example 78.00)".format(product_name=product.display_name))

            elif product.creation_state == 3:
                send_text(recipient_id = recipient_id, message_text = "Select a date the product will be available.", quick_replies = [
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Right Now", Const.PB_PAYLOAD_PRODUCT_RELEASE_NOW),
                    build_quick_reply(Const.KWIK_BTN_TEXT, "Next Month", Const.PB_PAYLOAD_PRODUCT_RELEASE_30_DAYS),
                    build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=2)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_60_DAYS),
                    build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=3)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_90_DAYS),
                    build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=4)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_120_DAYS)
                ])

            elif product.creation_state == 4:
                send_text(recipient_id, "Here's what your product will look like:")
                send_product_card(recipient_id=recipient_id, product_id=product.id, card_type=Const.CARD_TYPE_PRODUCT_PREVIEW)

    return "OK", 200


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


@app.route('/', methods=['POST'])
def  webook():

    #if 'delivery' in request.data or 'read' in request.data or 'optin' in request.data:
    #    return "OK", 200

    data = request.get_json()

    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    logger.info("[=-=-=-=-=-=-=-[POST DATA]-=-=-=-=-=-=-=-=]")
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    logger.info(data)
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")

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
                referral = None

                if sender_id == "1214675165306847":
                    logger.info("-=- BYPASS-USER -=-")
                    return "OK", 200

                if 'echo' in messaging_event:
                    logger.info("-=- MESSAGE-ECHO -=-")
                    return "OK", 200

                if 'delivery' in messaging_event:  # delivery confirmatio
                    # logger.info("-=- DELIVERY-CONFIRM -=-")
                    return "OK", 200

                if 'read' in messaging_event:  # read confirmation
                    # logger.info("-=- READ-CONFIRM -=- %s" % (recipient_id))
                    send_tracker("read-receipt", sender_id, "")
                    return "OK", 200

                if 'optin' in messaging_event:  # optin confirmation
                    # logger.info("-=- OPT-IN -=-")
                    return "OK", 200



                if 'referral' in messaging_event:
                    referral = messaging_event['referral']['ref'].encode('ascii', 'ignore')

                #-- check mysql for user
                try:
                    conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
                    with conn:
                        cur = conn.cursor(mysql.cursors.DictCursor)
                        cur.execute('SELECT `id` FROM `users` WHERE `fb_psid` = "{fb_psid}" LIMIT 1;'.format(fb_psid=sender_id))
                        row = cur.fetchone()

                        if row is None:
                            send_tracker("sign-up", sender_id, "")
                            add_new_user(sender_id, referral)

                        else:
                            if referral is not None:
                                cur.execute('UPDATE `users` SET `referrer` = "{referrer}" WHERE `fb_psid` = "{fb_psid}" LIMIT 1;'.format(referrer=referral, fb_psid=sender_id))
                                conn.commit()

                except mysql.Error, e:
                    logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                finally:
                    if conn:
                        conn.close()



                #-- entered via url referral
                if referral is not None:
                    welcome_message(sender_id, Const.CUSTOMER_REFERRAL, referral[1:])
                    return "OK", 200



                logger.info("USERS -->%s" % (Customer.query.filter(Customer.fb_psid == sender_id).first()))

                #-- look for created storefront
                storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 4)
                logger.info("STOREFRONTS -->%s" % (Storefront.query.filter(Storefront.owner_id == sender_id).all()))

                if storefront_query.count() > 0:
                    logger.info("PRODUCTS -->%s" % (Product.query.filter(Product.storefront_id == storefront_query.first().id).all()))
                    logger.info("SUBSCRIPTIONS -->%s" % (Subscription.query.filter(Subscription.storefront_id == storefront_query.first().id).all()))
                    logger.info("PURCHASES -->%s" % (Purchase.query.filter(Purchase.storefront_id == storefront_query.first().id).all()))
                    logger.info("PURCHASED -->%s" % (Purchase.query.filter(Purchase.customer_id == storefront_query.first().id).all()))


                #-- postback response w/ payload
                if 'postback' in messaging_event:  # user clicked/tapped "postback" button in earlier message
                    payload = messaging_event['postback']['payload']
                    logger.info("-=- POSTBACK RESPONSE -=- (%s)" % (payload))
                    received_payload_button(sender_id, payload, referral)
                    return "OK", 200


                #-- actual message
                if 'message' in messaging_event:
                    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECEIVED ->{message}".format(message=messaging_event['sender']))

                    message = messaging_event['message']
                    message_id = message['mid']
                    message_text = ""

                    #-- insert to log
                    write_message_log(sender_id, message_id, message)

                    if 'quick_reply' in message:
                        quick_reply = message['quick_reply']['payload']
                        logger.info("QR --> {quick_replies}".format(quick_replies=quick_reply))
                        received_quick_reply(sender_id, quick_reply)
                        return "OK", 200


                    if 'attachments' in message:
                        for attachment in message['attachments']:
                            recieved_attachment(sender_id, attachment['type'], attachment['payload'])
                        return "OK", 200



                    if 'text' in message:
                        received_text_response(sender_id, message['text'].encode('ascii', 'ignore'))
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


def send_video(recipient_id, url, attachment_id=None, quick_replies=None):
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            "id" : recipient_id
        },
        'message' : {
            'attachment' : {
                'type'    : "video",
                'payload' : {
                    'url'         : url,
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

    return True


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


if __name__ == '__main__':
    from gevent import monkey
    monkey.patch_all()

    logger.info("Firin up FbBot using verify token [{verify_token}].".format(verify_token=Const.VERIFY_TOKEN))
    app.run(debug=True)
