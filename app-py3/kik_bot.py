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

import urllib.request, urllib.error, urllib.parse
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
    TextResponse("Next Flip"),
    TextResponse("Next Player")
  ]
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur.execute("SELECT `game_name`, `viewer_total` FROM `top_games` WHERE `game_name` != \"Creative\" AND `game_name` != \"Gaming Talk Shows\" AND `game_name` != \"Music\" ORDER BY `viewer_total` DESC LIMIT 18;")
      
      for row in cur:
        buttons.append(TextResponse("{game_name} ({total})".format(game_name=row['game_name'], total=locale.format("%d", row['viewer_total'], grouping=True))))
        
  except pymysql.Error as err:
    print("MySQL DB error:%s" % (err))
    
  finally:
    if conn:
      conn.close()
      
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = hidden,
      responses = buttons
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
  
  try:
    kik.send_messages([
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "Get help & chat with live players. Select a game below.",
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
            chat_id = messge.chat_id,
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
  
  
def trade_item_message(message):
  print("trade_item_message(message=%s)" % (message))
  
  trade_items = [
    {
      'name': "USP-S | Dark Water",
      'image_url': "http://steamcommunity-a.akamaihd.net/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpoo6m1FBRp3_bGcjhQ0927q5qOleX1DL_QhGBu5Mx2gv3--Y3nj1H6qhc4ZGn6doTAIAA2YlDV-Qe3xO7n0cLqtc7Ly3djuXQlsCmPlhy1hAYMMLLPDZXOFA/330x192",
      'store_url': "http://steamcommunity.com/market/listings/730/USP-S%20%7C%20Dark%20Water%20(Minimal%20Wear)"
    },  {
      'name': "SSG 08 | Big Iron",
      'image_url': "http://steamcommunity-a.akamaihd.net/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpopamie19f0Ob3Yi5FvISJgIWIn_n9MLrdn39I18l4jeHVyoD0mlOx5UI9Y2z0dYeRIVc_aFmDr1C8x-zm0Ja6vpzOmiA2siYi7HjZmxHlgRtSLrs4lKhxtCY/330x192",
      'store_url': "http://steamcommunity.com/market/listings/730/SSG%2008%20%7C%20Big%20Iron%20(Factory%20New)"
    },  {
      'name': "Desert Eagle | Kumicho Dragon",
      'image_url': "http://steamcommunity-a.akamaihd.net/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgposr-kLAtl7PLZTjlH_9mkgIWKkPvxDLDEm2JS4Mp1mOjG-oLKhVGwogYxDDWiZtHAbFNqNwnX_wftw73nh8S46Jufz3M36HQl5CvcmRLjhhFNPbdohvyaHwmAR_seHMtxE0s/330x192",
      'store_url': "http://steamcommunity.com/market/listings/730/Desert%20Eagle%20%7C%20Kumicho%20Dragon%20(Field-Tested)"
    },  {
      'name': "SSG 08 | Big Iron",
      'image_url': "http://steamcommunity-a.akamaihd.net/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpopamie19f0Ob3Yi5FvISJgIWIn_n9MLrdn39I18l4jeHVyoD0mlOx5UI9Y2z0dYeRIVc_aFmDr1C8x-zm0Ja6vpzOmiA2siYi7HjZmxHlgRtSLrs4lKhxtCY/330x192",
      'store_url': "http://steamcommunity.com/market/listings/730/SSG%2008%20%7C%20Big%20Iron%20(Factory%20New)"
    },  {
      'name': "AK-47 | Elite Build",
      'image_url': "http://steamcommunity-a.akamaihd.net/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot7HxfDhjxszJemkV09G3h5SOhe7LP7LWnn9u5MRjjeyPod-l3VfkqRJoMWnxd9OQcQdoMljYqVO5xLi-g8e16JXOnSNh6XYlsGGdwUI-f1fsZg/330x192",
      'store_url': "http://steamcommunity.com/market/listings/730/AK-47%20%7C%20Elite%20Build%20(Minimal%20Wear)"
    },  {
      'name': "Falchion Case Key",
      'image_url': "http://steamcommunity-a.akamaihd.net/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXX7gNTPcUxuxpJSXPbQv2S1MDeXkh6LBBOieLreQE4g_CfI20b7tjmzNXYxK-hYOmHkj9QvpIg2OyVpdus0AW1_EQ9MnezetGj61oqPA/330x192",
      'store_url': "http://steamcommunity.com/market/listings/730/Falchion%20Case%20Key"
    },  {
      'name': "Operation Bravo Case",
      'image_url': "http://steamcommunity-a.akamaihd.net/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXU5A1PIYQNqhpOSV-fRPasw8rsXE1xNwVDv7WrFA5pnabNJGwSuN3gxtnawKOlMO6HzzhQucAm0uvFo4n2iw3h_UM-ZmilJNeLMlhpjfjxEoE/330x192http://steamcommunity.com/market/listings/730/Operation%20Bravo%20Case",
      'store_url': "http://steamcommunity.com/market/listings/730/Operation%20Bravo%20Case"
    },  {
      'name': "Glock-18 | Water Elemental",
      'image_url': "http://steamcommunity-a.akamaihd.net/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgposbaqKAxf0Ob3djFN79f7mImagvLnML7fglRc7cF4n-T--Y3nj1H68kVvYTvzJYacIA42MFHW-QLtl7vr0ZS_vpiYm3pi7HYl5CrUy0a00AYMMLI3Fd_03w/330x192",
      'store_url': "http://steamcommunity.com/market/listings/730/Glock-18%20%7C%20Water%20Elemental%20(Field-Tested)"
    },  {
      'name': "M4A1-S | Hyper Beast",
      'image_url': "http://steamcommunity-a.akamaihd.net/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpou-6kejhz2v_Nfz5H_uO1gb-Gw_alDLPIhm5D18d0i_rVyoHwjF2hpiwwMiukcZiQJAJvMwqGrAW-wubnjJe4uZXMwCRq6yIgsXyMnEPhiE4ZbOBs0aeeVxzAUEeAasNQ/330x192",
      'store_url': "http://steamcommunity.com/market/listings/730/M4A1-S%20%7C%20Hyper%20Beast%20(Field-Tested)"
    },  {
      'name': "AK-47 | Frontside Misty",
      'image_url': "http://steamcommunity-a.akamaihd.net/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot7HxfDhjxszJemkV08u_mpSOhcjnI7TDglRc7cF4n-T--Y3nj1H6-hBrMW_3LIOWdlU_MlGDqwO6wrvq15C6vp-bnHY36SAm4XbYl0SwhgYMMLJqUag1Og/330x192",
      'store_url': "http://steamcommunity.com/market/listings/730/AK-47%20%7C%20Frontside%20Misty%20(Field-Tested)"
    }
  ]
  
  trade_item = random.choice(trade_items)
  
  
  try:
    kik.send_messages([
      LinkMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        pic_url = trade_item['image_url'],
        url = trade_item['store_url'],
        title = trade_item['name'],
        text = "This feature is available for subscribers. Would you like to subscribe?",
        keyboards = [
          SuggestedResponseKeyboard(
            hidden = False,
            responses = [
              TextResponse("$1.99 per month"),
              TextResponse("Chat Now"),
              TextResponse("Trade"),
              TextResponse("Flip"),
              TextResponse("Steam"),
              TextResponse("No Thanks")
            ]
          )
        ]
      )
    ])
  except KikError as err:
    print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
  
  
  
#--:-- Model / Data Retrieval --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def send_player_help_message(message, topic_name, level="Intro"):
  print("send_player_help_message(message={message}, topic_name={topic_name}, level={level})".format(message=message, topic_name=topic_name, level=level))
  player_help_for_topic_level(message.from_user, message.chat_id, topic_name, level, 1, True)
      
      
def player_help_for_topic_level(username="", chat_id="", topic_name="", level="", amt=100, to_self=False):
  print("player_help_for_topic_level(username={username}, chat_id={chat_id}, topic_name={topic_name}, level={level}, amt={amt})".format(username=username, chat_id=chat_id, topic_name=topic_name, level=level, amt=amt))
  
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
        
         
      cur2.execute("SELECT `chat_id`, `username` FROM `kikbot_sessions` WHERE `topic_name` = %s AND `chat_id` != %s AND `username` != %s GROUP BY `chat_id` ORDER BY `added` DESC LIMIT %s;", (topic_name, chat_id, username, amt))
      #cur2.execute("SELECT `chat_id`, `username` FROM `kikbot_logs` WHERE `chat_id` != %s AND `username` != %s AND `body` != '__{MENTION}__' GROUP BY `chat_id` ORDER BY RAND() LIMIT %s;", (chat_id, username, amt))
          
      if cur2.rowcount < amt:
        #cur2.execute("SELECT `chat_id`, `username` FROM `kikbot_logs` WHERE `chat_id` != %s AND `username` != %s AND `body` != '__{MENTION}__' GROUP BY `chat_id` ORDER BY RAND() LIMIT %s;", (chat_id, username, amt))
        cur2.execute("SELECT `chat_id`, `username` FROM `kikbot_logs` WHERE `chat_id` != %s AND `username` != %s AND `body` != '__{MENTION}__' AND `targeted` < DATE_SUB(NOW(), INTERVAL 12 HOUR) GROUP BY `chat_id` ORDER BY RAND() LIMIT %s;", (chat_id, username, amt))
      
      
      if username == "alxar0":
        cur2.execute("SELECT `chat_id`, `username` FROM `kikbot_sessions` WHERE `id` = 4481 LIMIT 1;")  
      
      target_id = 0
      chat_ids = []
      csv_file = "/opt/kik_bot/queue/{timestamp}.csv".format(timestamp=int(time.time() * 100))
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
                title = "Chat Now",
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
                title = "{from_user} needs help with playing {game_name}. Want to chat now?".format(from_user=username, game_name=topic_name),
                text = "",
                attribution = CustomAttribution(
                  name = "{from_user}".format(from_user=username), 
                  icon_url = "http://cdn.kik.com/user/pic/{from_user}".format(from_user=username)
                )
              ),
              TextMessage(
                to = row['username'],
                chat_id = row['chat_id'],
                body = "Do you want to help {from_user} with {game_name}?".format(from_user=username, game_name=topic_name),
                keyboards = [
                  SuggestedResponseKeyboard(
                    hidden = False,
                    responses = [
                      TextResponse("Chat Now"),
                      TextResponse("Trade"),
                      TextResponse("Flip"),
                      TextResponse("Steam"),
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
  
  topic_names = [
    #"Pokémon Go",
    "Hearthstone",
    "CS:GO",
    "Dota 2",
    "League of Legends"
  ]
  
  topic_levels = [
    "Level 1",
    "Level 2-6",
    "Level 7-15",
    "Level 16+"
  ]
  
  if is_mention:
    print("MENTION PARTICIPANT:%s" % (message.participants[-1]))
    
    try:
      kik.send_messages([
        TextMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          body = "Welcome to Gamebots. Chat, trade, & flip items with players on Kik.",
          type_time = 500,
          keyboards = default_keyboard()
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
          body = "Welcome to Gamebots. Chat, trade, & flip items with players on Kik.",
          type_time = 500,
          keyboards = default_keyboard()
        ),
      ])
    except KikError as err:
      print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))    
    
    #default_content_reply(message, random.choice(topic_names), random.choice(topic_levels))
    #send_player_help_message(message=message, topic_name=random.choice(topic_names), level=random.choice(topic_levels))    
    
  modd.utils.send_evt_tracker(category="video-message", action=message.chat_id, label=message.from_user)
  modd.utils.send_evt_tracker(category="player-message", action=message.chat_id, label=message.from_user)    
  return



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
        modd.utils.send_evt_tracker(category="read", action=message.chat_id, label=message.from_user)
        self.set_status(200)
        return
         
      
      # -=-=-=-=-=-=-=-=- START CHATTING -=-=-=-=-=-=-=-=-
      elif isinstance(message, StartChattingMessage):
        print("-= StartChattingMessage =-= ")
        
        modd.utils.send_evt_tracker(category="Start Chat", action=message.chat_id, label=message.from_user)
        
        
        
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
            modd.utils.send_evt_tracker(category="Subscribe", action=message.chat_id, label=message.from_user)
            
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
            modd.utils.send_evt_tracker(category="reply", action=message.chat_id, label=message.from_user)
            
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
            
        
        topic_levels = [
          "Level 1",
          "Level 2-6",
          "Level 7-15",
          "Level 16+"
        ]
        
  
        
        # -=-=-=-=-=-=-=-=-=- END SESSION -=-=-=-=-=-=-=-
        if message.body.lower() == "!end" or message.body.lower() == "cancel" or message.body.lower() == "quit":
          print("-=- ENDING HELP -=-")
          
          if message.chat_id in game_convos:
            convo = game_convos[message.chat_id]
            try:
              kik.send_messages([
                TextMessage(
                  to = convo['recipient'],
                  chat_id = convo['recipient_id'],
                  body = "Thanks for using GameBots!",
                  type_time = 250,
                  keyboards = default_keyboard()
                ),
                TextMessage(
                  to = convo['username'],
                  chat_id = convo['username_id'],
                  body = "Thanks for using GameBots!",
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
          
            if row[2] in game_convos:
              del game_convos[row[2]]
          
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
        
          

        # -=-=-=-=-=-=-=-=- DEFAULT TOPIC BTNS -=-=-=-=-=-=-=-=-
        if message.body.rsplit(" ", 1)[0] in topic_names:
          topic_name = message.body.rsplit(" ", 1)[0]
          modd.utils.send_evt_tracker(category="player-message", action=message.chat_id, label=message.from_user)
          modd.utils.send_evt_tracker(category="player-message-button", action=message.chat_id, label=message.from_user)
          
          #modd.utils.send_evt_tracker(category="video-message", action=message.chat_id, label=message.from_user)          
          #default_content_reply(message, topic_name, topic_levels[0])
          
          send_player_help_message(message=message, topic_name=topic_name, level=random.choice(topic_levels))
          
          if message.from_user not in gameHelpList:
            gameHelpList[message.from_user] = topic_name
              
          
          help_convos[message.chat_id] = {
            'chat_id'       : message.chat_id,
            'username'      : message.from_user,
            'game'          : gameHelpList[message.from_user],
            'level'         : topic_levels[0],
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
          try:
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "You have selected {game_name} & will be connected to gamers shortly.".format(game_name=topic_name),
                type_time = 500,
                keyboards = default_keyboard()
              )
            ])
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
          
          conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
          try:
            with conn.cursor() as cur:
              cur = conn.cursor()

              cur.execute("INSERT INTO `kikbot_sessions` (`username`, `topic_name`, `level`, `chat_id`, `added`) VALUES (%s, %s, %s, %s, UTC_TIMESTAMP())", (message.from_user, topic_name, topic_levels[0], message.chat_id))
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
        
        
        # -=-=-=-=-=-=-=-=-=- NEXT PLAYER -=-=-=-=-=-=-=-
        if message.body == "Next Player":

          if message.chat_id in help_convos:
            send_player_help_message(message=message, topic_name=help_convos[message.chat_id]['game'], level=random.choice(topic_levels))

          else:
            send_player_help_message(message=message, topic_name=random.choice(topic_names), level=random.choice(topic_levels))

          try:
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Select a game for faster help…",
                keyboards = default_keyboard()
              )
            ])
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))

          modd.utils.send_evt_tracker(category="player-message", action=message.chat_id, label=message.from_user)
          modd.utils.send_evt_tracker(category="player-message-next", action=message.chat_id, label=message.from_user)

          self.set_status(200)
          return        
        
        
        # -=-=-=-=-=-=-=-=- CHAT NOW BTN -=-=-=-=-=-=-=-=-
        if message.body == "Chat Now":
          try:
            conn = sqlite3.connect("{script_path}/data/sqlite3/kikbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            cur = conn.cursor()
            cur.execute("SELECT id, username, username_id, game_name, game_image FROM targeting WHERE participant = \'{to_user}\' AND respond = 1 AND pending = 1 ORDER BY added DESC LIMIT 1".format(to_user=message.from_user))

            row = cur.fetchone()
            if row is not None:
              try:
                cur.execute("UPDATE targeting SET pending = 0 WHERE id = {id} LIMIT 1;".format(id=row[0]))
                conn.commit()
                
                try:
                  kik.send_messages([
                    TextMessage(
                      to = message.from_user,
                      chat_id = message.chat_id,
                      body = "One moment…",
                      type_time = 250
                    ),
                    PictureMessage(
                      to = row[1],
                      chat_id = row[2],
                      pic_url = row[4],
                      attribution = CustomAttribution(
                        name = "{username}".format(username=message.from_user), 
                        icon_url = "http://cdn.kik.com/user/pic/{username}".format(username=message.from_user)
                      )
                    ),
                    TextMessage(
                      to = row[1],
                      chat_id = row[2],
                      body = "Hi, I am available now to help with {game_name}".format(game_name=row[3]),
                      type_time = 500,
                      keyboards = [
                        SuggestedResponseKeyboard(
                          hidden = False,
                          responses = [
                            TextResponse("Say Hi"),
                            TextResponse("Next Player"),
                            TextResponse("No Thanks"),
                          ]
                        )
                      ]
                    )
                  ])
                except KikError as err:
                  print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
                
                modd.utils.send_evt_tracker(category="player-message", action=message.chat_id, label=message.from_user)

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
        
        # -=-=-=-=-=-=-=-=-=- TRADE BUTTON -=-=-=-=-=-=-=-
        if message.body == "Trade":
          modd.utils.send_evt_tracker(category="trade-button", action=message.chat_id, label=message.from_user)
          
          trade_item_message(message)
            
          self.set_status(200)
          return

                    
        # -=-=-=-=-=-=-=-=-=- FLIP BUTTON -=-=-=-=-=-=-=-
        if message.body == "Flip"or message.body == "Next Flip":
          modd.utils.send_evt_tracker(category="flip-button", action=message.chat_id, label=message.from_user)
          trade_item_message(message)
            
          self.set_status(200)
          return
          
          
        # -=-=-=-=-=-=-=-=-=- PAYPAL BUTTON -=-=-=-=-=-=-=-
        if message.body == "$1.99 per month":
          modd.utils.send_evt_tracker(category="paypal-button", action=message.chat_id, label=message.from_user)
          paypal_requests[message.from_user] = message.chat_id
          
          try:
            kik.send_messages([
              LinkMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                pic_url = "https://www.paypalobjects.com/en_US/i/btn/btn_subscribe_LG.gif",
                url = "http://gamebots.chat/paypal.html?u={from_user}".format(from_user=message.from_user),
                title = "TAP HERE",
                text = "",
                keyboards = default_keyboard()
              )
            ])
          except KikError as err:
            print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))

          self.set_status(200)
          return
        
        
        
        # -=-=-=-=-=-=-=-=-=- HELP CONNECT -=-=-=-=-=-=-=-
        if message.body == "Say Hi":
          try:
            conn = sqlite3.connect("{script_path}/data/sqlite3/kikbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            cur = conn.cursor()
            cur.execute("SELECT id, participant, participant_id, game_name, game_image FROM targeting WHERE username_id = \'{chat_id}\' AND respond = 1 AND pending = 0 ORDER BY added DESC LIMIT 1".format(chat_id=message.chat_id))

            row = cur.fetchone()
            if row is not None:
              try:
                cur.execute("UPDATE targeting SET in_session = 1 WHERE id = {id} LIMIT 1;".format(id=row[0]))
                conn.commit()
                
                try:
                  kik.send_messages([
                    TextMessage(
                      to = message.from_user,
                      chat_id = message.chat_id,
                      body = "You are now chatting about {game_name} with {username}".format(game_name=row[3], username=row[1]),
                      type_time = 500
                    ),
                    TextMessage(
                      to = row[1],
                      chat_id = row[2],
                      body = "You are now chatting about {game_name}with {username}".format(game_name=row[3], username=message.from_user),
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
                
                modd.utils.send_evt_tracker(category="player-message", action=message.chat_id, label=message.from_user)
                  
                
              except sqlite3.Error as err:
                print("::::::[cur.execute] sqlite3.Error - {message}".format(message=err.message))  
                
          
          except sqlite3.Error as err:
            print("::::::[cur.execute] sqlite3.Error - {message}".format(message=err.message))    
            
          finally:
            conn.close()
          
          
          self.set_status(200)
          return
        
        
        # -=-=-=-=-=-=-=-=- STEAM BTN -=-=-=-=-=-=-=-=-
        if message.body == "Connect Steam to Trade":
          modd.utils.send_evt_tracker(category="steam-button", action=message.chat_id, label=message.from_user)

          kik.send_messages([
            LinkMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              pic_url = "https://i.imgur.com/CctmFz0.png",
              url = "http://gamebots.chat/bot.html?t=s&u={from_user}".format(from_user=message.from_user),
              title = "",
              text = "Connect Steam to trade items with other players",
              attribution = custom_attribution("Sign into Stream"),
              keyboards = default_keyboard()
            )
          ])

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
              modd.utils.send_evt_tracker(category="player-message", action=convo['username_id'], label=convo['username'])
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
              modd.utils.send_evt_tracker(category="player-message", action=convo['recipient_id'], label=convo['recipient'])
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
          modd.utils.send_evt_tracker(category="reply", action=message.chat_id, label=message.from_user)
          modd.utils.send_evt_tracker(category="message", action=message.chat_id, label=message.from_user)
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
    
          # img = Image.open(BytesIO(requests.get(image_url).content))
          # tot = 0
          # for i in img.getdata():
          #   if i == (99, 64, 164) or i == (100, 65, 165):
          #     tot += 1
          #       
          # if tot >= 30000:
          #   image_url = "http://i.imgur.com/NBcs0Ix.png"
        
          link_messages.append(
            LinkMessage(
              to = to_user,
              chat_id = chat_id,
              pic_url = image_url,
              url = "http://gamebots.chat/bot.html?t=p&u={from_user}&r={to_user}".format(from_user=from_user, to_user=to_user),
              title = "{from_user} needs help with playing {game_name}. Want to chat now?".format(from_user=from_user, game_name=game_name),
              text = "",
              attribution = CustomAttribution(
                name = "{from_user}".format(from_user=from_user), 
                icon_url = "http://cdn.kik.com/user/pic/{from_user}".format(from_user=from_user)
              )
            )
          )
        
          txt_messages.append(
            TextMessage(
              to = to_user,
              chat_id = chat_id,
              body = "Do you want to help {from_user} with {game_name}?".format(from_user=from_user, game_name=game_name),
              keyboards = [
                SuggestedResponseKeyboard(
                  hidden = False,
                  responses = [
                    TextResponse("Chat Now"),
                    TextResponse("Trade"),
                    TextResponse("Flip"),
                    TextResponse("Steam"),
                    TextResponse("No Thanks")
                  ]
                )
              ]
            )
          )
          #modd.utils.send_evt_tracker(category="player-message", action=message['from_chat_id'], label=from_user)
          
        
          tracking_urls.append("http://beta.modd.live/api/user_tracking.php?username={username}&chat_id={chat_id}".format(username=from_user, chat_id=message['from_chat_id']))
          tracking_urls.append("http://beta.modd.live/api/bot_tracker.php?src=kik&category=player-message&action={action}&label={label}&value=0&cid={cid}".format(action=hashlib.md5(from_user.encode()).hexdigest(), label=from_user, cid=hashlib.md5(from_user.encode()).hexdigest()))

        conn.commit()
        conn.close()
        
        try:
          kik.send_broadcast(link_messages)
          kik.send_broadcast(txt_messages)
        
        except KikError as err:
          print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
        
        #modd.utils.async_send_evt_tracker(tracking_urls)
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
      try:
        kik.send_messages([
          PictureMessage(
            to = self.get_argument('username', ""),
            chat_id = self.get_argument('chat_id', ""),
            pic_url = self.get_argument('img_url', ""),
            keyboards = [
              SuggestedResponseKeyboard(
                responses = [
                  FriendPickerResponse(
                    body = "Pick Friends",
                    min = 5,
                    max = 20
                  ),
                  TextResponse("No Thanks")
                ]
              )
            ],
            attribution = CustomAttribution(
              name = self.get_argument('attribution', ""), 
              icon_url = "http://gamebots.chat/img/icon/favicon-96x96.png"
            )
          )
        ])
        
      except KikError as err:
        print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))
        
      self.set_status(200)
        
    else:
      self.set_status(403)
    
    return
    
    


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



gameHelpList = {}
help_convos = {}
game_convos = {}
paypal_requests = {}


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
#     'HOST'  : "http://98.248.37.68",
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
  (r"/paypal-callback", PaypalCallback),
  (r"/message", Message)
])


#-- server starting
if __name__ == "__main__":
  application.listen(int(Const.KIK_API_CONFIG['WEBHOOK']['PORT']))
  tornado.ioloop.IOLoop.instance().start()
  print("tornado start" % (int(time.time())))
