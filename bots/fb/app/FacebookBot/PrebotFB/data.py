#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import datetime

from models import db
from named_constants import Constants

class Consts(Constants):
    VERIFY_TOKEN = "6ba2254db1c8eed1e52815287f85acb8da96aeaae36db217"
    ACCESS_TOKEN = "EAADzAMIzYPEBAJGk5P18ibMeEBhhdvUzZBsMoItnuB19PEzUGnNZALX5MN1rK0HKEfSG4YsmyVM2NmeK3m9wcmDvmwoB97aqfn1U0KOdvNtv6ZCgPLvqPFr2YbnlinuUUSrPtnphqafj6ad73wIPVBCOhCaiLGfvEZCUr7CxcAZDZD"

    WEB_SERVER_IP = "192.241.212.32"

    MYSQL_HOST = '138.197.216.56'
    MYSQL_NAME = 'prebot_marketplace'
    MYSQL_USER = 'pre_usr'
    MYSQL_PASS = 'f4zeHUga.age'

    ORTHODOX_GREETING = "Welcome to Pre. A new way to pre-sell products before their release."
    GOODBYE_MESSAGE = "Ok, Thanks. Goodbye!"
    UNKNOWN_MESSAGE = "I'm sorry, I cannot understand that type of message."

    IMAGE_URL_CREATE_SHOP = "https://i.imgur.com/R3p8qEA.png"
    IMAGE_URL_ADD_PRODUCT = "https://i.imgur.com/ggLeUwX.png"
    IMAGE_URL_SHARE_STOREFRONT = "https://i.imgur.com/XUMntb0.png"
    IMAGE_URL_MARKETPLACE = "https://i.imgur.com/3Ozq4Wm.png"
    IMAGE_URL_NOTIFY_SUBSCRIBERS = "https://i.imgur.com/jXIttcH.png"
    IMAGE_URL_SUPPORT = "https://i.imgur.com/wm00Cin.png"

    MARKETPLACE_GREETING = 'MARKETPLACE_GREETING'
    STOREFRONT_ADMIN = 'STOREFRONT_ADMIN'
    CUSTOMER_EMPTY = 'CUSTOMER_EMPTY'
    CUSTOMER_REFERRAL = 'CUSTOMER_REFERRAL'
    CUSTOMER_STOREFRONT = 'CUSTOMER_STOREFRONT'
    CUSTOMER_PRODUCT = 'CUSTOMER_PRODUCT'

    CARD_TYPE_STOREFRONT = 'CARD_STOREFRONT'
    CARD_TYPE_PREVIEW_STOREFRONT = 'CARD_PREVIEW_STOREFRONT'
    CARD_TYPE_SHARE_STOREFRONT = 'CARD_SHARE_STOREFRONT'
    CARD_TYPE_PRODUCT = 'CARD_PRODUCT'
    CARD_TYPE_PREVIEW_PRODUCT = 'CARD_PREVIEW_PRODUCT'
    CARD_TYPE_SHARE_PRODUCT = 'CARD_SHARE_PRODUCT'
    CARD_TYPE_SUPPORT = 'CARD_SUPPORT'
    CARD_TYPE_NOTIFY_SUBSCRIBERS = 'CARD_NOTIFY_SUBSCRIBERS'


    CARD_BTN_POSTBACK = 'postback'
    CARD_BTN_URL = 'web_url'
    CARD_BTN_INVITE = 'element_share'
    KWIK_BTN_TEXT = 'text'
    KWIK_BTN_LOCATION = 'location'

    PB_PAYLOAD_ORTHODOX = 'ORTHODOX_PAYLOAD'
    PB_PAYLOAD_GREETING = 'WELCOME_MESSAGE'

    PB_PAYLOAD_CREATE_STOREFRONT = 'CREATE_STOREFRONT'
    PB_PAYLOAD_DELETE_STOREFRONT = 'DELETE_STOREFRONT'
    PB_PAYLOAD_SUBMIT_STOREFRONT = 'SUBMIT_STOREFRONT'
    PB_PAYLOAD_REDO_STOREFRONT = 'REDO_STOREFRONT'
    PB_PAYLOAD_CANCEL_STOREFRONT = 'CANCEL_STOREFRONT'

    PB_PAYLOAD_ADD_PRODUCT = 'ADD_PRODUCT'
    PB_PAYLOAD_DELETE_PRODUCT = 'DELETE_PRODUCT'
    PB_PAYLOAD_SUBMIT_PRODUCT = 'SUBMIT_PRODUCT'
    PB_PAYLOAD_REDO_PRODUCT = 'REDO_PRODUCT'
    PB_PAYLOAD_CANCEL_PRODUCT = 'CANCEL_PRODUCT'

    PB_PAYLOAD_PRODUCT_RELEASE_NOW = 'PRODUCT_RELEASE_0_DAYS'
    PB_PAYLOAD_PRODUCT_RELEASE_30_DAYS = 'PRODUCT_RELEASE_30_DAYS'
    PB_PAYLOAD_PRODUCT_RELEASE_60_DAYS = 'PRODUCT_RELEASE_60_DAYS'
    PB_PAYLOAD_PRODUCT_RELEASE_90_DAYS = 'PRODUCT_RELEASE_90_DAYS'
    PB_PAYLOAD_PRODUCT_RELEASE_120_DAYS = 'PRODUCT_RELEASE_120_DAYS'

    PB_PAYLOAD_RESERVE_PRODUCT = 'RESERVE_PRODUCT'
    PB_PAYLOAD_SHARE_STOREFRONT = 'SHARE_STOREFRONT'
    PB_PAYLOAD_VIEW_MARKETPLACE = 'VIEW_MARKETPLACE'
    PB_PAYLOAD_SUPPORT = 'SUPPORT'
    PB_PAYLOAD_CUSTOMERS = 'CUSTOMERS'
    PB_PAYLOAD_NOTIFY_SHOP_OWNER = 'NOTIFY_SHOP_OWNER'
    PB_PAYLOAD_NOTIFY_SUBSCRIBERS = 'NOTIFY_SUBSCRIBERS'


    RESERVED_MENU_REPLIES = "admin|main|main menu|menu|help|support"
    RESERVED_STOP_REPLIES = "cancel|end|quit|stop"



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
    fb_psid = db.Column(db.String(80))
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
    enabled = db.Column(db.Boolean)
    added = db.Column(db.DateTime)

    def __init__(self, storefront_id, fb_psid, creation_state=0):
        self.storefront_id = storefront_id
        self.fb_psid = fb_psid
        self.creation_state = creation_state
        self.description = ""
        self.price = 0.0
        self.attachment_id = ""
        self.enabled = True

    def __repr__(self):
        return "<Product storefront_id=%d, creation_state=%d, display_name=%s, enabled=%s, release_date=%s>" % (self.storefront_id, self.creation_state, self.display_name, self.enabled, self.release_date)


class Storefront(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer)
    fb_psid = db.Column(db.String(80))
    creation_state = db.Column(db.Integer)
    name = db.Column(db.String(80))
    display_name = db.Column(db.String(80))
    description = db.Column(db.String(200))
    logo_url = db.Column(db.String(500))
    prebot_url = db.Column(db.String(128), unique=True)
    enabled = db.Column(db.Boolean)
    added = db.Column(db.DateTime)

    def __init__(self, owner_id, fb_psid, creation_state=0):
        self.owner_id = owner_id
        self.fb_psid = fb_psid
        self.creation_state = creation_state
        self.enabled = True

    def __repr__(self):
        return "<Storefront owner_id=%s, creation_state=%d, display_name=%s, logo_url=%s, enabled=%s>" % (self.owner_id, self.creation_state, self.display_name, self.logo_url, self.enabled)


class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    storefront_id = db.Column(db.Integer)
    product_id = db.Column(db.Integer)
    customer_id = db.Column(db.Integer)
    fb_psid = db.Column(db.String(80))
    enabled = db.Column(db.Boolean)
    added = db.Column(db.DateTime)

    def __init__(self, storefront_id, product_id, customer_id, fb_psid, enabled=True):
        self.storefront_id = storefront_id
        self.product_id = product_id
        self.customer_id = customer_id
        self.fb_psid = fb_psid
        self.enabled = enabled
        self.added = datetime.utcnow()

    def __repr__(self):
        return "<Subscription storefront_id=%d, product_id=%d, customer_id=%d, enabled=%s>" % (self.storefront_id, self.product_id, self.customer_id, self.enabled)



