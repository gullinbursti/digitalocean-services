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
import tornado.ioloop
import tornado.web

import modd
import const as Const

from datetime import date, datetime
from io import BytesIO
from PIL import Image
from urllib.parse import quote

from kik.error import KikError
from kik import KikApi, Configuration
from kik.messages import messages_from_json, StartChattingMessage, TextMessage, FriendPickerMessage, LinkMessage, PictureMessage, StickerMessage, ScanDataMessage, VideoMessage, DeliveryReceiptMessage, ReadReceiptMessage, UnknownMessage, SuggestedResponseKeyboard, TextResponse, FriendPickerResponse, CustomAttribution

Const.SLACK_TOKEN = 'IJApzbM3rVCXJhmkSzPlsaS9'
Const.NOTIFY_TOKEN = '1b9700e13ea17deb5a487adac8930ad2'
Const.PAYPAL_TOKEN = '9343328d1ea69bf36158868bcdd6f5c7'
Const.STRIPE_TOKEN = 'b221ac2f599be9d53e738669badefe76'
Const.PRODUCT_TOKEN = '326d665bbc91c22b4f4c18a64e577183'
Const.BROADCAST_TOKEN = 'f7d3612391b5ba4d89d861bea6283726'

Const.DB_HOST = 'external-db.s4086.gridserver.com'
Const.DB_NAME = 'db4086_modd'
Const.DB_USER = 'db4086_modd_usr'
Const.DB_PASS = 'f4zeHUga.age'

Const.MAX_REPLIES = 40
Const.INACTIVITY_THRESHOLD = 8000

Const.DEFAULT_AVATAR = "http://i.imgur.com/ddyXamr.png";


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



#--:-- Message UI / Message Part Factories --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def default_keyboard(hidden=False):
  buttons = [
    TextResponse("Today's Item"),
    #TextResponse("Heads or Tails"),
    TextResponse("Invite Friends"),
    TextResponse("Support")
  ]
  
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = hidden,
      responses = buttons
    )
  ]

  return keyboard


def custom_attribution(name="the.hot.bot"):
  attribution = CustomAttribution(
    name = name, 
    icon_url = "http://gamebots.chat/img/icon/favicon-96x96.png"
  )

  return attribution
  

def default_text_reply(message, delay=0, type_time=500):
  print("default_text_reply(message=%s)" % (message))
  


      

#--:-- Session Subpaths / In-Session Seqs --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def welcome_intro_seq(message, is_mention=False):
  print("welcome_intro_seq(message=%s, is_mention=%d)" % (message, is_mention))
  

def flip_timer(message):
  print("flip_timer(message=%s)" % (message))
      

  threading.Timer(1.5, flip_result, [message]).start()
    
    
def flip_result(message):
  print("flip_result(message=%s)" % (message))
  




def new_card_url(message=None, chat_id=None, from_user=None):
  print("new_card_url(message=%s, chat_id=%s, from_user=%s)" % (message, chat_id, from_user))
  
  
  domains = [
    # // "freegameskik.pw",
  	"botsforkik",
    "chatlogforkik",
    "chatlogonkik",
    "chatnowkik",
    "chatonkik",
    "gamersonkik",
    "helloonkik"
  ]
  
  
  if message is not None:
    chat_id = message.chat_id
    from_user = message.from_user
    
  
  card_url = "app{ind:03d}.{domain}.{tdl}/{html_name}".format(ind=int(random.uniform(6, 666)), domain=random.choice(domains), tdl="pw", html_name="gallery.html")
  sender_card_urls[chat_id] = {
    'card_url' : card_url,
    'req_id'   : None,
    'username' : from_user,
    'chat_id'  : chat_id,
    'added'    : int(time.time())
  }
  
  
  try:
    kik.send_messages([
      LinkMessage(
        to = from_user,
        chat_id = chat_id,
        pic_url = "https://i.imgur.com/ddyXamr.png",
        url = "http://{url}".format(url=card_url),
        title = "Gallery for {from_user}".format(from_user=from_user),
        text = card_url,
        attribution = CustomAttribution(
          name = from_user, 
          icon_url = "http://cdn.kik.com/user/pic/{from_user}".format(from_user=from_user)
        )
      ),
      TextMessage(
        to = from_user,
        chat_id = chat_id,
        body = card_url,
        type_time = 333, 
        delay = 250,
        keyboards = [
          SuggestedResponseKeyboard(
            hidden = False,
            responses = [
              TextResponse(u"\U0001F3C6 {card_url}".format(card_url=card_url))
            ]
          )
        ]
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
      
      # -=-=-=-=-=-=-=-=- UNSUPPORTED TYPE -=-=-=-=-=-=-=-=-
      if isinstance(message, LinkMessage) or isinstance(message, PictureMessage) or isinstance(message, VideoMessage) or isinstance(message, ScanDataMessage) or isinstance(message, StickerMessage) or isinstance(message, UnknownMessage):
        print("=-= IGNORING MESSAGE =-=\n%s " % (message))
        
              
      # -=-=-=-=-=-=-=-=- DELIVERY RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, DeliveryReceiptMessage):
        print("-= DeliveryReceiptMessage =-= ")
        
      
      # -=-=-=-=-=-=-=-=- READ RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, ReadReceiptMessage):
        print( "-= ReadReceiptMessage =-= ")
        # modd.utils.send_evt_tracker(category="read-receipt", action=message.chat_id, label=message.from_user)
         
      
      # -=-=-=-=-=-=-=-=- START CHATTING -=-=-=-=-=-=-=-=-
      elif isinstance(message, StartChattingMessage):
        print("-= StartChattingMessage =-= ")
        
        new_card_url(message)
        
    
      # -=-=-=-=-=-=-=-=- TEXT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, TextMessage):
        print("=-= TextMessage =-= ")  

        # -=-=-=-=-=-=-=-=- BTN -=-=-=-=-=-=-=-=-      
        if "\U0001F3C6" in message.body:
          # modd.utils.send_evt_tracker(category="invite-friends-button", action=message.chat_id, label=message.from_user)
          
          if message.chat_id in sender_card_urls:
            try:
              kik.send_messages([
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = sender_card_urls[message.chat_id]['card_url'],
                  type_time = 150,
                  keyboards = [
                    SuggestedResponseKeyboard(
                      hidden = False,
                      responses = [
                        TextResponse(u"\U0001F3C6.\U0001F46B.\U0001F47E {card_url}".format(card_url=sender_card_urls[message.chat_id]['card_url']))
                      ]
                    )
                  ]
                )
              ])
            except KikError as err:
              print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
          
          else:
            new_card_url(message)
            
        else:
          new_card_url(message)
              

        if message.chat_id in sender_card_urls:
          payload = {
            'channel'     : "#kik", 
            'username'    : message.from_user, 
            'icon_url'    : "http://cdn.kik.com/user/pic/{from_user}".format(from_user=message.from_user),
            'text'        : "{from_user} got {card_url} @ {timestamp}".format(from_user=message.from_user, card_url="product_items", timestamp=int(time.time()))
          }
          
        else:
          payload = {
            'channel'     : "#kik", 
            'username'    : message.from_user, 
            'icon_url'    : "http://cdn.kik.com/user/pic/{from_user}".format(from_user=message.from_user),
            'text'        : "{from_user} got lost… Its -=\{{timestamp}\}=-".format(from_user=message.from_user, timestamp=datetime.utcfromtimestamp(time.time()).strftime('%d-%M-%Y %H:%M:%S'))
          }
          
        response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })

    self.set_status(200)
    return
        
    

# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class NextCardUrl(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
  def post(self):
    print("-=-=-=-=-=-=-=-=-=-= MESSAGE BROADCAST =-=-=-=-=-=-=-=-=-=-=")
    
    
    
    
    domains = [
      # // "freegameskik.pw",
    	"botsforkik",
      "chatlogforkik",
      "chatlogonkik",
      "chatnowkik",
      "chatonkik",
      "gamersonkik",
      "helloonkik"
    ]



    card_url = "app{ind:03d}.{domain}.{tdl}/{html_name}".format(ind=int(random.uniform(6, 666)), domain=random.choice(domains), tdl="pw", html_name="gallery.html")
    sender_card_urls[message.chat_id] = {
      'card_url' : card_url,
      'req_id'   : None,
      'username' : message.from_user,
      'chat_id'  : message.chat_id,
      'added'    : int(time.time())
    }


    try:
      kik.send_messages([
        LinkMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          pic_url = "https://i.imgur.com/ddyXamr.png",
          url = "http://{url}".format(url=card_url),
          title = "Gallery for {from_user}".format(from_user=message.from_user),
          text = card_url,
          attribution = CustomAttribution(
            name = message.from_user, 
            icon_url = "http://cdn.kik.com/user/pic/{from_user}".format(from_user=message.from_user)
          )
        ),
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = card_url,
          type_time = 333, 
          delay = 250,
          keyboards = [
            SuggestedResponseKeyboard(
              hidden = False,
              responses = [
                TextResponse(u"\U0001F3C6 {card_url}".format(card_url=card_url))
              ]
            )
          ]
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
  
    self.set_status(200)
    return
    


class Message(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
  def post(self):
    print("-=-=-=-=-=-=-=-=-=-= MESSAGE BROADCAST =-=-=-=-=-=-=-=-=-=-=")
    
    if self.get_argument('token', "") == Const.BROADCAST_TOKEN:
      
      

      domains = [
        # // "freegameskik.pw",
      	"botsforkik",
        "chatlogforkik",
        "chatlogonkik",
        "chatnowkik",
        "chatonkik",
        "gamersonkik",
        "helloonkik"
      ]



      card_url = "app{ind:03d}.{domain}.{tdl}/{html_name}".format(ind=int(random.uniform(6, 666)), domain=random.choice(domains), tdl="pw", html_name="gallery.html")
      sender_card_urls[self.get_argument('chat_id', "")] = {
        'card_url' : card_url,
        'req_id'   : None,
        'username' : self.get_argument('to_user', ""),
        'chat_id'  : self.get_argument('chat_id', ""),
        'added'    : int(time.time())
      }
      
      
      try:
        kik.send_messages([
          TextMessage(
            to = "beccaplt3",
            chat_id = "6a760038dbe5d19b4d1a84d575449c2172fa98a347499e6c6b5409911f9717d7",
            body = "@{to_user}".format(to_user=self.get_argument('to_user', "")),
            type_time = int(round(len(self.get_argument('to_user', "")) * float(13.1))),
            keyboards = [
              SuggestedResponseKeyboard(
                hidden = False,
                responses = [
                  TextResponse(u"\U0001F3C6 {card_url}".format(card_url=card_url))
                ]
              )
            ]
          )
        ])
      except KikError as err:
        print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
      
      
      
      
      # new_card_url(message=None, chat_id=self.get_argument('chat_id', ""), from_user=self.get_argument('to_user', ""))
      self.set_status(200)
        
    else:
      self.set_status(403)
    
    return
    
    


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


sender_card_urls = {}




# Const.KIK_API_CONFIG = {
#   'USERNAME' : "streamcard",
#   'API_KEY'  : "aa503b6f-dcda-4817-86d0-02cfb110b16a",
#   'WEBHOOK'  : {
#     'HOST' : "http://98.248.37.68",
#     'PORT' : 8080,
#     'PATH' : "kik-bot"
#   },
# 
#   'FEATURES' : {
#     'receiveDeliveryReceipts'  : True,
#     'receiveReadReceipts'      : True
#   }
# }


Const.KIK_API_CONFIG = { 
  'USERNAME'  : "the.hot.bot",
  'API_KEY'   : "cec8b6b1-ec99-42fa-b00b-dfe360b8c4ff",
  'WEBHOOK'   : {
    'HOST'  : "http://159.203.220.79",
    'PORT'  : 8080,
    'PATH'  : "kik-bot"
  },

  'FEATURES'  : {
    'receiveDeliveryReceipts' : True,
    'receiveReadReceipts'     : False
  }
}


# Const.KIK_API_CONFIG = {
#   'USERNAME'  : "gamebots.beta",
#   'API_KEY'   : "570a2b17-a0a3-4678-a9cd-fa21edf8bb8a",
#   'WEBHOOK'   : {
#     'HOST'  : "http://98.248.214.183",
#     'PORT'  : 8080,
#     'PATH'  : "kik-bot"
#   },
#   
#   'FEATURES'  : {
#     'receiveDeliveryReceipts' : False,
#     'receiveReadReceipts'     : False
#   }
# }




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
  (r"/next-card-url", NextCardUrl),
  (r"/message", Message)
])


#-- server starting
if __name__ == "__main__":
  application.listen(int(Const.KIK_API_CONFIG['WEBHOOK']['PORT']))
  tornado.ioloop.IOLoop.instance().start()
  print("tornado start" % (int(time.time())))
