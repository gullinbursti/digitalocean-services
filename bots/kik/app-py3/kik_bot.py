#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import threading
import time
import csv
import locale
import hashlib
import json
import random
import sqlite3
import re

import requests
import pymysql.cursors

import tornado.escape
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.web

import modd
import const as Const

from datetime import date, datetime
from io import BytesIO
from PIL import Image

from kik.error import KikError
from kik import KikApi, Configuration
from kik.messages import messages_from_json, StartChattingMessage, TextMessage, FriendPickerMessage, LinkMessage, PictureMessage, StickerMessage, ScanDataMessage, VideoMessage, DeliveryReceiptMessage, ReadReceiptMessage, UnknownMessage, SuggestedResponseKeyboard, TextResponse, FriendPickerResponse, CustomAttribution

Const.SLACK_TOKEN = 'IJApzbM3rVCXJhmkSzPlsaS9'
Const.NOTIFY_TOKEN = '1b9700e13ea17deb5a487adac8930ad2'
Const.PAYPAL_TOKEN = '9343328d1ea69bf36158868bcdd6f5c7'
Const.STRIPE_TOKEN = 'b221ac2f599be9d53e738669badefe76'
Const.PRODUCT_TOKEN = '326d665bbc91c22b4f4c18a64e577183'
Const.BROADCAST_TOKEN = 'f7d3612391b5ba4d89d861bea6283726'

Const.DB_HOST = '138.197.216.56'
Const.DB_NAME = 'pre'
Const.DB_USER = 'pre_usr'
Const.DB_PASS = 'f4zeHUga.age'

Const.MAX_REPLIES = 40
Const.INACTIVITY_THRESHOLD = 8000

Const.DEFAULT_AVATAR = "http://i.imgur.com/ddyXamr.png";


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#

class Application(tornado.web.Application):
  def __init__(self):
    handlers = [
      (r"/", HomeHandler),
      #(r"/entry/([^/]+)", EntryHandler),
      (r"/([a-zA-Z_-.0-9]+)[^/]+", ShopHandler),
      (r"/(\d+)[^/]+", ProductHandler),
    ]
    
    settings = dict(
      blog_title=u"Tornado Blog",
      template_path=os.path.join(os.path.dirname(__file__), "templates"),
      static_path=os.path.join(os.path.dirname(__file__), "static"),
      ui_modules={"Entry": EntryModule},
      xsrf_cookies=True,
      cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
      login_url="/auth/login",
      debug=True,
    )

    super(Application, self).__init__(handlers, **settings)
    





class HomeHandler(BaseHandler):
    def get(self):
        entries = self.db.query("SELECT * FROM entries ORDER BY published "
                                "DESC LIMIT 5")
        if not entries:
            self.redirect("/compose")
            return
        self.render("home.html", entries=entries)





#--:-- Message UI / Message Part Factories --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def init_keyboard(chat_id):
  buttons = [
    TextResponse("Create Shop")
  ]
  
  if chat_id in companies:
    buttons.append(TextResponse("Add Product"))
  
  buttons.append(TextResponse("Dashboard"))
  buttons.append(TextResponse("Invite Friends"))
  
  if chat_id in companies and 'bots' in companies[chat_id] and len(companies[chat_id]['bots']) > 0:
    buttons.append(TextResponse("Share Bot"))
  
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = False,
      responses = buttons
    )
  ]
  
  return keyboard
  

def default_keyboard():
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = False,
      responses = [
        TextResponse("Yes"),
        TextResponse("No"),
        TextResponse("Cancel")
      ]
    )
  ]

  return keyboard


def friend_picker_keyboard(min=1, max=5, message="Pick some friends!"):
  keyboard = [
    SuggestedResponseKeyboard(
      responses = [
        FriendPickerResponse(
          body = message,
          min = min,
          max = max
        ),
        TextResponse("No Thanks")
      ]
    )
  ]

  return keyboard


def custom_attribution(name="gamebots.chat"):
  attribution = CustomAttribution(
    name = name, 
    icon_url = "http://gamebots.chat/img/icon/favicon-96x96.png"
  )

  return attribution

def intro_text_reply(message):
  print("intro_text_reply(message=%s)" % (message))
  
  try:
    kik.send_messages([
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "Welcome to Pre!",
        type_time = 250,
        keyboards = init_keyboard(message.chat_id)
      )
    ])
  except KikError as err:
    print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
    

def default_text_reply(message):
  print("default_text_reply(message=%s)" % (message))
  
  try:
    kik.send_messages([
      VideoMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        video_url = "http://i.imgur.com/IngIFI2.gif",
        autoplay = True,
        loop = True,
        muted = True,
        keyboards = default_keyboard(),
        attribution = custom_attribution(" ")
      )
    ])
  except KikError as err:
    print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))


def message_for_state(message, state):
  print("message_for_state(message=%s, state=%d)" % (message, state))
  
  if state == 1:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Enter your bot's name",
          type_time = 250
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
        
  elif state == 2:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Are you sure you want {bot_name}?".format(bot_name=convo_replies[message.chat_id]['bot_name']),
          type_time = 250,
          keyboards = default_keyboard()
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
  
  elif state == 3:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Enter your bot's description",
          type_time = 250
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
  
  elif state == 4:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Are you sure you want {bot_description}?".format(bot_description=convo_replies[message.chat_id]['bot_description']),
          type_time = 250,
          keyboards = default_keyboard()
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
  elif state == 5:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Upload your bot's profile image.",
          type_time = 250
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
    
  elif state == 6:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Enter your product's name",
          type_time = 250
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
  elif state == 7:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Are you sure you want {product_name}?".format(product_name=convo_replies[message.chat_id]['product_name']),
          type_time = 250,
          keyboards = default_keyboard()
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
  elif state == 8:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Enter your product's description",
          type_time = 250
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
  
  elif state == 9:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Are you sure you want {product_description}?".format(product_description=convo_replies[message.chat_id]['product_description']),
          type_time = 250,
          keyboards = default_keyboard()
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
  elif state == 10:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Enter your product's price",
          type_time = 250
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
  elif state == 11:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Are you sure your product at ${product_price:.2f}?".format(product_price=convo_replies[message.chat_id]['product_price']),
          type_time = 250,
          keyboards = default_keyboard()
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
  elif state == 12:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Enter your product's release date (MM-DD-YYYY)",
          type_time = 250
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
  elif state == 13:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Are you sure you want your product released on {product_release}?".format(product_release=convo_replies[message.chat_id]['product_release']),
          type_time = 250,
          keyboards = default_keyboard()
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
  elif state == 14:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Upload product photo.",
          type_time = 250
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
  elif state == 15:
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "How many of this product are available for give-a-ways?",
          type_time = 250
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
      
  # try:
  #   kik.send_messages([
  #     TextMessage(
  #       to = message.from_user,
  #       chat_id = message.chat_id,
  #       body = body,
  #       type_time = 250,
  #       keyboards = default_keyboard()
  #     )
  #   ])
  # except KikError as err:
  #   print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
    
  
#--:-- Model / Data Retrieval --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

      

#--:-- Session Subpaths / In-Session Seqs --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def intro_session(message):
  print("intro_session(message=%s)" % (message))
  convo_states[message.chat_id] = 0
  intro_text_reply(message)
    
  
  
def submit_bot(message):
  print("submit_bot(message=%s)" % (message))
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur.execute("INSERT IGNORE INTO `bots` (`id`, `company_id`, `platform_id`, `name`, `info`, `logo_url`, `added`) VALUES (NULL, %s, 1, %s, %s, %s, NOW())", (companies[message.chat_id]['company_id'], convo_replies[message.chat_id]['bot_name'], convo_replies[message.chat_id]['bot_description'], message.pic_url))
      conn.commit()
      
      if 'bots' in companies[message.chat_id]:
        companies[message.chat_id]['bots'].append({
          'bot_id' : cur.lastrowid,
          'bot_name' : convo_replies[message.chat_id]['bot_name']
        })
        
      else:
        companies[message.chat_id]['bots'] = [{
          'bot_id' : cur.lastrowid,
          'bot_name' : convo_replies[message.chat_id]['bot_name']
        }]
        
      cur.close()
    
  except pymysql.Error as err:
      print("MySQL DB error:%s" % (err))
        
  finally:
    if conn:
      conn.close()
      
  
  payload = {
    'channel'     : "#pre", 
    'username'    : "pre", 
    'icon_url'    : "http://icons.iconarchive.com/icons/chrisbanks2/cold-fusion-hd/128/kik-Messenger-icon.png",
    'text'        : "*{from_user}* submitted bot _{bot_name}_".format(from_user=message.from_user, bot_name=convo_replies[message.chat_id]['bot_name']),
  }
  response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })
  
  convo_states[message.chat_id] = 5.1
  try:
    kik.send_messages([
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "Ok great! Your bot has been submitted for review.\n\nShow this bot shop's URL?",
        type_time = 250,
        keyboards = [
          SuggestedResponseKeyboard(
            hidden = False,
            responses = [
              TextResponse("Yes"),
              TextResponse("No")
            ]
          )
        ]
      )
    ])
  except KikError as err:
    print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
    
  
def submit_product(message):
  print("submit_product(message=%s)" % (message))
  
  release = datetime.strptime(convo_replies[message.chat_id]['product_release'], '%m-%d-%Y')
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur.execute("INSERT IGNORE INTO `products` (`id`, `bot_id`, `name`, `info`, `image_url`, `price`, `release_date`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, NOW())", (companies[message.chat_id]['bots'][0]['bot_id'], convo_replies[message.chat_id]['product_name'], convo_replies[message.chat_id]['product_description'], message.pic_url, convo_replies[message.chat_id]['product_price'], release.strftime('%Y-%m-%d 00:00:00')))
      conn.commit()
      
      if 'products' in companies[message.chat_id]:
        companies[message.chat_id]['products'].append({
          'product_id' : cur.lastrowid,
          'bot_id'     : companies[message.chat_id]['bots'][0]['bot_id']
        })
        
      else:
        companies[message.chat_id]['products'] = [{
          'product_id' : cur.lastrowid,
          'bot_id'     : companies[message.chat_id]['bots'][0]['bot_id']
        }]
        
      cur.close()
    
  except pymysql.Error as err:
      print("MySQL DB error:%s" % (err))
        
  finally:
    if conn:
      conn.close()
      
      
  try:
    kik.send_messages([
      PictureMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        pic_url = message.pic_url,
        attribution = custom_attribution("Tap above to reserve")
      ),
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "Here is what your product message will look like. Want to add another?",
        type_time = 333,
        keyboards = default_keyboard()
      )
    ])
  except KikError as err:
    print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))

# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class KikBot(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
  
  def post(self):
    print("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    
    #-- missing header
    if not kik.verify_signature(self.request.headers.get('X-Kik-Signature'), self.request.body):
      print("self.request.headers.get('X-Kik-Signature')=%s" % (self.request.headers.get('X-Kik-Signature')))
      print("403 Forbidden")
      self.set_status(403)
      return
    
    
    #-- parse
    data_json = tornado.escape.json_decode(self.request.body)
    messages = messages_from_json(data_json["messages"])
    print(":::::::: MESSAGES :::::::::\n%s" % (data_json["messages"]))
    
    #-- each message
    for message in messages:
      
      if message.chat_id not in user_lookups:
        conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
        try:
          with conn.cursor() as cur:
            cur.execute("SELECT `id` FROM `companies` WHERE `name` = %s LIMIT 1;", (message.from_user))

            if cur.rowcount == 1:
              row = cur.fetchone()      
              print("row[]={row}".format(row=row))
              companies[message.chat_id] = {
                'company_id' : row['id']
              }
              
              cur.execute("SELECT `id`, `name` FROM `bots` WHERE `platform_id` = 1 AND `company_id` = %s;", (row['id']))
              for row in cur:
                if 'bots' in companies[message.chat_id]:
                  companies[message.chat_id]['bots'].append({
                    'bot_id'   : row['id'],
                    'bot_name' : row['name']
                  })

                else:
                  companies[message.chat_id]['bots'] = [{
                    'bot_id'   : row['id'],
                    'bot_name' : row['name']
                  }]
              

        except pymysql.Error as err:
          print("MySQL DB error:%s" % (err))

        finally:
          if conn:
            conn.close()
        
        user_lookups[message.chat_id] = True
      
      
      
      # -=-=-=-=-=-=-=-=- UNSUPPORTED TYPE -=-=-=-=-=-=-=-=-
      if isinstance(message, LinkMessage) or isinstance(message, VideoMessage) or isinstance(message, ScanDataMessage) or isinstance(message, StickerMessage) or isinstance(message, UnknownMessage):
        print("=-= IGNORING MESSAGE =-=\n%s " % (message))
        default_text_reply(message=message)
        
        self.set_status(200)
        return
        
        
      # -=-=-=-=-=-=-=-=- DELIVERY RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, DeliveryReceiptMessage):
        print("-= DeliveryReceiptMessage =-= ")
        self.set_status(200)
        return
        

      # -=-=-=-=-=-=-=-=- READ RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, ReadReceiptMessage):
        print("-= ReadReceiptMessage =-= ")
        self.set_status(200)
        return
         
      
      # -=-=-=-=-=-=-=-=- START CHATTING -=-=-=-=-=-=-=-=-
      elif isinstance(message, StartChattingMessage):
        print("-= StartChattingMessage =-= ")
        
        conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
        try:
          with conn.cursor() as cur:
            cur.execute("INSERT IGNORE INTO `users` (`id`, `platform_id`, `bot_id`, `username`, `chat_id`, `added`) VALUES (NULL, 1, 1, %s, %s, NOW())", (message.from_user, message.chat_id))
            conn.commit()
            cur.close()

        except pymysql.Error as err:
            print("MySQL DB error:%s" % (err))

        finally:
          if conn:
            conn.close()
            
        # conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
        # try:
        #   with conn.cursor() as cur:
        #     cur.execute("INSERT IGNORE INTO `kikbot_logs` (`id`, `username`, `chat_id`, `body`, `added`) VALUES (NULL, %s, %s, %s, NOW())", (message.from_user, message.chat_id, "__{START-CHATTING}__"))
        #     conn.commit()
        #     cur.close()
        #   
        # except pymysql.Error as err:
        #     print("MySQL DB error:%s" % (err))
        #       
        # finally:
        #   if conn:
        #     conn.close()
        
        
        intro_session(message)
        
        self.set_status(200)
        return
        
      
      # -=-=-=-=-=-=-=-=- FRIEND PICKER MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, FriendPickerMessage):
        conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
        try:
          with conn.cursor() as cur:
            cur = conn.cursor()
            
            for username in message.picked:
              cur.execute("INSERT IGNORE INTO `invited_users` (`id`, `username`, `source_user`, `added`) VALUES (NULL, %s, %s, NOW())", (username, message.from_user))
              conn.commit()
            cur.close()
            
        except pymysql.Error as err:
            print("MySQL DB error:%s" % (err))
                
        finally:
          if conn:
            conn.close()
          
      
      # -=-=-=-=-=-=-=-=- PHOTO MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, PictureMessage):
        print("=-= PictureMessage =-= ")
        
        if message.chat_id in convo_states:
          if convo_states[message.chat_id] == 5:
            submit_bot(message)
            
            # convo_states[message.chat_id] = 6
            # message_for_state(message, convo_states[message.chat_id])
            
          elif convo_states[message.chat_id] == 14:
            convo_states[message.chat_id] = 15
            message_for_state(message, convo_states[message.chat_id])
              
              
        self.set_status(200)
        return
      
      # -=-=-=-=-=-=-=-=- TEXT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, TextMessage):
        print("=-= TextMessage =-= ")
        
        # -=-=-=-=-=-=-=-=-=- MENTIONS -=-=-=-=-=-=-=-=-
        if message.mention is None:
          pass
          # conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
          # try:
          #   with conn.cursor() as cur:
          #     cur = conn.cursor()
          #     cur.execute("INSERT IGNORE INTO `kikbot_logs` (`username`, `chat_id`, `body`) VALUES (%s, %s, %s)", (message.from_user, message.chat_id, message.body))
          #     conn.commit()
          #     cur.close()
          #   
          # except pymysql.Error as err:
          #     print("MySQL DB error:%s" % (err))
          #         
          # finally:
          #   if conn:
          #     conn.close()
                  
        
        # -=-=-=-=-=-=-=-=-=- END SESSION -=-=-=-=-=-=-=-
        if message.body.lower() == "cancel" or message.body.lower() == "quit":
          print("-=- ENDING SESSION -=-")
          
          try:
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Thanks for using Pre!",
                type_time = 250,
                keyboards = init_keyboard(message.chat_id)
              )
            ])
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
            
        
        # -=-=-=-=-=-=-=-=- INVITE FRIENDS BTN -=-=-=-=-=-=-=-=-    
        elif message.body.lower() == "invite friends":
          try:
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Invite 5 friends now",
                type_time = 150,
                keyboards = friend_picker_keyboard()
              )
            ])
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
          
        
        # -=-=-=-=-=-=-=-=- CREATE SHOP BTN -=-=-=-=-=-=-=-=-    
        elif message.body.lower() == "create shop":
          
          conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
          try:
            with conn.cursor() as cur:
              cur.execute("SELECT `id` FROM `companies` WHERE `name` = %s LIMIT 1;", (message.from_user))

              if cur.rowcount == 0:
                cur.execute("INSERT IGNORE INTO `companies` (`id`, `name`, `added`) VALUES (NULL, %s, NOW())", (message.from_user))
                conn.commit()
                companies[message.chat_id] = {
                  'company_id' : cur.lastrowid
                }
                
              else:
                row = cur.fetchone()
                companies[message.chat_id] = {
                  'company_id' : row['id']
                }
                
                cur.close()

          except pymysql.Error as err:
              print("MySQL DB error:%s" % (err))

          finally:
            if conn:
              conn.close()
              
              
          convo_states[message.chat_id] = 1
          message_for_state(message, convo_states[message.chat_id])
          
          
        # -=-=-=-=-=-=-=-=- ADD PRODUCT BUTTON -=-=-=-=-=-=-=-=-
        elif message.body.lower() == "add product":
          convo_states[message.chat_id] = 6
          message_for_state(message, convo_states[message.chat_id])
        
        
        # -=-=-=-=-=-=-=-=- DASHBOARD BUTTON -=-=-=-=-=-=-=-=-
        elif message.body.lower() == "dashboard":
          try:
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Visit {dashboard_url} to manage your shop & products.".format(dashboard_url="http://prekey.co/dashboard/{from_user}".format(from_user=message.from_user)),
                type_time = 250,
                keyboards = init_keyboard(message.chat_id)
              )
            ])
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
          
        
        # -=-=-=-=-=-=-=-=- SHARE BUTTON -=-=-=-=-=-=-=-=-
        elif message.body.lower() == "share bot":
          buttons = []
          for bot in companies[message.chat_id]['bots']:
            buttons.append(TextResponse(bot['bot_name']))
          buttons.append(TextResponse("Cancel"))
          
          try:
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Choose your bot shop",
                type_time = 250,
                keyboards = [
                  SuggestedResponseKeyboard(
                    hidden = False,
                    responses = buttons
                  )
                ]
              )
            ])
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
        
        
        # -=-=-=-=-=-=-=-=- YES BUTTON -=-=-=-=-=-=-=-=-
        elif message.body.lower() == "yes":
          if convo_states[message.chat_id] == 5.1:
            try:
              kik.send_messages([
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = "http://prekey.co/{bot_name}".format(bot_name=convo_replies[message.chat_id]['bot_name'].replace(" ", "")),
                  type_time = 250
                ),
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = "Now let's add your first Pre-Sale product.",
                  type_time = 250
                )
              ])
            except KikError as err:
              print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
            convo_states[message.chat_id] = 6
            
          else:    
            convo_states[message.chat_id] += 1
          
          message_for_state(message, convo_states[message.chat_id])
              
        # -=-=-=-=-=-=-=-=- NO BUTTONS -=-=-=-=-=-=-=-=-
        elif message.body.lower() == "no":
          if message.chat_id in convo_states:
            #-- share bot
            if convo_states[message.chat_id] == 5.1:
              try:
                kik.send_messages([
                  TextMessage(
                    to = message.from_user,
                    chat_id = message.chat_id,
                    body = "Now let's add your first Pre-Sale product.",
                    type_time = 250
                  )
                ])
              except KikError as err:
                print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
                
              convo_states[message.chat_id] = 6
              message_for_state(message, convo_states[message.chat_id])
              
            #-- product image
            if convo_states[message.chat_id] == 15:
              intro_text_reply(message)
              
            else:
              message_for_state(message, convo_states[message.chat_id])
              
          else:
            message_for_state(message, convo_states[message.chat_id])
                    
        # -=-=-=-=-=-=-=-=- ALL ELSE -=-=-=-=-=-=-=-=
        else:
          #-- bot name reply
          if message.chat_id in companies:
            if 'bots' in companies[message.chat_id]:
              for bot in companies[message.chat_id]['bots']:
                if message.body == bot['bot_name']:
                  try:
                    kik.send_messages([
                      TextMessage(
                        to = message.from_user,
                        chat_id = message.chat_id,
                        body = "http://prekey.co/{bot_name}".format(bot_name=bot['bot_name'].replace(" ", "")),
                        type_time = 250
                      )
                    ])
                  except KikError as err:
                    print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
                                  
                  self.set_status(200)
                  return
          
          #-- text replies
          if message.chat_id in convo_states:
            #-- bot name
            if convo_states[message.chat_id] == 1:
              convo_states[message.chat_id] = 2
              convo_replies[message.chat_id] = {
                'bot_name' : message.body
              }
              message_for_state(message, convo_states[message.chat_id])
            
            #-- bot description
            elif convo_states[message.chat_id] == 3:
              convo_states[message.chat_id] = 4
              convo_replies[message.chat_id]['bot_description'] = message.body
              message_for_state(message, convo_states[message.chat_id])
              
            #-- product name
            elif convo_states[message.chat_id] == 6:
              convo_states[message.chat_id] = 7
              if message.chat_id in convo_replies:
                convo_replies[message.chat_id]['product_name'] = message.body
                
              else:
                convo_replies[message.chat_id] = {
                  'product_name' : message.body
                }
                
              message_for_state(message, convo_states[message.chat_id])
              
            #-- product description
            elif convo_states[message.chat_id] == 8:
              convo_states[message.chat_id] = 9
              convo_replies[message.chat_id]['product_description'] = message.body
              message_for_state(message, convo_states[message.chat_id])
              
            #-- product price
            elif convo_states[message.chat_id] == 10:
              try:
                price = round(float(message.body), 2)
                convo_states[message.chat_id] = 11
                convo_replies[message.chat_id]['product_price'] = price
                
              except ValueError:
                pass
              
              message_for_state(message, convo_states[message.chat_id])
              
            #-- product release
            elif convo_states[message.chat_id] == 12:
              try:
                datetime.strptime(message.body, '%m-%d-%Y')
                convo_states[message.chat_id] = 13
                convo_replies[message.chat_id]['product_release'] = message.body
                
              except ValueError:
                pass
              
              message_for_state(message, convo_states[message.chat_id])
              
            #-- give-a-way
            elif convo_states[message.chat_id] == 15:
              try:
                amt = round(int(message.body), 0)
                convo_states[message.chat_id] = 16
                convo_replies[message.chat_id]['product_givaway'] = amt
                
                submit_product(message)
                
              except ValueError:
                pass
              
              message_for_state(message, convo_states[message.chat_id])
              
              
          else:
            if message.chat_id in convo_states:
              message_for_state(message, convo_states[message.chat_id])
              
            else:
              convo_states[message.chat_id] = 0
              intro_text_reply(message)
        
        
      self.set_status(200)
      return  
        
      
    self.set_status(200)
    return
        


# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class Message(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
  def post(self):
    print("-=-=-=-=-=-=-=-=-=-= MESSAGE BROADCAST =-=-=-=-=-=-=-=-=-=-=")
    
    self.set_status(403)
    return
    
    


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#




convo_states = {}
convo_replies = {}
companies = {}
user_lookups = {}


# Const.KIK_API_CONFIG = { 
#   'USERNAME'  : "game.bots",
#   'API_KEY'   : "0fb46005-dd00-49c3-a4a5-239a0bdc1e79",
#   'WEBHOOK'   : {
#     'HOST'  : "http://159.203.250.4",
#     'PORT'  : 8080,
#     'PATH'  : "kik-bot"
#   },
# 
#   'FEATURES'  : {
#     'receiveDeliveryReceipts' : False,
#     'receiveReadReceipts'     : True
#   }
# }


Const.KIK_API_CONFIG = {
  'USERNAME'  : "prebot",
  'API_KEY'   : "f20ca71d-5b22-45f0-a317-b64891a4410f",
  'WEBHOOK'   : {
    'HOST'  : "http://98.248.214.183",
    'PORT'  : 8080,
    'PATH'  : "kik-bot"
  },
  
  'FEATURES'  : {
    'receiveDeliveryReceipts' : False,
    'receiveReadReceipts'     : False
  }
}




# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #
# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #




#-=:=- Start + Config Kik -=:=-#
#-=:=--=:=--=:=--=:=--=:=--=:=--=:=--=:=--=:=--=:=-#
locale.setlocale(locale.LC_ALL, 'en_US.utf8')

Const.KIK_CONFIGURATION = Configuration(
  webhook = "%s:%d/%s" % (Const.KIK_API_CONFIG['WEBHOOK']['HOST'], Const.KIK_API_CONFIG['WEBHOOK']['PORT'], Const.KIK_API_CONFIG['WEBHOOK']['PATH']),
  features = Const.KIK_API_CONFIG['FEATURES']
)

kik = KikApi(
  Const.KIK_API_CONFIG['USERNAME'],
  Const.KIK_API_CONFIG['API_KEY']
)

kik.set_configuration(Const.KIK_CONFIGURATION)


#-- output what the hell kik is doing
print("\n\n\n# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #")
print("# -= Firing up KikBot: =- #")
print("# -= =-=-=-=-=-=-=-=-= =- #")
print("USERNAME : %s\nAPI_KEY  : %s\nHOST     : %s\nPORT     : %d\nPATH     : %s\nCONFIG   : %s" % (
  Const.KIK_API_CONFIG['USERNAME'],
  Const.KIK_API_CONFIG['API_KEY'],
  Const.KIK_API_CONFIG['WEBHOOK']['HOST'],
  Const.KIK_API_CONFIG['WEBHOOK']['PORT'],
  Const.KIK_API_CONFIG['WEBHOOK']['PATH'],
  kik.get_configuration().to_json()))
print("# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #\n\n\n")



#-- url webhooks
application = tornado.web.Application([
  (r"/kik-bot", KikBot),
  (r"/message", Message)
])



#-- server init
def main():
  http_server = tornado.httpserver.HTTPServer(Application())
  http_server.listen(int(Const.KIK_API_CONFIG['WEBHOOK']['PORT']))
  tornado.ioloop.IOLoop.current().start()

#-- server starting    
if __name__ == "__main__":
  print("tornado start @ %d" % (int(time.time())))
  main()    

#-- server starting
# if __name__ == "__main__":
#   application.listen(int(Const.KIK_API_CONFIG['WEBHOOK']['PORT']))
#   tornado.ioloop.IOLoop.instance().start()
#   print("tornado start" % (int(time.time())))
