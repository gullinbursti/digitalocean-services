#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import csv
import hashlib
import json
import locale
import os
import random
import re
import sqlite3
import threading
import time

import pymysql.cursors
import requests
import tornado.escape
import tornado.httpclient
import tornado.ioloop
import tornado.web

import modd
import const as Const

from datetime import datetime
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
Const.ALWAYS_WIN_PATTERN = '^Xersss'


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



#--:-- Message UI / Message Part Factories --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def default_keyboard(hidden=False):
  buttons = [
    TextResponse("Today's Game"),
    TextResponse("Play Flip Coin"),
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


def next_item_keyboard(hidden=False):
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = hidden,
      responses = [
        TextResponse("Flip Coin"),
        TextResponse("Next Item"),
        TextResponse("No Thanks")
      ]
    )
  ]

  return keyboard


def friend_picker_keyboard(min=1, max=5, message="Invite 5 friends"):

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


def flip_coin_keyboard(hidden=False):
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = hidden,
      responses = [
        TextResponse("Invite Friends"),
        TextResponse("Steam Trade URL"),
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
  

def default_text_reply(message, delay=0, type_time=500):
  print("default_text_reply(message=%s)" % (message))
  
  response = requests.post("http://beta.modd.live/api/kikbot_total.php", data={'type' : "users"})
  
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
      ),
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "Welcome to Gamebots. WIN pre-sale games & items with {total} players on Kik & Facebook Messenger.".format(total=locale.format("%d", int(response.text), grouping=True)),
        keyboards = default_keyboard(),
        type_time = type_time,
        delay = delay
      )
    ])
  except KikError as err:
    print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))


def default_content_reply(message, topic, level):
  print("default_content_reply(message={message}, topic={topic}, level={level})".format(message=message, topic=topic, level=level))
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur.execute("SELECT `id`, `youtube_id`, `video_title`, `image_url`, `video_url`, `topic_name` FROM `topic_content` WHERE `topic_name` = %s AND `level` = %s ORDER BY RAND() LIMIT 1;", (topic_name, level))

      if cur.rowcount == 0:
        cur.execute("SELECT `id`, `youtube_id`, `video_title`, `image_url`, `video_url`, `topic_name` FROM `topic_content` ORDER BY RAND() LIMIT 1;")
      
      row = cur.fetchone()
      
      print("row[]={row}".format(row=row))
      try:
        kik.send_messages([
          LinkMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            pic_url = row['image_url'],
            url = "http://gamebots.chat/bot.html?t=v&u={from_user}&y={youtube_id}&g={topic_name}&l={level}".format(from_user=message.from_user, youtube_id=row['youtube_id'], topic_name=topic, level=level),
            title = "{topic_name} - {level}".format(topic_name=row['topic_name'], level=level),
            text = "Keep tapping Watch Now for more coins.",
            delay = delay,
            attribution = custom_attribution("WATCH NOW"),
            keyboards = default_keyboard()
          )
        ])
      except KikError as err:
        print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
        
  except pymysql.Error as err:
    print("MySQL DB error:%s" % (err))

  finally:
    if conn:
      conn.close()
      
  return _message
  

def daily_product_message(message):
  print("daily_product_message(message={message})".format(message=message))
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur.execute("SELECT `id`, `name`, `info`, `image_url`, `video_url`, `price`, `added` FROM `fb_products` WHERE `enabled` = 1 ORDER BY RAND() LIMIT 1;")

      if cur.rowcount == 0:
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "No items for today! Come back tomorrow for another.",
            keyboards = default_keyboard()
          )
        ])
        
      else:
        row = cur.fetchone()      
        print("row[]={row}".format(row=row))
        
        td = datetime.now() - row['added']
        m, s = divmod(td.seconds, 60)
        h, m = divmod(m, 60)
        
        product_items[message.chat_id] = {
          'item_id': row['id'],
          'username': message.from_user,
          'chat_id' : message.chat_id
        }
        
        if len(row['video_url']) > 0:
          pic_url = row['video_url']
        
        else:
          pic_url = row['image_url']
          
        try:
          kik.send_messages([
            LinkMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              pic_url = pic_url,
              url = "http://prekey.co/stripe/{item_id}/{from_user}".format(item_id=row['id'], from_user=message.from_user),
              #url = "http://prekey.co/stripe.php?from_user={from_user}&item_id={item_id}".format(from_user=message.from_user, item_id=row['id']),
              title = "",
              text = "", 
              attribution = custom_attribution("Tap to Win"),
              keyboards = default_keyboard()
            )
          ])
          
          
          # if len(row['video_url']) > 0 or ".gif" in row['image_url']:
          #     kik.send_messages([
          #       VideoMessage(
          #         to = message.from_user,
          #         chat_id = message.chat_id,
          #         video_url = pic_url,
          #         autoplay = True,
          #         loop = True,
          #         muted = True,
          #         attribution = custom_attribution(row['name'])
          #       ),
          #       TextMessage(
          #         to = message.from_user,
          #         chat_id = message.chat_id,
          #         body = "Tap here for {item_name}:\nhttp://prekey.co/stripe/{item_id}/{from_user}".format(item_name=row['name'], item_id=row['id'], from_user=message.from_user),
          #         #body = "Tap here for {item_name}:\nhttp://prekey.co/stripe.php?from_user={from_user}&item_id={item_id}".format(item_name=row['name'], from_user=message.from_user, item_id=row['id']),
          #         type_time = 250,
          #         keyboards = default_keyboard()
          #       )
          #     ])
          #    
          # else:  
          #   kik.send_messages([
          #     LinkMessage(
          #       to = message.from_user,
          #       chat_id = message.chat_id,
          #       pic_url = pic_url,
          #       url = "http://prekey.co/stripe/{item_id}/{from_user}".format(item_id=row['id'], from_user=message.from_user),
          #       #url = "http://prekey.co/stripe.php?from_user={from_user}&item_id={item_id}".format(from_user=message.from_user, item_id=row['id']),
          #       title = "",
          #       text = "", 
          #       attribution = custom_attribution("Tap to Win"),
          #       keyboards = default_keyboard()
          #     )
          #   ])
          
        except KikError as err:
          print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
        
  except pymysql.Error as err:
    print("MySQL DB error:%s" % (err))

  finally:
    if conn:
      conn.close()
  
  
def flip_item_message(message):
  print("flip_item_message(message=%s)" % (message))
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur.execute("SELECT `id`, `name`, `game_name`, `image_url`, `trade_url` FROM `flip_inventory` WHERE `quantity` > 0 AND `type` = 1 ORDER BY RAND() LIMIT 1;")
      row = cur.fetchone()

      if row is not None:
        print("row[]={row}".format(row=row))
        item_flips[message.chat_id] = row
        
        if random.random() <= 0.45 or re.search(Const.ALWAYS_WIN_PATTERN, message.from_user, re.IGNORECASE) is not None:
          item_flips[message.chat_id]['flip'] = True
          
        else:
          item_flips[message.chat_id]['flip'] = False
        
        try:
          kik.send_messages([
            LinkMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              pic_url = row['image_url'],
              url = row['image_url'],
              title = "",
              text = "",
              keyboards = next_item_keyboard(),
              attribution = CustomAttribution(
                name = row['name'],
                icon_url = "http://store.steampowered.com/favicon.ico"
              )
            )
          ])
        except KikError as err:
          print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))

      else:
        try:
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "All items have been rewarded today! Come back tomorrow for more to win.",
              keyboards = default_keyboard()
            )
          ])

        except KikError as err:
          print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
    
  except pymysql.Error as err:
    print("MySQL DB error:%s" % (err))

  finally:
    if conn:
      conn.close()
  
      
  
#--:-- Model / Data Retrieval --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def send_player_help_message(message, topic_name, level="Intro"):
  print("send_player_help_message(message={message}, topic_name={topic_name}, level={level})".format(message=message, topic_name=topic_name, level=level))
  player_help_for_topic_level(message.from_user, message.chat_id, topic_name, level, 1, True)
      
      
def player_help_for_topic_level(username="", chat_id="", topic_name="", level="", amt=5, to_self=False):
  print("player_help_for_topic_level(username={username}, chat_id={chat_id}, topic_name={topic_name}, level={level}, amt={amt}, to_self={to_self})".format(username=username, chat_id=chat_id, topic_name=topic_name, level=level, amt=amt, to_self=to_self))
  
  if topic_name == "":
    topic_name = ""
  
  conn2 = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor, autocommit=True);
  try:
    with conn2.cursor() as cur2:
      cur2.execute("SELECT `game_art` FROM `top_games` WHERE `game_name` = %s;", (topic_name))
      if cur2.rowcount == 1:
        row = cur2.fetchone()
        image_url = row['game_art']
          
      else:
        image_url = "http://i.imgur.com/NBcs0Ix.png"
        
      
      img = Image.open(BytesIO(requests.get(image_url).content))
      tot = 0
      for i in img.getdata():
        if i == (99, 64, 164) or i == (100, 65, 165):
          tot += 1
          
      if tot >= 30000:
        image_url = "http://i.imgur.com/NBcs0Ix.png"
        
         
      cur2.execute("SELECT `chat_id`, `username` FROM `kikbot_sessions` WHERE `topic_name` = %s AND `chat_id` != %s AND `username` != %s GROUP BY `chat_id` ORDER BY RAND() LIMIT %s;", (topic_name, chat_id, username, amt))
      #cur2.execute("SELECT `chat_id`, `username` FROM `kikbot_logs` WHERE `chat_id` != %s AND `username` != %s AND `body` != '__{MENTION}__' GROUP BY `chat_id` ORDER BY RAND() LIMIT %s;", (chat_id, username, amt))
          
      if cur2.rowcount < amt:
        #cur2.execute("SELECT `chat_id`, `username` FROM `kikbot_logs` WHERE `chat_id` != %s AND `username` != %s AND `body` != '__{MENTION}__' GROUP BY `chat_id` ORDER BY RAND() LIMIT %s;", (chat_id, username, amt))
        cur2.execute("SELECT `chat_id`, `username` FROM `kikbot_logs` WHERE `chat_id` != %s AND `username` != %s AND `body` != '__{MENTION}__' AND `targeted` < DATE_SUB(NOW(), INTERVAL 12 HOUR) GROUP BY `chat_id` ORDER BY RAND() LIMIT %s;", (chat_id, username, amt))
      
      
      if username == "alxar0":
        cur2.execute("SELECT `chat_id`, `username` FROM `kikbot_logs` WHERE `id` = 57006 LIMIT 1;")  
      
      target_id = 0
      chat_ids = []
      csv_file = "/opt/kik_bot/queue/users/{timestamp}.csv".format(timestamp=int(time.time() * 100))
      for row in cur2:
        if to_self:
          avatar = "http://cdn.kik.com/user/pic/{username}".format(username=row['username'])
          print("row[]={row}, avatar={avatar}".format(row=row, avatar=avatar))
          
          try:
            kik.send_messages([
              LinkMessage(
                to = username,
                chat_id = chat_id,
                pic_url = image_url,
                url = "http://gamebots.chat/bot.html?t=p&u={from_user}&r={to_user}".format(from_user=username, to_user=row['username']),
                title = "Chat & Trade request sent.",
                text = "",
                attribution = CustomAttribution(
                  name = row['username'],
                  icon_url = avatar
                ),
                keyboards = default_keyboard()
              ),
              LinkMessage(
                to = row['username'],
                chat_id = row['chat_id'],
                pic_url = image_url,
                url = "http://gamebots.chat/bot.html?t=p&u={from_user}&r={to_user}".format(from_user=username, to_user=row['username']),
                title = "",#{from_user} wants to chat about {game_name}. Want to chat now?".format(from_user=username, game_name=topic_name),
                text = "",
                attribution = CustomAttribution(
                  name = "{from_user}".format(from_user=username), 
                  icon_url = "http://cdn.kik.com/user/pic/{from_user}".format(from_user=username)
                ),
                keyboards = [
                  SuggestedResponseKeyboard(
                    hidden = False,
                    responses = [
                      TextResponse("Chat with {from_user}".format(from_user=username)),
                      TextResponse("Trade Items"),
                      TextResponse("No Thanks")
                    ]
                  )
                ]
              )
            ])
            
            conn = sqlite3.connect("{script_path}/data/sqlite3/kikbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            cur = conn.cursor()

            try:            
              cur.execute("INSERT INTO targeting (id, username, username_id, type, participant, participant_id, game_name, game_image, pending, respond, in_session, last_response, added) VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", (username, chat_id, 1, row['username'], row['chat_id'], topic_name, image_url, 1, 0, 0, "0000-00-00 00:00:00"))
              conn.commit()
              target_id = cur.lastrowid

            except sqlite3.Error as err:
              print("::::::[cur.execute] sqlite3.Error - {message}".format(message=err.message))

            finally:
              conn.close()
              
              
            modd.utils.send_evt_tracker(category="player-message", action=chat_id, label=username)
            
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
          
        else:
          conn = sqlite3.connect("{script_path}/data/sqlite3/kikbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
          cur = conn.cursor()

          try:            
            cur.execute("INSERT INTO targeting (id, username, username_id, type, participant, participant_id, game_name, game_image, pending, respond, in_session, last_response, added) VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", (username, chat_id, 1, row['username'], row['chat_id'], topic_name, image_url, 1, 0, 0, "0000-00-00 00:00:00"))
            conn.commit()
            target_id = cur.lastrowid

          except sqlite3.Error as err:
            print("::::::[cur.execute] sqlite3.Error - {message}".format(message=err.message))

          finally:
            conn.close()

          chat_ids.append("OR `chat_id` = '{chat_id}'".format(chat_id=row['chat_id']))
          
          avatar = "http://cdn.kik.com/user/pic/{username}".format(username=username)
          # print("QUEUE --- row[]={row}, avatar={avatar}".format(row=row, avatar=avatar))
          
          with open(csv_file, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([target_id, username, chat_id, row['username'], row['chat_id'], topic_name, image_url])
          
      # if len(chat_ids) > 0:
      #   cur2.execute("UPDATE `kikbot_logs` SET `targeted` = NOW() WHERE `chat_id` = '0' {chat_ids};".format(chat_ids=" ".join(chat_ids)))
                  
  except pymysql.Error as err:
    print("MySQL DB error:%s" % (err))

  finally:
    if conn2:
      conn2.close()
      
      

#--:-- Session Subpaths / In-Session Seqs --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def welcome_intro_seq(message, is_mention=False):
  print("welcome_intro_seq(message=%s, is_mention=%d)" % (message, is_mention))
  modd.utils.send_evt_tracker(category="start-chatting", action=message.chat_id, label=message.from_user)
  
  topic_names = [
    #"Pokémon Go",
    "Hearthstone",
    "CS:GO",
    "Dota 2",
    "League of Legends"
  ]
  
  response = requests.post("http://beta.modd.live/api/kikbot_total.php", data={'type' : "users"})
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur.execute("SELECT `id`, `name`, `info`, `image_url`, `video_url`, `price`, `added` FROM `fb_products` WHERE `enabled` = 1 ORDER BY RAND() LIMIT 1;")

      if cur.rowcount == 0:
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "No items for today! Come back tomorrow for another.",
            keyboards = default_keyboard()
          )
        ])
        
      else:
        row = cur.fetchone()      
        print("row[]={row}".format(row=row))
        
        td = datetime.now() - row['added']
        m, s = divmod(td.seconds, 60)
        h, m = divmod(m, 60)
        
        try:
          if len(row['video_url']) > 0:
            kik.send_messages([
              VideoMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                video_url = row['video_url'],
                autoplay = True,
                loop = True,
                muted = True,
                attribution = custom_attribution(" ")
              )
            ])

          kik.send_messages([
            # TextMessage(
            #   to = message.from_user,
            #   chat_id = message.chat_id,
            #   body = "{item_name} just went live.".format(item_name=row['name'])
            # ),            
            # LinkMessage(
            #   to = message.from_user,
            #   chat_id = message.chat_id,
            #   pic_url = row['image_url'],
            #   url = "http://prekey.co/stripe/{item_id}/{from_user}".format(item_id=row['id'], from_user=message.from_user),
            #   title = "",
            #   text = "", 
            #   attribution = custom_attribution("Buy Now")
            # ),
            # TextMessage(
            #   to = message.from_user,
            #   chat_id = message.chat_id,
            #   body = "{item_name} went on sale {hours}h {minutes}m {seconds}s ago.".format(item_name=row['name'], hours=h, minutes=m, seconds=s)
            # ),
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Welcome to Gamebots. WIN pre-sale games & items with {total} players on Kik & Facebook Messenger.".format(total=locale.format("%d", int(response.text), grouping=True)),
              type_time = 500,
              keyboards = default_keyboard()
            )
          ])
        except KikError as err:
          print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
        
  except pymysql.Error as err:
    print("MySQL DB error:%s" % (err))

  finally:
    if conn:
      conn.close()
  
  return


def flip_timer(message):
  print("flip_timer(message=%s)" % (message))
      
  if item_flips[message.chat_id]['flip'] is True:
    if message.chat_id in button_taps:
      button_taps[message.chat_id] += 1
      
    else:
      button_taps[message.chat_id] = 1
      
    try:
      kik.send_messages([
        VideoMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          video_url = "http://i.imgur.com/9fmZntz.gif",
          autoplay = True,
          loop = True,
          muted = True,
          attribution = custom_attribution(" ")
        )
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
    
  else:
    try:
      kik.send_messages([
        VideoMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          video_url = "http://i.imgur.com/7YNujdq.gif",
          autoplay = True,
          loop = True,
          muted = True,
          attribution = custom_attribution(" ")
        )
      ])
    
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
  threading.Timer(1.5, flip_result, [message]).start()
    
    
def flip_result(message):
  print("flip_result(message=%s)" % (message))
  
  if item_flips[message.chat_id]['flip'] is True or message.from_user == "hugh.janus00":
    modd.utils.send_evt_tracker(category="flip-coin-win", action=message.chat_id, label=message.from_user)

    pin_code = hashlib.md5(str(time.time()).encode()).hexdigest()[-4:].upper()

    payload = {
      'channel'     : "#bot-alerts", 
      'username'    : "game.bots", 
      'icon_url'    : "http://icons.iconarchive.com/icons/chrisbanks2/cold-fusion-hd/128/kik-Messenger-icon.png",
      'text'        : "Flip Win by {from_user}:\n{item_name}\n{pin_code}".format(from_user=message.from_user, item_name=item_flips[message.chat_id]['name'], pin_code=pin_code),
      'attachments' : [{
        'image_url' : item_flips[message.chat_id]['image_url']
      }]
    }
    response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })
    
    conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
    try:
      with conn.cursor() as cur:
        cur = conn.cursor()
        cur.execute("INSERT INTO `item_winners` (`kik_name`, `pin`, `item_id`, `item_name`, `added`) VALUES (%s, %s, %s, %s, NOW())", (message.from_user, pin_code, item_flips[message.chat_id]['id'], item_flips[message.chat_id]['name']))
        item_flips[message.chat_id]['claim_id'] = cur.lastrowid
        conn.commit()
        cur.execute("UPDATE `flip_inventory` SET `quantity` = `quantity` - 1 WHERE `id` = {item_id} LIMIT 1;".format(item_id=item_flips[message.chat_id]['id']))
        conn.commit()
        cur.close()
        
        try:
          kik.send_messages([
            LinkMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              pic_url = item_flips[message.chat_id]['image_url'],
              url = "http://prebot.me/claim/{claim_id}/{from_user}".format(claim_id=item_flips[message.chat_id]['claim_id'], from_user=message.from_user),
              title = "",
              text = "", 
              attribution = custom_attribution("CLAIM ITEM NOW")
            ),  
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "WINNER! You won {item_name} from {game_name}.\n\nInstructions:\nInvite 3 friends to m.me/gamebotsc & kik.me/game.bots\nSign into Steam: {claim_url}\nFollow all instructions to get items.".format(item_name=item_flips[message.chat_id]['name'], game_name=item_flips[message.chat_id]['game_name'], claim_url="http://prebot.me/claim/{claim_id}/{from_user}".format(claim_id=item_flips[message.chat_id]['claim_id'], from_user=message.from_user)),
              type_time = 250,
              keyboards = flip_coin_keyboard()

            )
          ])
        except KikError as err:
          print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
          

    except pymysql.Error as err:
        print("MySQL DB error:%s" % (err))

    finally:
      if conn:
        conn.close()
    
  else:
    modd.utils.send_evt_tracker(category="flip-coin-lost", action=message.chat_id, label=message.from_user)
    try:
      kik.send_messages([
        PictureMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          pic_url = item_flips[message.chat_id]['image_url'],
          attribution = CustomAttribution(
            name = item_flips[message.chat_id]['name'],
            icon_url = "http://store.steampowered.com/favicon.ico"
          ),
          keyboards = [
            SuggestedResponseKeyboard(
              hidden = False,
              responses = [
                TextResponse("Next Item"),
                TextResponse("No Thanks")
              ]
            )
          ]
        ),
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "TRY AGAIN! You lost {item_name} from {game_name}.\n\nIncrease your chances by getting Gamebots on Messenger.\nm.me/gamebotsc".format(item_name=item_flips[message.chat_id]['name'], game_name=item_flips[message.chat_id]['game_name']),
          type_time = 500,
          delay = 500,
          keyboards = [
            SuggestedResponseKeyboard(
              hidden = False,
              responses = [
                TextResponse("Next Item"),
                TextResponse("No Thanks")
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
        default_text_reply(message=message)
        
        self.set_status(200)
        return
        
        
      
      # -=-=-=-=-=-=-=-=- DELIVERY RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, DeliveryReceiptMessage):
        # print "-= DeliveryReceiptMessage =-= "

        try:
          conn = sqlite3.connect("{script_path}/data/sqlite3/kikbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
          cur = conn.cursor()
          cur.execute("SELECT id FROM mentions WHERE participant = \'{participant}\' AND enabled = 1 ORDER BY added DESC LIMIT 1".format(participant=message.from_user))

          row = cur.fetchone()
          if row is not None:
            try:
              cur.execute("UPDATE mentions SET enabled = 0 WHERE id = {id} LIMIT 1".format(id=row[0]))
              conn.commit()

            except sqlite3.Error as err:
                print("::::::[cur.execute] sqlite3.Error - {message}".format(message=err.message))
            
            conn2 = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
            try:
              with conn2.cursor() as cur2:
                cur2 = conn2.cursor()

                cur2.execute("INSERT INTO `kikbot_logs` (`username`, `chat_id`, `body`) VALUES (%s, %s, %s)", (message.from_user, message.chat_id, "__{MENTION}__"))
                conn2.commit()
                cur2.close()

            except pymysql.Error as err:
                print("MySQL DB error:%s" % (err))

            finally:
              if conn2:
                conn2.close()            

          conn.close()

        except sqlite3.Error as err:
          print("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=err.message))

        finally:
          pass

        
        self.set_status(200)
        return
          
      
      # -=-=-=-=-=-=-=-=- READ RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, ReadReceiptMessage):
        # print "-= ReadReceiptMessage =-= "
        modd.utils.send_evt_tracker(category="read-receipt", action=message.chat_id, label=message.from_user)
        self.set_status(200)
        return
         
      
      # -=-=-=-=-=-=-=-=- FRIEND PICKER MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, FriendPickerMessage):
        conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
        try:
          with conn.cursor() as cur:
            cur = conn.cursor()
            cur.execute("INSERT INTO `kikbot_logs` (`username`, `chat_id`, `body`) VALUES (%s, %s, %s)", (message.from_user, message.chat_id, "__[INVITE]__ {picked}".format(picked=",".join(message.picked))))
            conn.commit()
            cur.close()

        except pymysql.Error as err:
            print("MySQL DB error:%s" % (err))

        finally:
          if conn:
            conn.close()
                        
        try:
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Awesome! Keep inviting friends for more items.",
              type_time = 250, 
              keyboards = default_keyboard()
            )
          ])
        except KikError as err:
          print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
      
      # -=-=-=-=-=-=-=-=- START CHATTING -=-=-=-=-=-=-=-=-
      elif isinstance(message, StartChattingMessage):
        print("-= StartChattingMessage =-= ")
        
        try:
          conn = sqlite3.connect("{script_path}/data/sqlite3/kikbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
          cur = conn.cursor()
          cur.execute("SELECT id FROM mentions WHERE participant = \'{participant}\' AND enabled = 1 ORDER BY added DESC LIMIT 1".format(participant=message.from_user))

          row = cur.fetchone()
          if row is not None:
            try:
              cur.execute("UPDATE mentions SET enabled = 0 WHERE id = {id} LIMIT 1".format(id=row[0]))
              conn.commit()

            except sqlite3.Error as err:
                print("::::::[cur.execute] sqlite3.Error - {message}".format(message=err.message))
            
            conn2 = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
            try:
              with conn2.cursor() as cur2:
                cur2 = conn2.cursor()

                cur2.execute("INSERT INTO `kikbot_logs` (`username`, `chat_id`, `body`) VALUES (%s, %s, %s)", (message.from_user, message.chat_id, "__{MENTION}__"))
                conn2.commit()
                cur2.close()

            except pymysql.Error as err:
                print("MySQL DB error:%s" % (err))

            finally:
              if conn2:
                conn2.close()            

          conn.close()

        except sqlite3.Error as err:
          print("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=err.message))

        finally:
          pass
          
          
        conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
        try:
          with conn.cursor() as cur:
            cur.execute("INSERT IGNORE INTO `kikbot_logs` (`id`, `username`, `chat_id`, `body`, `added`) VALUES (NULL, %s, %s, %s, NOW())", (message.from_user, message.chat_id, "__{START-CHATTING}__"))
            conn.commit()
            cur.close()
          
        except pymysql.Error as err:
            print("MySQL DB error:%s" % (err))
      
        finally:
          if conn:
            conn.close()
        
        
        response = requests.get("http://beta.modd.live/api/bot_tracker.php?src=botlandia&category=kikbot&action=start-chat&label={username}&value=0&cid={cid}".format(username=message.from_user, cid=message.chat_id))
        response = requests.get("http://beta.modd.live/api/user_tracker.php?username={username}&chat_id={chat_id}".format(username=message.from_user, chat_id=message.chat_id))
        
        
        welcome_intro_seq(message)
        
        
        conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor, autocommit=True);
        try:
          with conn.cursor() as cur:
            cur.execute("SELECT `id`, `username`, `game_name`, `game_image` FROM `kikbot_targeting` WHERE `recipient` = %s AND `pending` = 1 LIMIT 1;", (message.from_user))
            
            if cur.rowcount == 1:
              row = cur.fetchone()
              
              try:
                kik.send_messages([
                  LinkMessage(
                    to = message.from_user,
                    chat_id = message.chat_id,
                    pic_url = row['game_image'],
                    url = "http://gamebots.chat/bot.html?t=p&u={from_user}&r={to_user}".format(from_user=row['recipient'], to_user=message.from_user),
                    title = "{game_name}".format(game_name=row['game_name']),
                    text = "Chat Now",
                    attribution = CustomAttribution(
                      name = row['username'], 
                      icon_url = "http://cdn.kik.com/user/pic/{username}".format(username=row['username'])
                    ),
                    keyboards = default_keyboard()
                  )
                ])
              except KikError as err:
                print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
              
              cur.execute("UPDATE `kikbot_targeting` SET `pending` = 0, `requested` = NOW() WHERE `id` = {target_id};".format(target_id=row['id']))
              

        except pymysql.Error as err:
          print("MySQL DB error:%s" % (err))

        finally:
          if conn:
            conn.close()
        
        
        self.set_status(200)
        return
        
      
      # -=-=-=-=-=-=-=-=- TEXT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, TextMessage):
        print("=-= TextMessage =-= ")
        
        # -=-=-=-=-=-=-=-=-=- MENTIONS -=-=-=-=-=-=-=-=-
        if message.mention is not None:
          if message.body == "Start Chatting":
            try:
              kik.send_messages([
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = "Want a FREE CS:GO SKIN?",
                  type_time = 575, 
                  delay = 2150,
                  keyboards = [
                    SuggestedResponseKeyboard(
                      hidden = False,
                      responses = [
                        TextResponse(u"\U0001F3C6 FREE CS:GO SKIN"),
                        TextResponse(u"\U0001F46B CHAT NOW"),
                        TextResponse(u"\U0001F47E GET GAME HELP")
                      ]
                    )
                  ]
                )
              ])
            except KikError as err:
              print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
            
            self.set_status(200)            
            return

          else:
            #-- start the idle timeout - phasers to kill!
            #idle_activity_timer_starts(message.chat_id, True)
            
            try:
              conn = sqlite3.connect("{script_path}/data/sqlite3/kikbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
              cur = conn.cursor()

              try:
                cur.execute("SELECT id FROM mentions WHERE from_user = \'{from_user}\' AND participant = \'{participant}\'".format(from_user=message.from_user, participant=message.participants[-1]))

                if len(cur.fetchall()) == 0:
                  cur.execute("INSERT INTO mentions (id, from_user, participant) VALUES (NULL, ?, ?)", (message.from_user, message.participants[-1]))
                  conn.commit()

              except sqlite3.Error as err:
                print("::::::[cur.execute] sqlite3.Error - {message}".format(message=err.message))


            except sqlite3.Error as err:
              print("::::::[cur.execute] sqlite3.Error - {message}".format(message=err.message))

            finally:
              conn.close()


            print ("%s\tMENTION:\nCHAT ID:%s\nFROM:%s\nPARTICIPANT:%s" % (int(time.time()), message.chat_id, message.from_user, message.participants[-1]))
            welcome_intro_seq(message, True)
            self.set_status(200)
            return
            
          
        else:
          modd.utils.send_evt_tracker(category="reply", action=message.chat_id, label=message.from_user)
          
          conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
          try:
            with conn.cursor() as cur:
              cur = conn.cursor()
              cur.execute("INSERT IGNORE INTO `kikbot_logs` (`username`, `chat_id`, `body`) VALUES (%s, %s, %s)", (message.from_user, message.chat_id, quote(message.body.encode('utf-8'))))
              conn.commit()
              cur.close()
            
          except pymysql.Error as err:
              print("MySQL DB error:%s" % (err))
        
          finally:
            if conn:
              conn.close()
        
          
          print("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
          print("-=- help_convos -=- %s" % (help_convos))
          print("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
          
        
        
        topic_names = []
        conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
        try:
          with conn.cursor() as cur:
            cur.execute("SELECT `game_name` FROM `top_games` WHERE `game_name` != \"Creative\" AND `game_name` != \"Gaming Talk Shows\" AND `game_name` != \"Music\" ORDER BY `viewer_total` DESC LIMIT 18;")

            for row in cur:
              topic_names.append(row['game_name'])


        except pymysql.Error as err:
          print("MySQL DB error:%s" % (err))

        finally:
          if conn:
            conn.close()
            
        
        
        # -=-=-=-=-=-=-=-=-=- END SESSION -=-=-=-=-=-=-=-
        if message.body.lower() == "!end" or message.body.lower() == "cancel" or message.body.lower() == "quit":
          print("-=- ENDING HELP -=-")
          
          if message.chat_id in game_convos:
            response = requests.post("http://beta.modd.live/api/kikbot_total.php", data={'type' : "users"})
            convo = game_convos[message.chat_id]
            try:
              kik.send_messages([
                TextMessage(
                  to = convo['recipient'],
                  chat_id = convo['recipient_id'],
                  body = "Thanks for using Gamebots. Play Flip Coin with {total} gamers on Kik.".format(total=locale.format("%d", int(response.text), grouping=True)),
                  type_time = 250,
                  keyboards = default_keyboard()
                ),
                TextMessage(
                  to = convo['username'],
                  chat_id = convo['username_id'],
                  body = "Thanks for using Gamebots. Play Flip Coin with {total} gamers on Kik.".format(total=locale.format("%d", int(response.text), grouping=True)),
                  type_time = 250,
                  keyboards = default_keyboard()
                )
              ])
            except KikError as err:
              print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
              
            try:
              conn = sqlite3.connect("{script_path}/data/sqlite3/kikbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
              cur = conn.cursor()
              cur.execute("UPDATE targeting SET pending = 0, in_session = 0 WHERE username_id = \'{chat_id}\' OR participant_id = \'{participant_id}\';".format(chat_id=message.chat_id, participant_id=message.chat_id))
              conn.commit()
                

            except sqlite3.Error as err:
              print("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=err.message))

            finally:
              conn.close()
            
            del game_convos[message.chat_id]
          
          else:
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Thanks for using GameBots!",
                type_time = 250,
                keyboards = default_keyboard()
              )
            ])
          
          self.set_status(200)
          return
        
        
        # -=-=-=-=-=-=-=-=- NO THANKS BUTTONS -=-=-=-=-=-=-=-=-
        if message.body == "No Thanks":
          modd.utils.send_evt_tracker(category="no-thanks-button", action=message.chat_id, label=message.from_user)
          default_text_reply(message=message)
          
          self.set_status(200)
          return
            

        # -=-=-=-=-=-=-=-=- DEFAULT TOPIC BTNS -=-=-=-=-=-=-=-=-
        #if message.body.rsplit(" ", 1)[0] in topic_names:
        if message.body in topic_names:
          topic_name = message.body
          modd.utils.send_evt_tracker(category="{game_name}-button".format(game_name=topic_name), action=message.chat_id, label=message.from_user)
          modd.utils.send_evt_tracker(category="{game_name}-selection".format(game_name=topic_name), action=message.chat_id, label=message.from_user)
          
          send_player_help_message(message=message, topic_name=topic_name, level="Level 1")
          
          if message.from_user not in gameHelpList:
            gameHelpList[message.from_user] = topic_name
              
          
          help_convos[message.chat_id] = {
            'chat_id'       : message.chat_id,
            'username'      : message.from_user,
            'game'          : gameHelpList[message.from_user],
            'level'         : "Level 1",
            'ignore_streak' : 0,
            'started'       : int(time.time()),
            'last_message'  : int(time.time()),
            'idle_timer'    : None,
            'messages'      : [],
            'replies'       : [],
            'im_channel'    : "",
            'session_id'    : 0
          }
          
          player_help_for_topic_level(username=message.from_user, chat_id=message.chat_id, topic_name=help_convos[message.chat_id]['game'], level=help_convos[message.chat_id]['level'])          
          conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
          try:
            with conn.cursor() as cur:
              cur = conn.cursor()

              cur.execute("INSERT INTO `kikbot_sessions` (`username`, `topic_name`, `level`, `chat_id`, `added`) VALUES (%s, %s, %s, %s, UTC_TIMESTAMP())", (message.from_user, topic_name, "Level 1", message.chat_id))
              conn.commit()
              help_convos[message.chat_id]['session_id'] = cur.lastrowid
              cur.close()

          except pymysql.Error as err:
              print("MySQL DB error:%s" % (err))

          finally:
            if conn:
              conn.close()
          
          del gameHelpList[message.from_user]
          #modd.utils.slack_send(help_convos[message.chat_id], topic_name, message.from_user)
          
          self.set_status(200)
          return
          
          
          
        # -=-=-=-=-=-=-=-=-=- PRESALE -=-=-=-=-=-=-=-
        if message.body == "Today's Game":
          modd.utils.send_evt_tracker(category="todays-pre-sale-button", action=message.chat_id, label=message.from_user)
          daily_product_message(message)
          
          self.set_status(200)
          return
        
        
        # -=-=-=-=-=-=-=-=- INVITE FRIENDS BTN -=-=-=-=-=-=-=-=-      
        if message.body == "Invite Friends":
          modd.utils.send_evt_tracker(category="invite-button", action=message.chat_id, label=message.from_user)
          
          try:
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Invite 5 friends now for a FREE CS:GO item, then send a screenshot of the invite to @support.gamebots.1",
                type_time = 150,
                keyboards = friend_picker_keyboard()
              )
            ])            
            
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
          
          self.set_status(200)
          return
          
        
        # -=-=-=-=-=-=-=-=-=- Steam Trade URL -=-=-=-=-=-=-=-
        if message.body == "Steam Trade URL":
          modd.utils.send_evt_tracker(category="steam-button", action=message.chat_id, label=message.from_user)
          
          title = " "
          pic_url = "https://i.imgur.com/CctmFz0.png"
          url = item_flips[message.chat_id]['image_url']
          if message.chat_id in item_flips:
            title = item_flips[message.chat_id]['name']
            url = "http://prebot.me/claim/{claim_id}/{from_user}".format(claim_id=item_flips[message.chat_id]['claim_id'], from_user=message.from_user)
            # pic_url = item_flips[message.chat_id]['image_url']
            # url = item_flips[message.chat_id]['trade_url']
          
          try:
            kik.send_messages([
              LinkMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                pic_url = pic_url,
                url = url,
                title = title,
                text = "",
                attribution = CustomAttribution(
                  name = "CLAIM ITEM",
                  icon_url = "https://steamcommunity.com/favicon.ico"
                ),
                keyboards = default_keyboard()
              )
            ])

            self.set_status(200)
            return
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
            
          self.set_status(200)
          return
          
        # -=-=-=-=-=-=-=-=-=- SUPPORT -=-=-=-=-=-=-=-
        if message.body == "Support":
          modd.utils.send_evt_tracker(category="support-button", action=message.chat_id, label=message.from_user)
          
          try:
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Need help? chat with @support.gamebots.1",
                type_time = 500,
                keyboards = default_keyboard()
              )
            ])
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
          
          
          payload = {
            'channel'     : "#pre", 
            'username'    : "game.bots", 
            'icon_url'    : "http://icons.iconarchive.com/icons/chrisbanks2/cold-fusion-hd/128/kik-Messenger-icon.png",
            'text'        : "*{from_user}* needs help…".format(from_user=message.from_user),
          }
          response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })
          

          self.set_status(200)
          return
        
        # -=-=-=-=-=-=-=-=-=- NEXT PLAYER -=-=-=-=-=-=-=-
        if message.body == "Next Player":

          if message.chat_id in help_convos:
            send_player_help_message(message=message, topic_name=help_convos[message.chat_id]['game'], level="Level 1")
            player_help_for_topic_level(username=message.from_user, chat_id=message.chat_id, topic_name=help_convos[message.chat_id]['game'], level="Level 1")

          else:
            send_player_help_message(message=message, topic_name=random.choice(topic_names), level="Level 1")
            player_help_for_topic_level(username=message.from_user, chat_id=message.chat_id, topic_name=random.choice(topic_names), level="Level 1")
          
          modd.utils.send_evt_tracker(category="next-player-button", action=message.chat_id, label=message.from_user)
          
          if message.chat_id in button_taps:
            button_taps[message.chat_id] += 1
            
          else:
            button_taps[message.chat_id] = 1
            
          # if button_taps[message.chat_id] % 3 == 0:
          #   modd.utils.send_evt_tracker(category="paypal-button", action=message.chat_id, label=message.from_user)
          #   paypal_requests[message.from_user] = message.chat_id
          # 
          #   try:
          #     kik.send_messages([
          #       LinkMessage(
          #         to = message.from_user,
          #         chat_id = message.chat_id,
          #         pic_url = "https://i.imgur.com/GrlEhwP.png",
          #         url = "http://gamebots.chat/paypal.html?u={from_user}".format(from_user=message.from_user),
          #         title = "",
          #         text = "Trade unlimited items with millions of gamers for $1.99 a week.",
          #         keyboards = default_keyboard(),
          #         attribution = CustomAttribution(
          #           name = "PayPal",
          #           icon_url = "http://gamebots.chat/img/icon/favicon-96x96.png"
          #         ),
          #       )
          #     ])
          #   except KikError as err:
          #     print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
              
          self.set_status(200)
          return        
        
        
        # -=-=-=-=-=-=-=-=-=- NEXT ITEM BUTTON -=-=-=-=-=-=-=-
        if message.body == "Play Flip Coin" or message.body == "Next Item":
          modd.utils.send_evt_tracker(category="play-flip-coin-button", action=message.chat_id, label=message.from_user)
          
          payload = {
            'action'    : "paid",
            'username'  : message.from_user
          }
          response = requests.post("http://beta.modd.live/api/paypal.php", data=payload)
          print("PAID: %s" % (response.json()))
          
          if message.chat_id not in button_taps:
            button_taps[message.chat_id] = 1
            
          if button_taps[message.chat_id] <= 3000000000 or response.json()['result'] == True:
            flip_item_message(message)
          
          else:
            modd.utils.send_evt_tracker(category="paypal-button", action=message.chat_id, label=message.from_user)
            paypal_requests[message.from_user] = message.chat_id
          
            try:
              kik.send_messages([
                LinkMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  pic_url = "http://i.imgur.com/mhALd6P.png",
                  url = "http://gamebots.chat/paypal.html?u={from_user}".format(from_user=message.from_user),
                  #url = "http://gamebots.chat/bot.html?t=c&u={from_user}".format(from_user=message.from_user),
                  title = "",
                  text = "",
                  keyboards = default_keyboard(),
                  attribution = CustomAttribution(
                    name = "Unlimited Flip Coin",
                    icon_url = "http://gamebots.chat/img/icon/favicon-96x96.png"
                  ),
                ),
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = "You have won 3 items today. Unlimited Flip Coin games cost $1.99 / wk.\nTap above or come back tomorrow for more chances to win.",
                  type_time = 500,
                  keyboards = default_keyboard()
                )
              ])
            except KikError as err:
              print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
              
          self.set_status(200)
          return
          
          
        # -=-=-=-=-=-=-=-=- STEAM BTN -=-=-=-=-=-=-=-=-
        if message.body == "Stream" or message.body == "Connect Steam to Trade":
          modd.utils.send_evt_tracker(category="steam-button", action=message.chat_id, label=message.from_user)

          kik.send_messages([
            LinkMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              pic_url = "http://i.imgur.com/f2762Mg.png",
              url = "http://gamebots.chat/bot.html?t=s&u={from_user}".format(from_user=message.from_user),
              title = "",
              text = "",
              attribution = CustomAttribution(
                name = "Tap for Item",
                icon_url = "https://steamcommunity.com/favicon.ico"
              ),
              keyboards = default_keyboard()
            )
          ])

          self.set_status(200)
          return
        
          
        # -=-=-=-=-=-=-=-=-=- FLIP BUTTON -=-=-=-=-=-=-=-
        if message.body == "Flip Coin":
          modd.utils.send_evt_tracker(category="flip-coin-button", action=message.chat_id, label=message.from_user)
          
          try:
            kik.send_messages([
              VideoMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                video_url = "https://trello-attachments.s3.amazonaws.com/583d3bbf81f5e0b239bb2ce1/5848a8353035a6947d085bf1/1c5adb17a5c3cb359220c777831493a3/gb-coinflip_360.gif",
                autoplay = True,
                loop = True,
                muted = True,
                attribution = custom_attribution(" ")
              )
            ])
            threading.Timer(2.5, flip_timer, [message]).start()
            
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
          
          self.set_status(200)
          return
          
          
        # -=-=-=-=-=-=-=-=-=- PAYPAL BUTTON -=-=-=-=-=-=-=-
        if message.body == "Trade Items":
          modd.utils.send_evt_tracker(category="paypal-button", action=message.chat_id, label=message.from_user)
          paypal_requests[message.from_user] = message.chat_id

          try:
            kik.send_messages([
              LinkMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                pic_url = "https://i.imgur.com/GrlEhwP.png",
                url = "http://gamebots.chat/paypal.html?u={from_user}".format(from_user=message.from_user),
                title = "",
                text = "Trade unlimited items with millions of gamers for $1.99 a week.",
                keyboards = default_keyboard(),
                attribution = CustomAttribution(
                  name = "PayPal",
                  icon_url = "http://gamebots.chat/img/icon/favicon-96x96.png"
                ),
              )
            ])
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))

          self.set_status(200)
          return
      
        
        # -=-=-=-=-=-=-=-=- CHAT NOW BTN -=-=-=-=-=-=-=-=-
        if message.body == "Chat & Trade":
          try:
            conn = sqlite3.connect("{script_path}/data/sqlite3/kikbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            cur = conn.cursor()
            cur.execute("SELECT id, username, username_id, game_name, game_image FROM targeting WHERE participant = \'{to_user}\' AND respond = 1 ORDER BY added DESC LIMIT 1".format(to_user=message.from_user))

            row = cur.fetchone()
            if row is not None:
              try:
                cur.execute("UPDATE targeting SET pending = 0, in_session = 1 WHERE id = {id} LIMIT 1;".format(id=row[0]))
                conn.commit()

                try:
                  kik.send_messages([
                    TextMessage(
                      to = message.from_user,
                      chat_id = message.chat_id,
                      body = "You are now chatting with {username} about {game_name} items. Be careful when exchanging your Steam IDs.".format(game_name=row[3], username=row[1]),
                      type_time = 500
                    ),
                    TextMessage(
                      to = row[1],
                      chat_id = row[2],
                      body = "You are now chatting with {username} about {game_name} items. Be careful when exchanging your Steam IDs.".format(game_name=row[3], username=message.from_user),
                      type_time = 500
                    )
                  ])
                except KikError as err:
                  print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))

                game_convos[message.chat_id] = {
                  'username': message.from_user,
                  'username_id': message.chat_id,
                  'recipient': row[1],
                  'recipient_id': row[2],
                  'game_name': row[3]
                }

                game_convos[row[2]] = {
                  'username': message.from_user,
                  'username_id': message.chat_id,
                  'recipient': row[1],
                  'recipient_id': row[2],
                  'game_name': row[3]
                }

              except sqlite3.Error as err:
                print("::::::[cur.execute] sqlite3.Error - {message}".format(message=err.message))

            else:
              try:
                kik.send_messages([
                  TextMessage(
                    to = message.from_user,
                    chat_id = message.chat_id,
                    body = "Something went wrong, couldn't find this player…",
                    type_time = 250
                  )
                ])
              except KikError as err:
                print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))

          except sqlite3.Error as err:
            print("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=err.message))

          finally:
            conn.close()

          self.set_status(200)
          return
          
          
        # -=-=-=-=-=-=-=-=-=- SHOW MORE/LESS BUTTON -=-=-=-=-=-=-=-
        if message.body == "Show More" or message.body == "Show Less":
          modd.utils.send_evt_tracker(category="show-{show}-button".format(show=message.body.split(" ")[-1].lower()), action=message.chat_id, label=message.from_user)
          if message.chat_id in product_items:          
            if message.body == "Show More":
              display = 1
            else:
              display = 0
          
            conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
            try:
              with conn.cursor() as cur:
                cur = conn.cursor()

                cur.execute("INSERT INTO `product_show` (`id`, `kik_name`, `chat_id`, `item_id`, `show`, `added`) VALUES (NULL, %s, %s, %s, %s, NOW())", (message.from_user, message.chat_id, product_items[message.chat_id]['item_id'], display))
                conn.commit()
                cur.close()

            except pymysql.Error as err:
                print("MySQL DB error:%s" % (err))

            finally:
              if conn:
                conn.close()
            
            del product_items[message.chat_id]
            
            try:
              kik.send_messages([
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = "Thanks for letting us know! For more info: www.prebot.chat",
                  type_time = 250,
                  keyboards = default_keyboard()
                )
              ])
            except KikError as err:
              print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
          
          self.set_status(200)
          return
          
          
        
        # -=-=-=-=-=-=-=-=-=- SESSION CHAT -=-=-=-=-=-=-=-
        if message.chat_id in game_convos:
          convo = game_convos[message.chat_id]
          if convo['username'] == message.from_user:
            try:
              kik.send_messages([
                TextMessage(
                  to = convo['recipient'],
                  chat_id = convo['recipient_id'],
                  body = "{username} says:\n{body}".format(username=convo['username'], body=message.body),
                  type_time = 250
                )
              ])
            except KikError as err:
              print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
                          
          else:
            try:
              kik.send_messages([
                TextMessage(
                  to = convo['username'],
                  chat_id = convo['username_id'],
                  body = "{username} says:\n{body}".format(username=convo['recipient'], body=message.body),
                  type_time = 250
                )
              ])
            except KikError as err:
              print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
                          
          self.set_status(200)
          return
        
        
        # -=-=-=-=-=-=-=-=-=- HELP CONNECT -=-=-=-=-=-=-=-
        if message.from_user in gameHelpList:
          start_help(message)
          self.set_status(200)
          return
            
          
          
        # -=-=-=-=-=-=-=-=-=- HAS EXISTING SESSION -=-=-=-=-=-=-=-
        if message.chat_id in help_convos:
          
          #-- inc message count & log
          help_convos[message.chat_id]['ignore_streak'] += 1
          help_convos[message.chat_id]['messages'].append(message.body)
          help_convos[message.chat_id]['last_message'] = int(time.time())
          
          # -=-=-=-=-=-=-=-=-=- SESSION GOING INACTIVE -=-=-=-=-=-=-=-
          if help_convos[message.chat_id]['ignore_streak'] >= Const.MAX_REPLIES:
            print("-=- TOO MANY UNREPLIED (%d)... CLOSE OUT SESSION -=-" % (help_convos[message.chat_id]['ignore_streak']))
            
            #-- closing out session w/ 2 opts
            try:
              kik.send_messages([
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = "Sorry! GameBots is taking so long to answer your question. What would you like to do?",
                  type_time = 250,
                  keyboards = [
                    SuggestedResponseKeyboard(
                      hidden = False,
                      responses = [
                        TextResponse("More Details"),
                        TextResponse("Cancel")
                      ]
                    )
                  ]
                )
              ])
            except KikError as err:
              print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
                          
            self.set_status(200)
            return
            
          
          
          # -=-=-=-=-=-=-=-=-=- CONTIUNE SESSION -=-=-=-=-=-=-=-
          else:
          
            #-- respond with waiting msg
            #topic_level = topic_level_for_chat_id(message.chat_id)
            #if topic_level is not None:
            #  default_text_reply(message=message)
              #default_content_reply(message, topic_level['topic'], topic_level['level'])
            
            #-- route to slack api, guy
            #modd.utils.slack_im(help_convos[message.chat_id], message.body)
          
            self.set_status(200)
            return
        
          self.set_status(200)
          return
          
          
          
        # -=-=-=-=-=-=-=-=- BUTTON PROMPT -=-=-=-=-=-=-=-=
        #-- anything else, prompt with 4 topics
        if message.from_user not in gameHelpList and message.chat_id not in help_convos:
          default_text_reply(message=message)
          
          self.set_status(200)
          return
        
      self.set_status(200)
      return
        


# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class ProfileNotify(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

  def post(self):
    print("=-=-=-=-=-=-=-=-=-=-= CONNECT PLAYER =-=-=-=-=-=-=-=-=-=-=")
    #print("self.request.body:{request_body}".format(request_body=self.request.body))
    
    
    data = tornado.escape.json_decode(self.request.body)
    if data['token'] == Const.NOTIFY_TOKEN:
      
      link_messages = []
      txt_messages = []
      tracking_urls = []
      
      try:
        conn = sqlite3.connect("{script_path}/data/sqlite3/kikbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        cur = conn.cursor()
        
      except sqlite3.Error as err:
        print("::::::[cur.execute] sqlite3.Error - {message}".format(message=err.message))
        
      else:
        for message in data['messages']:
          from_user = message['from_user']
        
          to_user = message['to_user']
          chat_id = message['to_chat_id']
          game_name = message['game_name']
          image_url = message['img_url']
        
          print("-- CONNECT: {from_user} -> {to_user}".format(from_user=from_user, to_user=to_user))
        
          try:
            cur.execute("UPDATE targeting SET respond = 1 WHERE id = {target_id} LIMIT 1".format(target_id=message['target_id']))
        
          except sqlite3.Error as err:
            print("::::::[cur.execute] sqlite3.Error - {message}".format(message=err.message))
    
          link_messages.append(
            LinkMessage(
              to = to_user,
              chat_id = chat_id,
              pic_url = image_url,
              url = "http://gamebots.chat/bot.html?t=p&u={from_user}&r={to_user}".format(from_user=from_user, to_user=to_user),
              title = "{from_user} wants to chat about {game_name}. Want to chat now?".format(from_user=from_user, game_name=game_name),
              text = "",
              attribution = CustomAttribution(
                name = "{from_user}".format(from_user=from_user), 
                icon_url = "http://cdn.kik.com/user/pic/{from_user}".format(from_user=from_user)
              ),
              keyboards = [
                SuggestedResponseKeyboard(
                  hidden = False,
                  responses = [
                    TextResponse("Chat & Trade"),
                    TextResponse("No Thanks")
                  ]
                )
              ]
            )
          )
          
        
          tracking_urls.append("http://beta.modd.live/api/user_tracking.php?username={username}&chat_id={chat_id}".format(username=from_user, chat_id=message['from_chat_id']))
          tracking_urls.append("http://beta.modd.live/api/bot_tracker.php?src=kik&category=player-message&action={action}&label={label}&value=0&cid={cid}".format(action=from_user, label=from_user, cid=hashlib.md5(from_user.encode()).hexdigest()))

        conn.commit()
        conn.close()
        
        try:
          kik.send_broadcast(link_messages)
          #kik.send_broadcast(txt_messages)
        
        except KikError as err:
          print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
        
        #modd.utils.async_send_evt_tracker(tracking_urls)
        self.set_status(200)
      
    else:
      self.set_status(403)
      
    return
    

# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class ProductNotify(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
  def post(self):
    print("-=-=-=-=-=-=-=-=-=-= PRODUCT NOTIFY =-=-=-=-=-=-=-=-=-=-=")
    print("from_user:{from_user}".format(from_user=self.get_argument('from_user', "")))
    print("chat_id:{chat_id}".format(chat_id=self.get_argument('chat_id', "")))
    print("item_id:{item_id}".format(item_id=self.get_argument('item_id', "")))
    print("item_url:{item_url}".format(item_url=self.get_argument('item_url', "")))
    print("img_url:{img_url}".format(img_url=self.get_argument('img_url', "")))
    print("body_txt:{body_txt}".format(body_txt=self.get_argument('body_txt', "")))
    print("attrib_txt:{attrib_txt}".format(attrib_txt=self.get_argument('attrib_txt', "")))
    print("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-==-=-=-=-=-=-=-=-=-=-=")
    
    if self.get_argument('token', "") == Const.PRODUCT_TOKEN:
      from_user = self.get_argument('from_user', "")
      chat_id = self.get_argument('chat_id', "")
      item_id = self.get_argument('item_id', "")
      item_url = self.get_argument('item_url', "")
      img_url = self.get_argument('img_url', "")
      body_txt = self.get_argument('body_txt', "")
      attrib_txt = self.get_argument('attrib_txt', "")
      
      modd.utils.send_evt_tracker(category="broadcast", action=chat_id, label=from_user)
      
      try:
        kik.send_messages([
          LinkMessage(
            to = from_user,
            chat_id = chat_id,
            pic_url = img_url,
            url = item_url,
            title = "",
            text = "",
            attribution = custom_attribution(attrib_txt),
          ),
          TextMessage(
            to = from_user,
            chat_id = chat_id,
            body = body_txt,
            keyboards = default_keyboard()
          )
        ])
          
      except KikError as err:
        print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
        error_csv = "/opt/kik_bot/var/log/product-notify.error.%s.csv" % (datetime.now().strftime('%Y-%m-%d'))
        with open(error_csv, 'a') as f:
          writer = csv.writer(f)
          writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%s'), chat_id, from_user, err])
      
      else:
        log_csv = "/opt/kik_bot/var/log/product-notify.sent.%s.csv" % (datetime.now().strftime('%Y-%m-%d'))
        with open(log_csv, 'a') as f:
          writer = csv.writer(f)
          writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%s'), chat_id, from_user])
          
      self.set_status(200)
      
    else:
      self.set_status(403)
    
    return

# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class PaypalCallback(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
  def post(self):
    print("-=-=-=-=-=-=-=-=-=-= PAYPAL CALLBACK =-=-=-=-=-=-=-=-=-=-=")
    
    if self.get_argument('token', "") == Const.PAYPAL_TOKEN:
      if self.get_argument('username', "") in paypal_requests:
        try:
          kik.send_messages([
            TextMessage(
              to = self.get_argument('username', ""),
              chat_id = paypal_requests[self.get_argument('username', "")],
              body = "Successfully purchased subscription. Your account will be verified shortly for accessing to our trading platform.",
              keyboards = default_keyboard()
            ),
            TextMessage(
              to = "support.gamebots",
              chat_id = "a0dca296f86d49bf5e525f601ba0f3f85bd9a36bf3643f98d3ee083f5591e9ce",
              body = "Username has purchased a weekly subscription to game bots.\nkik.me/{username}".format(username=self.get_argument('username', ""))
            )
          ])
        except KikError as err:
          print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
      
      self.set_status(200)
      
    else:
      self.set_status(403)
      
    return
  
  
# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class StripeCallback(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

  def post(self):
    print("-=-=-=-=-=-=-=-=-=-= STRIPE CALBACK =-=-=-=-=-=-=-=-=-=-=")

    if self.get_argument('token', "") == Const.STRIPE_TOKEN:
      try:
        kik.send_messages([
          TextMessage(
            to = self.get_argument('to_user', ""),
            chat_id = self.get_argument('chat_id', ""),
            body = self.get_argument('message', ""),
            type_time = 1500
          )
        ])

      except KikError as err:
        print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))

      self.set_status(200)

    else:
      self.set_status(403)

    return
# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class Message(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
  def post(self):
    print("-=-=-=-=-=-=-=-=-=-= MESSAGE BROADCAST =-=-=-=-=-=-=-=-=-=-=")
    
    if self.get_argument('token', "") == Const.BROADCAST_TOKEN:
      print("SENDING --> %s %s" % (self.get_argument('to_user', ""), self.get_argument('chat_id', "")))
      
      to_user = self.get_argument('to_user', "")
      chat_id = self.get_argument('chat_id', "")
      body = self.get_argument('message', "")
      
      try:
        kik.send_messages([
          TextMessage(
            to = to_user,
            chat_id = chat_id,
            body = body,
            type_time = len(body) * 33,
            keyboards = default_keyboard()
          )
        ])
      
      except KikError as err:
        print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
        error_csv = "/opt/kik_bot/var/log/message.error.%s.csv" % (datetime.now().strftime('%Y-%m-%d'))
        with open(error_csv, 'a') as f:
          writer = csv.writer(f)
          writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%s'), chat_id, to_user, err])
      
      else:
        log_csv = "/opt/kik_bot/var/log/message.sent.%s.csv" % (datetime.now().strftime('%Y-%m-%d'))
        with open(log_csv, 'a') as f:
          writer = csv.writer(f)
          writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%s'), chat_id, to_user])
          
      finally:
        self.set_status(200)
        
    else:
      self.set_status(403)
    
    return
    
    


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



class KikSendingException(Exception):
  '''Raise an api send error here'''
  
  def __init__(self, message, error, *args, **kwargs):
    Exception.__init__(self, message, error, *args, **kwargs)
    
    
    
class KikSendingError(KikError):
  def __init__(self, message, error, *args, **kwargs):
    KikError.__init__(self, message, error, *args,**kwargs)
    
  def __init__(self, message, error):
    print("KikSendingError.__init__(self={self}, message={message}, error={error})")
    super(KikSendingError, self).__init__(message, error)
    
    #-- append error log
    error_csv = "/opt/kik_bot/var/log/product-notify.error.%d.csv" % (int(time.time()) / 86400)
    with open(error_csv, 'a') as f:
      writer = csv.writer(f)
      writer.writerow([datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%s+0000'), error, message])
      #writer.writerow([datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%s+0000'), from_user, chat_id, item_id, item_url, img_url, body, errors])

    #-- console output
    print("::::::[kik.send_messages] kik.KikError - {message}".format(message=error))
      
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
      
      

gameHelpList = {}
help_convos = {}
game_convos = {}
paypal_requests = {}
product_items = {}
button_taps = {}
item_flips = {}


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
  'USERNAME'  : "game.bots",
  'API_KEY'   : "0fb46005-dd00-49c3-a4a5-239a0bdc1e79",
  'WEBHOOK'   : {
    'HOST'  : "http://159.203.250.4",
    'PORT'  : 8080,
    'PATH'  : "kik-bot"
  },

  'FEATURES'  : {
    'receiveDeliveryReceipts' : False,
    'receiveReadReceipts'     : True
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
  (r"/kik", KikBot),
  (r"/kik-bot", KikBot),
  (r"/profile-notify", ProfileNotify),
  (r"/product-notify", ProductNotify),
  (r"/paypal-callback", PaypalCallback),
  (r"/stripe-callback", StripeCallback),
  (r"/steam-callback", PaypalCallback),
  (r"/message", Message)
])


#-- server starting
if __name__ == "__main__":
  application.listen(int(Const.KIK_API_CONFIG['WEBHOOK']['PORT']))
  tornado.ioloop.IOLoop.instance().start()
  print("tornado start" % (int(time.time())))
