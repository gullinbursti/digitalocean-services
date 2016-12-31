#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import cStringIO
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
import urllib

from datetime import date, datetime, timedelta
from time import mktime
from urllib import urlopen

import av
import gevent
import grequests
import MySQLdb as mdb
import pycurl
import requests

from flask import Flask, escape, request
from flask_sqlalchemy import SQLAlchemy
from gevent import monkey; monkey.patch_all()

import const as Const




app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///prebotfb.db"
db = SQLAlchemy(app)


gevent.monkey.patch_all()
locale.setlocale(locale.LC_ALL, 'en_US.utf8')

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler("/var/log/FacebookBot.log")
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)


Const.VERIFY_TOKEN = "6ba2254db1c8eed1e52815287f85acb8da96aeaae36db217"
Const.ACCESS_TOKEN = "EAADzAMIzYPEBAEaJZCHO4bSF36ZB8Jlue86Sp3g1QujTbTOjBoA4N92IOAxZA7JHgX5tPHT62m0sZCG5TUZATLw5uvsUCjtgHkmzveAWZAyR9V9NUiBPNxG5lXKsl71gyROy8hZBHfZA1yMH0ZBieu6RIIID8Tynbh3EZCVzv4nJZBowAZDZD"

Const.WEB_SERVER_IP = "192.241.212.32"

Const.ORTHODOX_GREETING = "Welcome to Pre. The first chatbot for makers. Tap below to create your own Shop Bot."
Const.IMAGE_URL_CREATE_SHOP = "https://i.imgur.com/9PGh9vO.png"
Const.IMAGE_URL_ADD_PRODUCT = "https://i.imgur.com/ipSd9dP.png"
Const.IMAGE_URL_SHARE_STOREFRONT = "https://i.imgur.com/XUMntb0.png"
Const.IMAGE_URL_MARKETPLACE = "https://i.imgur.com/XUMntb0.png"
Const.IMAGE_URL_SUPPORT = "https://i.imgur.com/4aOGaoi.png"

Const.MARKETPLACE_GREETING = 'MARKETPLACE_GREETING'
Const.STOREFRONT_ADMIN = 'STOREFRONT_ADMIN'
Const.CUSTOMER_EMPTY = 'CUSTOMER_EMPTY'
Const.CUSTOMER_STOREFRONT = 'CUSTOMER_STOREFRONT'
Const.CUSTOMER_PRODUCT = 'CUSTOMER_PRODUCT'

Const.CARD_BTN_POSTBACK = 'postback'
Const.CARD_BTN_URL = 'web_url'
Const.CARD_BTN_INVITE = 'element_share'
Const.KWIK_BTN_TEXT = 'text'
Const.KWIK_BTN_LOCATION = 'location'

Const.PB_PAYLOAD_ORTHODOX = 'ORTHODOX_PAYLOAD'
Const.PB_PAYLOAD_GREETING = 'WELCOME_MESSAGE'
Const.PB_PAYLOAD_CREATE_STOREFRONT = 'CREATE_STOREFRONT'
Const.PB_PAYLOAD_DELETE_STOREFRONT = 'DELETE_STOREFRONT'
Const.PB_PAYLOAD_SUBMIT_STOREFRONT = 'SUBMIT_STOREFRONT'
Const.PB_PAYLOAD_UNDO_STOREFRONT = 'UNDO_STOREFRONT'
Const.PB_PAYLOAD_ADD_STOREFRONT_ITEM = 'ADD_STOREFRONT_ITEM'
Const.PB_PAYLOAD_DELETE_STOREFRONT_ITEM = 'DELETE_STOREFRONT_ITEM'
Const.PB_PAYLOAD_PRODUCT_RELEASE_NOW = 'PRODUCT_RELEASE_0_DAYS'
Const.PB_PAYLOAD_PRODUCT_RELEASE_30_DAYS = 'PRODUCT_RELEASE_30_DAYS'
Const.PB_PAYLOAD_PRODUCT_RELEASE_60_DAYS = 'PRODUCT_RELEASE_60_DAYS'
Const.PB_PAYLOAD_PRODUCT_RELEASE_90_DAYS = 'PRODUCT_RELEASE_90_DAYS'
Const.PB_PAYLOAD_PRODUCT_RELEASE_120_DAYS = 'PRODUCT_RELEASE_120_DAYS'

Const.PB_PAYLOAD_SUBMIT_PRODUCT = 'SUBMIT_PRODUCT'
Const.PB_PAYLOAD_UNDO_PRODUCT = 'UNDO_PRODUCT'
Const.PB_PAYLOAD_SHARE_STOREFRONT = 'SHARE_STOREFRONT'
Const.PB_PAYLOAD_SUPPORT = 'SUPPORT'
Const.PB_PAYLOAD_CUSTOMERS = 'CUSTOMERS'
Const.PB_PAYLOAD_RESERVE = 'RESERVE'


#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


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


class Product(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  storefront_id = db.Column(db.Integer)
  creation_state = db.Column(db.Integer)
  name = db.Column(db.String(80))
  display_name = db.Column(db.String(80))
  description = db.Column(db.String(200))
  image_url = db.Column(db.String(500))
  video_url = db.Column(db.String(500))
  price = db.Column(db.Float)
  prebot_url = db.Column(db.String(128), unique=True)
  release_date = db.Column(db.DateTime)
  added = db.Column(db.DateTime)
  
  def __init__(self, storefront_id, creation_state=0):
    self.storefront_id = storefront_id
    self.creation_state = creation_state

  def __repr__(self):
    return "<Product storefront_id=%d, creation_state=%d, display_name=%s, release_date=%s>" % (self.storefront_id, self.creation_state, self.display_name, self.release_date)



#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#



def async_send_evt_tracker(urls):
  logger.info("send_evt_tracker(len(urls)=%d)" % (len(urls)))
  
  responses = (grequests.get(u) for u in urls)
  grequests.map(responses)
  
  

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
  
  # try:
  #   conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
  #   with conn:
  #     cur = conn.cursor()
  #     cur.execute("INSERT IGNORE INTO `fbbot_logs` (`id`, `message_id`, `chat_id`, `body`) VALUES (NULL, \'{message_id}\', \'{sender_id}\', \'{message_txt}\')".format(message_id=message_id, sender_id=sender_id, message_txt=message_txt))
  #     
  # except mdb.Error, e:
  #   logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))
  # 
  # finally:
  #   if conn:    
  #     conn.close()
  
  

def build_button(btn_type, caption="", url="", payload=""):
  logger.info("build_button(btn_type={btn_type}, caption={caption}, payload={payload})".format(btn_type=btn_type, caption=caption, payload=payload))
  
  if btn_type == Const.CARD_BTN_POSTBACK:
    button = {
      'type' : "postback",
      'payload' : payload,
      'title' : caption
    }
    
  elif btn_type == Const.CARD_BTN_URL:
    button = {
      'type' : "web_url",
      'url' : url,
      'title' : caption
    }
    
  elif btn_type == Const.CARD_BTN_INVITE:
    button = { 'type': "element_share" }
    
  elif btn_type == Const.KWIK_BTN_TEXT:
    button = {
      'content_type' : "text",
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
  

def build_content_card(recipient_id, title, subtitle, image_url, item_url, buttons=None, quick_replies=None):
  logger.info("build_content_card(recipient_id=%s, title=%s, subtitle=%s, image_url=%s, item_url=%s, buttons=%s, quick_replies=%s)")
  
  data = {
    'recipient' : {
      'id' : recipient_id
    },
    'message' : {
      'attachment' : {
        'type' : "template",
        'payload' : {
          'template_type' : "generic",
          'elements' : [{
            'title' : title, 
            'subtitle' : subtitle,
            'image_url' : image_url,
            'item_url' : item_url
          }]
        }
      }
    }
  }
  
  if buttons is not None:
    data['message']['attachment']['payload']['elements'][0]['buttons'] = buttons
  
  if quick_replies is not None:
    data['message']['quick_replies'] = quick_replies
    
  return data




def build_carousel_element(index, title, subtitle, image_url, item_url, buttons=None):
  logger.info("build_carousel_element(index=%d, title=%s, subtitle=%s, image_url=%s, item_url=%s, buttons=%s, quick_replies=%s)")
  
  element = {
    'title' : title, 
    'subtitle' : subtitle,
    'image_url' : image_url, 
    'item_url' : item_url
  }
  
  if buttons is not None:
    element['buttons'] = buttons
  
  return element


def build_carousel(recipient_id, cards, quick_replies=None):
  logger.info("build_carousel(recipient_id={recipient_id})".format(recipient_id=recipient_id))
  
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
  logger.info("welcome_message(recipient_id={recipient_id}, entry_type={entry_type})".format(recipient_id=recipient_id, entry_type=entry_type))
  
  send_video(recipient_id, "http://{ip_addr}/videos/intro_all.mp4".format(ip_addr=Const.WEB_SERVER_IP))
  if entry_type == Const.MARKETPLACE_GREETING:
    send_text(recipient_id, Const.ORTHODOX_GREETING)
    send_admin_carousel(recipient_id)
    
  elif entry_type == Const.STOREFRONT_ADMIN:
    send_text(recipient_id, Const.ORTHODOX_GREETING)
    send_admin_carousel(recipient_id)
    
  elif entry_type == Const.CUSTOMER_EMPTY:
    send_text(recipient_id, Const.ORTHODOX_GREETING)
    send_admin_carousel(recipient_id)
    
  elif entry_type == Const.CUSTOMER_STOREFRONT:
    storefront_query = Storefront.query.filter(Storefront.name == deeplink)
    if storefront_query.count() > 0:
      storefront = storefront_query.first()      
      send_text(recipient_id, "Welcome to {storefront_name}'s Shop Bot on Pre. You have been subscribed to {storefront_name} updates.".format(storefront_name=storefront.display_name))
      send_storefront_carousel(recipient_id, storefront.id)
      
    else:
      send_text(recipient_id, Const.ORTHODOX_GREETING)
      send_admin_carousel(recipient_id)
    
  elif entry_type == Const.CUSTOMER_PRODUCT:
    product_query = Product.query.filter(Product.name == deeplink)
    if product_query.count() > 0:
      product = product.first()
      storefront_query = Storefront.query.filter(Storefront.id == product.storefront_id)
      
      if storefront_query.count() > 0:
        storefront = storefront_query.first()
        send_text(recipient_id, "Welcome to {storefront_name}'s Shop Bot on Pre. You have been subscribed to {storefront_name} updates.".format(storefront_name=storefront.display_name))
        send_storefront_carousel(recipient_id, storefront.id)
        
      else:
        send_text(recipient_id, Const.ORTHODOX_GREETING)
        send_admin_carousel(recipient_id)
        
    else:
      send_text(recipient_id, Const.ORTHODOX_GREETING)
      send_admin_carousel(recipient_id)
        
  else:
    send_text(recipient_id, Const.ORTHODOX_GREETING)
    send_admin_carousel(recipient_id)
  


def send_admin_carousel(recipient_id):
  logger.info("send_admin_carousel(recipient_id={recipient_id})".format(recipient_id=recipient_id))
  
  #-- look for created storefront
  storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id)
  cards = []
  
  if storefront_query.count() == 0:
    cards.append(
      build_carousel_element(
        index = 0, 
        title = "Create Shop", 
        subtitle = "", 
        image_url = Const.IMAGE_URL_CREATE_SHOP, 
        item_url = "http://prebot.me/shop/new", 
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
      storefront.description = "[DESCRIPTION NOT SET]"
      
    if storefront.logo_url is None:
      storefront.logo_url = Const.IMAGE_URL_ADD_PRODUCT
      
    if storefront.prebot_url is None:
      storefront.prebot_url = "http://prebot.me"
      
    cards.append(
      build_carousel_element(
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
    
    product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id)#.filter(Product.creation_state == 4)
    if product_query.count() == 0:
      cards.append(
        build_carousel_element(
          index = 1, 
          title = "Add Item", 
          subtitle = "", 
          image_url = Const.IMAGE_URL_ADD_PRODUCT, 
          item_url = "http://prebot.me/shop/add", 
          buttons = [
            build_button(Const.CARD_BTN_POSTBACK, caption="Add Item", payload=Const.PB_PAYLOAD_ADD_STOREFRONT_ITEM)
          ]
        )
      )
      
    else:
      product = product_query.first()
      
      if product.prebot_url is None:
        product.prebot_url = "http://prebot.me"
      
      if product.display_name is None:
        product.display_name = "[NAME NOT SET]"

      if product.video_url is None:
        product.image_url = Const.IMAGE_URL_ADD_PRODUCT
        product.video_url = "http://{ip_addr}/videos/product_default.mp4".format(ip_addr=Const.WEB_SERVER_IP)

      cards.append(
        build_carousel_element(
          index = 1, 
          title = product.display_name, 
          subtitle = "",
          image_url = product.image_url, 
          item_url = product.video_url, 
          buttons = [
            build_button(Const.CARD_BTN_POSTBACK, caption="Remove Item", payload=Const.PB_PAYLOAD_DELETE_STOREFRONT_ITEM)
          ]
        )
      )
          
    cards.append(
      build_carousel_element(
        index = 2, 
        title = "Share Shop", 
        subtitle = "", 
        image_url = Const.IMAGE_URL_SHARE_STOREFRONT, 
        item_url = "http://prebot.me/share", 
        buttons = [
          build_button(Const.CARD_BTN_POSTBACK, caption="Share Shop", payload=Const.PB_PAYLOAD_SHARE_STOREFRONT)
        ]
      )
    )
        
  cards.append(
    build_carousel_element(
      index = 3, 
      title = "View Shops", 
      subtitle = "", 
      image_url = Const.IMAGE_URL_MARKETPLACE, 
      item_url = "http://prebot.me/marketplace", 
      buttons = [
        build_button(Const.CARD_BTN_URL, caption="View Shops", url="http://prebot.me/marketplace")
      ]
    )
  )
  
  cards.append(
    build_carousel_element(
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
  
  data = build_carousel(
    recipient_id = recipient_id, 
    cards = cards
  )
  
  send_message(json.dumps(data))
  
  
def send_storefront_preview(recipient_id):
  logger.info("send_storefront_preview(recipient_id={recipient_id})".format(recipient_id=recipient_id))
  logger.info("STOREFRONTS -->%s" % (Storefront.query.filter(Storefront.owner_id == recipient_id).all()))
  
  query = Storefront.query.filter(Storefront.owner_id == recipient_id).filter(Storefront.creation_state == 3)
  if query.count() > 0:
    storefront = query.first()
    
    data = build_content_card(
      recipient_id = recipient_id, 
      title = storefront.display_name, 
      subtitle = storefront.description, 
      image_url = storefront.logo_url, 
      item_url = storefront.prebot_url, 
      quick_replies = [
        build_quick_reply(Const.KWIK_BTN_TEXT, "Submit", Const.PB_PAYLOAD_SUBMIT_STOREFRONT),
        build_quick_reply(Const.KWIK_BTN_TEXT, "Cancel", Const.PB_PAYLOAD_UNDO_STOREFRONT)
      ]
    )
    
    send_message(json.dumps(data))


def send_storefront_carousel(recipient_id, storefront_id, product_name=""):
  logger.info("send_storefront_carousel(recipient_id={recipient_id}, storefront_id={storefront_id})".format(recipient_id=recipient_id, storefront_id=storefront_id))
  
  query = Storefront.query.filter(Storefront.id == storefront_id)
  if query.count() > 0:
    storefront = query.first()
    
    query = Product.query.filter(Product.storefront_id == storefront.id)
    if query.count() > 0:
      product = query.first()
      
      data = build_carousel(
        recipient_id = recipient_id, 
        cards = [
          build_carousel_element(
            index = 0, 
            title = product.display_name, 
            subtitle = "", 
            image_url = product.image_url, 
            item_url = product.prebot_url, 
            buttons = [
              build_button(Const.CARD_BTN_URL, caption="Reserve Now", url="http://prebot.me/products/{product_id}"),
              build_button(Const.CARD_BTN_INVITE)
            ]
          ),
          build_carousel_element(
            index = 1, 
            title = storefront.display_name, 
            subtitle = "", 
            image_url = storefront.logo_url, 
            item_url = storefront.prebot_url, 
            buttons = [
              build_button(Const.CARD_BTN_INVITE)
            ]
          ),
          build_carousel_element(
            index = 3, 
            title = "View Shops", 
            subtitle = "", 
            image_url = Const.IMAGE_URL_MARKETPLACE, 
            item_url = "http://prebot.me/marketplace", 
            buttons = [
              build_button(Const.CARD_BTN_URL, caption="View Shops", url="http://prebot.me/marketplace")
            ]
          ),
          build_carousel_element(
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
  
  
def send_product_preview(recipient_id, product_id):
  logger.info("send_product_preview(recipient_id={recipient_id}, product_id={product_id})".format(recipient_id=recipient_id, product_id=product_id))
  logger.info("PRODUCTS -->%s" % (Product.query.filter(Product.id == recipient_id).all()))
  
  query = Product.query.filter(Product.id == product_id)
  if query.count() > 0:
    product = query.first()
    
    if product.image_url is None:
      product.image_url = Const.IMAGE_URL_ADD_PRODUCT
    
    if product.video_url is None:
      product.video_url = "http://{ip_addr}/videos/product_default.mp4".format(ip_addr=Const.WEB_SERVER_IP)
    
    data = build_content_card(
      recipient_id = recipient_id, 
      title = product.display_name, 
      subtitle = "", 
      image_url = product.image_url, 
      item_url = product.video_url, 
      quick_replies = [
        build_quick_reply(Const.KWIK_BTN_TEXT, "Submit", Const.PB_PAYLOAD_SUBMIT_PRODUCT),
        build_quick_reply(Const.KWIK_BTN_TEXT, "Cancel", Const.PB_PAYLOAD_UNDO_PRODUCT)
      ]
    )
  
    send_message(json.dumps(data))


def send_share_card(recipient_id, is_product=True):
  logger.info("send_share_card(recipient_id={recipient_id})".format(recipient_id=recipient_id))
  
  storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id)
  storefront = storefront_query.first()
  product_query = Product.query.filter(Product.storefront_id == storefront.id).filter(Product.creation_state == 4)
  
  if product_query.count() == 0 or is_product == False:
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
    product = product_query.first()
    data = build_content_card(
      recipient_id = recipient_id, 
      title = product.display_name, 
      subtitle = "", 
      image_url = product.image_url, 
      item_url = product.video_url, 
      buttons = [
        build_button(Const.CARD_BTN_INVITE)
      ]
    )
  
  send_message(json.dumps(data))
    


@app.route('/', methods=['POST'])
def webook():
  data = request.get_json()
  
  logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
  logger.info("[=-=-=-=-=-=-=-[POST DATA]-=-=-=-=-=-=-=-=]")
  logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
  logger.info(data)
  logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
  logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")

  if data['object'] == "page":
    for entry in data['entry']:
      for messaging_event in entry['messaging']:
        sender_id = messaging_event['sender']['id']
        recipient_id = messaging_event['recipient']['id']  # the recipient's ID, which should be your page's facebook ID
        timestamp = messaging_event['timestamp']
        
        message_id = None
        message_text = None
        quick_reply = None
        
        if 'delivery' in messaging_event:  # delivery confirmation
          logger.info("-=- DELIVERY CONFIRM -=-")
          return "OK", 200
          
        if 'read' in messaging_event:  # read confirmation
          logger.info("-=- READ CONFIRM -=- %s" % (messaging_event))
          send_tracker("read-receipt", sender_id, "")
          return "OK", 200

        if 'optin' in messaging_event:  # optin confirmation
          logger.info("-=- OPT-IN -=-")
          return "OK", 200
        
        # try:
        #   total = db.session.query(Storefront).delete()
        #   db.session.commit()
        # except:
        #   db.session.rollback()
        
        # try:
        #   total = db.session.query(Product).delete()
        #   db.session.commit()
        # except:
        #   db.session.rollback()
        
        
        #-- look for created storefront
        storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 4)
        logger.info("STOREFRONTS -->%s" % (Storefront.query.filter(Storefront.owner_id == sender_id).all()))
        
        if storefront_query.count() > 0:
          logger.info("PRODUCTS -->%s" % (Product.query.filter(Product.storefront_id == storefront_query.first().id).all()))
        
        referral = ""
        #-- entered via url referral
        # if 'referral' in messaging_event:
        #   referral = messaging_event['referral']
          
        
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
            
            send_text(sender_id, "Create a new bot shop by picking a name for your store...")
            
              
          elif payload == Const.PB_PAYLOAD_DELETE_STOREFRONT:    
            send_tracker("button-delete-shop", sender_id, "")
            
            for storefront in Storefront.query.filter(Storefront.owner_id == sender_id):
              send_text(sender_id, "Removing your existing shop \"{storefront_name}\"...".format(storefront_name=storefront.display_name))
              Product.query.filter(Product.storefront_id == storefront.id).delete()
            
            Storefront.query.filter(Storefront.owner_id == sender_id).delete()
            db.session.commit()
            
            send_admin_carousel(sender_id)
            
            
          elif payload == Const.PB_PAYLOAD_ADD_STOREFRONT_ITEM:
            send_tracker("button-add-item", sender_id, "")
            db.session.add(Product(storefront_query.first().id))
            db.session.commit()
            
            send_text(sender_id, "What is your product's name?")
            
            
          elif payload == Const.PB_PAYLOAD_DELETE_STOREFRONT_ITEM:
            send_tracker("button-delete-item", sender_id, "")
            
            storefront = storefront_query.first()
            for product in Product.query.filter(Product.storefront_id == storefront.id):
              send_text(sender_id, "Removing your existing product \"{product_name}\"...".format(product_name=product.display_name))
              Product.query.filter(Product.storefront_id == storefront.id).delete()
            
            db.session.commit()
            send_admin_carousel(sender_id)
            
            
          elif payload == Const.PB_PAYLOAD_SHARE_STOREFRONT:
            send_tracker("button-share", sender_id, "")
            send_share_card(sender_id)
            send_admin_carousel(sender_id)
            
            
          elif payload == Const.PB_PAYLOAD_SUPPORT:
            send_tracker("button-support", sender_id, "")
            send_text(sender_id, "Support for Prebot:\nprebot.me/support")
          
          else:
            send_tracker("unknown-button", sender_id, "")
            send_text(sender_id, "Button not recognized!")
            
          return "OK", 200
        
        
        #-- actual message
        if messaging_event.get('message'):
          logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECIEVED ->{message}".format(message=messaging_event['sender']))
          
          message = messaging_event['message']
          message_id = message['mid']
          message_text = ""
                      
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
                  send_storefront_preview(sender_id)
                  
              #------- VIDEO MESSAGE
              elif attachment['type'] == "video":
                logger.info("VIDEO: %s" % (attachment['payload']['url']))
                query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 1)
                
                if query.count() > 0:  
                  file_path = os.path.dirname(os.path.realpath(__file__))
                  timestamp = int(time.time())
                  
                  with open("{file_path}/videos/{timestamp}.mp4".format(file_path=file_path, timestamp=timestamp), 'wb') as handle:
                    response = requests.get(attachment['payload']['url'], stream=True)
                    
                    if not response.ok:
                      logger.info("DOWNLOAD FAILED!!! %s" % (response.text))

                    for block in response.iter_content(1024):
                      handle.write(block)
                  
                  
                  container = av.open("{file_path}/videos/{timestamp}.mp4".format(file_path=file_path, timestamp=timestamp))
                  video = next(s for s in container.streams if s.type == b'video')
                  for packet in container.demux(video):
                    for frame in packet.decode():
                      if frame.index == 20:
                        frame.to_image().save("/var/www/html/thumbs/{timestamp}.jpg".format(file_path=file_path, timestamp=timestamp))
                        break
                  
                  os.remove("{file_path}/videos/{timestamp}.mp4".format(file_path=file_path, timestamp=timestamp))
                  product = query.first()
                  product.creation_state = 2
                  product.image_url = "http://{ip_addr}/thumbs/{timestamp}.jpg".format(ip_addr=Const.WEB_SERVER_IP, timestamp=timestamp)
                  product.video_url = attachment['payload']['url']
                  db.session.commit()
                                    
                  send_text(
                    recipient_id = sender_id, 
                    message_text = "Select when your product will be available:", 
                    quick_replies = [
                      build_quick_reply(Const.KWIK_BTN_TEXT, "Right Now", Const.PB_PAYLOAD_PRODUCT_RELEASE_NOW),
                      build_quick_reply(Const.KWIK_BTN_TEXT, "Next Month", Const.PB_PAYLOAD_PRODUCT_RELEASE_30_DAYS),
                      build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + timedelta(days=60)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_60_DAYS),
                      build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + timedelta(days=90)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_90_DAYS),
                      build_quick_reply(Const.KWIK_BTN_TEXT, (datetime.now() + timedelta(days=120)).strftime('%B %Y'), Const.PB_PAYLOAD_PRODUCT_RELEASE_120_DAYS)
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
                  
                  send_text(sender_id, "Submitting your \"{storefront_name}\" shop...".format(storefront_name=storefront.display_name))
                  send_admin_carousel(sender_id)
                  
              elif quick_reply == Const.PB_PAYLOAD_UNDO_STOREFRONT:
                send_tracker("button-undo-store", sender_id, "")
                
                storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 3)
                if storefront_query.count() > 0:
                  send_text(sender_id, "Undoing your \"{storefront_name}\" shop...".format(storefront_name=storefront.display_name))
                  Storefront.query.filter(Storefront.owner_id == sender_id).delete()
                  db.session.commit()

                send_admin_carousel(sender_id)
                
              elif re.search('PRODUCT_RELEASE_(\d+)_DAYS', quick_reply) is not None:
                match = re.match(r'PRODUCT_RELEASE_(\d+)_DAYS', quick_reply)
                send_tracker("button-product-release-{days}-days-store".format(days=match.group(1)), sender_id, "")
                
                product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 2)
                if product_query.count() > 0:
                  product = product_query.first()
                  product.release_date = datetime.utcnow() + timedelta(days=int(match.group(1)))
                  product.creation_state = 3
                  db.session.commit()
                  
                  send_text(sender_id, "Here's what your product will look like:")
                  send_product_preview(sender_id, product.id)
                  
              elif quick_reply == Const.PB_PAYLOAD_SUBMIT_PRODUCT:
                send_tracker("button-submit-product", sender_id, "")

                product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 3)
                if product_query.count() > 0:
                  product = product_query.first()
                  product.creation_state = 4
                  product.added = datetime.utcnow()
                  db.session.commit()

                  send_text(sender_id, "Share \"{product_name}\" with others".format(product_name=product.display_name))
                  send_share_card(sender_id)

                send_admin_carousel(sender_id)
                  
              elif quick_reply == Const.PB_PAYLOAD_UNDO_PRODUCT:
                send_tracker("button-undo-product", sender_id, "")
                
                product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id)
                if product_query.count() > 0:
                  product = product_query.first()
                  send_text(sender_id, "Undoing your \"{product_name}\" product...".format(product_name=product.display_name))
                  
                  Product.query.filter(Product.storefront_id == storefront_query.first().id).delete()
                  db.session.commit()

                send_admin_carousel(sender_id)
                
              
                
            #-- text entry
            else:
              message_text = ""
              if 'text' in message:
                message_text = message['text']  # the message's text
                
                if message_text.lower() == "admin":
                  send_admin_carousel(sender_id)
                  return "OK", 200
                  
                if storefront_query.count() > 0:
                  
                  #-- look for in-progress product creation
                  product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4)
                  if product_query.count() > 0:
                    product = product_query.first()

                    #-- name submitted
                    if product.creation_state == 0:
                      product.creation_state = 1
                      product.display_name = message_text
                      product.name = message_text.replace(" ", "_")
                      product.prebot_url = "http://prebot.me/{slug}".format(slug=storefront_query.first().prebot_url)
                      db.session.commit()

                      send_text(sender_id, "Upload a video for \"{product_name}\"...".format(product_name=product.name))

                    return "OK", 200
                    
                  else:
                    welcome_message(sender_id, Const.CUSTOMER_STOREFRONT, message_text)

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
                      storefront.prebot_url = "http://prebot.me/{slug}".format(slug=escape(message_text.replace(" ", "_")))
                      db.session.commit()

                      send_text(sender_id, "Enter your \"{storefront_name}\" store's description...".format(storefront_name=storefront.display_name))

                    #-- description entered
                    elif storefront.creation_state == 1:
                      storefront.creation_state = 2
                      storefront.description = message_text
                      db.session.commit()

                      send_text(sender_id, "Submit an image for your \"{storefront_name}\" store's avatar / logo...".format(storefront_name=storefront.display_name))
                  
                    else:
                      welcome_message(sender_id, Const.CUSTOMER_STOREFRONT, message_text)
                      
                  else:
                    welcome_message(sender_id, Const.CUSTOMER_STOREFRONT, message_text)
                          
        else:
          send_text(sender_id, "I'm sorry, I cannot understand that type of message.")
          
          #-- insert to log
          # write_message_log(sender_id, message_id, quote(message_text.encode('utf-8')))

  return "OK", 200



#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#
#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#



@app.route('/', methods=['GET'])
def verify():
  logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
  logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= GET -- VERIFY ({hub_mode})->{request}\n".format(hub_mode=request.args.get('hub.mode'), request=request))
  logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

  if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
    if not request.args.get('hub.verify_token') == Const.VERIFY_TOKEN:
      return "Verification token mismatch", 403
    return request.args['hub.challenge'], 200

  return "OK", 200

#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#
#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#



def send_text(recipient_id, message_text, quick_replies=None):
  #logger.info("send_text(recipient_id={recipient}, message_text={text}, quick_replies={quick_replies})".format(recipient=recipient_id, text=message_text, quick_replies=quick_replies))
  data = {
    "recipient": {
      "id": recipient_id
    },
    "message": {
      "text": message_text
    }
  }
  
  if quick_replies is not None:
    data['message']['quick_replies'] = quick_replies
  
  send_message(json.dumps(data))
  

def send_image(recipient_id, url, quick_replies=None):
  data = {
    "recipient": {
      "id": recipient_id
    },
    "message": {
      "attachment": {
        "type": "image",
        "payload": {
          "url": url
        }
      }
    }
  }
  
  if quick_replies is not None:
    data['message']['quick_replies'] = quick_replies
  
  send_message(json.dumps(data))
  
  
def send_video(recipient_id, url, quick_replies=None):
  data = {
    "recipient": {
      "id": recipient_id
    },
    "message": {
      "attachment": {
        "type": "video",
        "payload": {
          "url": url
        }
      }
    }
  }
  
  if quick_replies is not None:
    data['message']['quick_replies'] = quick_replies
    
  send_message(json.dumps(data))


def send_message(payload):
  logger.info("\nsend_message(payload={payload})".format(payload=payload))  
  
  
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
    print("SEND MESSAGE Error: -({errno})- {errstr}".format(errno=errno, errstr=errstr))
  
  finally:
    buf.close()
    
    
  return True


if __name__ == '__main__':
  logger.info("Firin up FbBot using verify token [{verify_token}] w/ page access:\n{oauth_token}")
  app.run(debug=True)
