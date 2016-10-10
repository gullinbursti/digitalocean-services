#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import threading
import time
import csv
import json
import random
import sqlite3
import re

import urllib.request, urllib.error, urllib.parse
import requests
import pymysql.cursors

import tornado.escape
import tornado.ioloop
import tornado.web

import modd
import const as Const

from datetime import date, datetime
from urllib.parse import quote

from kik.error import KikError
from kik import KikApi, Configuration
from kik.messages import messages_from_json, StartChattingMessage, TextMessage, FriendPickerMessage, LinkMessage, PictureMessage, StickerMessage, ScanDataMessage, VideoMessage, DeliveryReceiptMessage, ReadReceiptMessage, UnknownMessage, SuggestedResponseKeyboard, TextResponse, FriendPickerResponse, CustomAttribution

Const.SLACK_TOKEN = 'IJApzbM3rVCXJhmkSzPlsaS9'
Const.NOTIFY_TOKEN = '1b9700e13ea17deb5a487adac8930ad2'
Const.CONNECT_TOKEN = '48a60e9010e9f235adcebbc2cc19604f'
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

def topics_keyboard():
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = False,
      responses = [
        TextResponse(u"\U0001F3C6 FREE CS:GO SKIN"),
        TextResponse(u"\U0001F46B CHAT NOW"),
        TextResponse("Hearthstone"),
        TextResponse("Dota 2"),
        TextResponse("League of Legends"),
        TextResponse("CS:GO"),
        TextResponse("Cancel")
      ]
    )
  ]
  
  return keyboard
  
  
def levels_keyboard():
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = False,
      responses = [
        TextResponse("Intro"),
        TextResponse("Level 1-3"),
        TextResponse("Level 4-7"),
        TextResponse("Level 8-10"),
        TextResponse("Level 10+"),
        TextResponse("Cancel")
      ]
    )
  ]
  
  return keyboard
  
  
def topic_content_keyboard(hidden=False):
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = hidden,
      responses = [
        TextResponse(u"\U0001F3AC ANOTHER CLIP"),
        TextResponse(u"\U0001F46B CHAT NOW"),
        TextResponse(u"\U0001F3C6 FREE CS:GO SKIN"),
        TextResponse(u"\U0001F47E GET GAME HELP")
      ]
    )
  ]

  return keyboard
  
  
def welcome_keyboard(hidden=False):
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = hidden,
      responses = [
        TextResponse("Next Video (50 coins)"),
        TextResponse("Next Player (100 coins)"),
        TextResponse("Steam (1000 coins)")
      ]
    )
  ]

  return keyboard


def default_friend_picker(min=1, max=20, message="Pick friends"):
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
  
  
def default_attribution():
  return custom_attribution()
  
  
def custom_attribution(name="gamebots.chat"):
  attribution = CustomAttribution(
    name = name, 
    icon_url = "http://gamebots.chat/img/icon/favicon-96x96.png"
  )

  return attribution
  

def default_text_reply(message, delay=0, type_time=500):
  print("default_text_reply(message=%s)" % (message))
  
  kik.send_messages([
    TextMessage(
      to = message.from_user,
      chat_id = message.chat_id,
      body = "Chat now with over a million players.",
      keyboards = welcome_keyboard(),
      type_time = type_time,
      delay = delay
    )
  ])


def default_content_reply(message, topic, level):
  print("default_content_reply(message={message}, topic={topic}, level={level})".format(message=message, topic=topic, level=level))
  
  kik.send_messages([
    message_for_topic_level(to_user=message.from_user, chat_id=message.chat_id, topic_name=topic, level=level)
  ])
  

def default_wait_reply(message):
  print("default_wait_reply(message=%s)" % (message))
  
  kik.send_messages([
    TextMessage(
      to = message.from_user,
      chat_id = message.chat_id,
      body = "Your message has been routed.",
      keyboards = topic_content_keyboard(True)
    )
  ])


#--:-- Model / Data Retrieval --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def fetch_faq(topic_name):
  print("fetch_faq(topic_name=%s)" % (topic_name))
  
  _arr = []
  
  try:
    conn = sqlite3.connect("%s/data/sqlite3/kikbot.db" % (os.getcwd()))
    c = conn.cursor()
    c.execute("SELECT faq_content.entry FROM faqs JOIN faq_content ON faqs.id = faq_content.faq_id WHERE faqs.title = \'%s\';" % (topic_name))
    
    for row in c.fetchall():
      _arr.append(row[0])
    
    conn.close()
  
  except:
    pass
  
  finally:
    pass
  
  return _arr


def send_player_help_message(message, topic_name, level="Intro"):
  print("send_player_help_message(message={message}, topic_name={topic_name}, level={level})".format(message=message, topic_name=topic_name, level=level))
  player_help_for_topic_level(message.from_user, message.chat_id, topic_name, level, 1, True)
      
      
def player_help_for_topic_level(username="", chat_id="", topic_name="", level="", amt=2, to_self=False):
  print("player_help_for_topic_level(username={username}, chat_id={chat_id}, topic_name={topic_name}, level={level}, amt={amt})".format(username=username, chat_id=chat_id, topic_name=topic_name, level=level, amt=amt))
  
  if topic_name == "":
    topic_name = ""
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur.execute("SELECT `id`, `chat_id`, `username` FROM `kikbot_logs` WHERE `chat_id` != %s AND `username` != %s GROUP BY `chat_id` ORDER BY RAND() LIMIT %s;", (chat_id, username, amt))
      
      for row in cur:
        if to_self:
          avatar = "http://cdn.kik.com/user/pic/{username}".format(username=row['username'])
          print("row[]={row}, avatar={avatar}".format(row=row, avatar=avatar))
          
          kik.send_messages([
            LinkMessage(
              to = username,
              chat_id = chat_id,
              pic_url = avatar,
              # url = "http://gamebots.chat/player_help.php?lid={lid}".format(lid=row['id']),
              # url = "http://gamebots.chat/profile.php?lid={lid}&from_user={from_user}&username={to_user}&img={img}".format(lid=row['id'], from_user=username, to_user=row['username'], img=""),
              url = "http://gamebots.chat/bot.html?t=p&u={from_user}&r={to_user}".format(from_user=username, to_user=row['username']),
              title = "{username}".format(username=row['username']),
              text = "Keep tapping Chat Now for more coins.",
              attribution = custom_attribution("CHAT NOW"),
              keyboards = welcome_keyboard()
            )
          ])
          
        else:
          avatar = "http://cdn.kik.com/user/pic/{username}".format(username=username)
          print("row[]={row}, avatar={avatar}".format(row=row, avatar=avatar))
          
          kik.send_messages([
            LinkMessage(
              to = row['username'],
              chat_id = row['chat_id'],
              pic_url = avatar,
              # url = "http://gamebots.chat/player_help.php?lid={lid}".format(lid=row['id']),
              #url = "http://gamebots.chat/profile.php?lid={lid}&from_user={from_user}&username={to_user}&img={img}".format(lid=row['id'], from_user=username, to_user=row['username'], img=""),
              url = "http://gamebots.chat/bot.html?t=p&u={from_user}&r={to_user}".format(from_user=row['username'], to_user=username),
              title = "{username}".format(username=username),
              text = "Keep tapping Chat Now for more coins.",
              attribution = custom_attribution("CHAT NOW"),
              keyboards = welcome_keyboard()
            )
          ])
            
  except pymysql.Error as err:
    print("MySQL DB error:%s" % (err))

  finally:
    if conn:
      conn.close()
      

def topic_level_for_chat_id(chat_id):
  print("topic_level_for_chat_id(chat_id={chat_id})".format(chat_id=chat_id))
  
  _obj = {}
  
  if chat_id in help_convos:
    _obj = {
      'username'  : help_convos[chat_id]['username'],
      'topic'     : help_convos[chat_id]['game'],
      'level'     : help_convos[chat_id]['level']
    }
    
    return _obj
    
  else:
    conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
    try:
      with conn.cursor() as cur:
        cur.execute("SELECT `username`, `topic_name`, `level` FROM `kikbot_sessions` WHERE `chat_id` = %s ORDER BY `added` DESC LIMIT 1;", (chat_id))

        if cur.rowcount == 1:
          row = cur.fetchone()

          print("row[]={row}".format(row=row))
          _obj = {
            'username'  : row['username'],
            'topic'     : row['topic_name'],
            'level'     : row['level']
          }
          
        else:
          cur.execute("SELECT `username` FROM `kikbot_logs` WHERE `chat_id` = %s ORDER BY `added` DESC LIMIT 1;", (chat_id))
          row = cur.fetchone()
          username = row['username']
          
          cur.execute("SELECT `topic_name`, `level` FROM `kikbot_sessions` ORDER BY `added` DESC LIMIT 1;")
          row = cur.fetchone()
          print("row[]={row}".format(row=row))
          _obj = {
            'username'  : username,
            'topic'     : row['topic_name'],
            'level'     : row['level']
          }

    except pymysql.Error as err:
      print("MySQL DB error:%s" % (err))

    finally:
      if conn:
        conn.close()
    
    return _obj
  

def message_for_topic_level(to_user, chat_id, topic_name, level="Intro", delay=1250, hidden=False):
  print("message_for_topic_level(to_user={to_user}, chat_id={chat_id}, topic_name={topic_name}, level={level}, hidden={hidden})".format(to_user=to_user, chat_id=chat_id, topic_name=topic_name, level=level, hidden=hidden))
  
  _message = TextMessage(
    to = to_user,
    chat_id = chat_id,
    body = "No content found for {topic_name}".format(topic_name=topic_name),
    type_time = 500
  )
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur.execute("SELECT `id`, `youtube_id`, `video_title`, `image_url`, `video_url` FROM `topic_content` WHERE `topic_name` = %s AND `level` = %s ORDER BY RAND() LIMIT 1;", (topic_name, level))

      if cur.rowcount == 1:
        row = cur.fetchone()
        
        print("row[]={row}".format(row=row))
        _message = LinkMessage(
          to = to_user,
          chat_id = chat_id,
          pic_url = row['image_url'],
          # url = "http://gamebots.chat/topic_content.php?tid={tid}&username={to_user}&img={video_img}&youtube_id={youtube_id}&title={title}".format(tid=row['id'], to_user=to_user, video_img=row['image_url'], youtube_id=row['youtube_id'], title=row['video_title']),
          #url = "http://gamebots.chat/video.php?tid={tid}&username={to_user}&img={video_img}&youtube_id={youtube_id}&title={title}".format(tid=row['id'], to_user=to_user, video_img=row['image_url'], youtube_id=row['youtube_id'], title=row['video_title']),
          #url = "http://gamebots.chat/bot.html?t=v&u={from_user}&y={youtube_id}&g={topic_name}&l={level}".format(from_user=to_user, youtube_id=row['youtube_id'], topic_name=topic_name, level=level),
          url = "http://gamebots.chat/bot.html?t=v&u={from_user}&y={youtube_id}&g={topic_name}&l={level}".format(from_user=to_user, youtube_id=row['youtube_id'], topic_name="", level=""),
          title = "{topic_name} - {level}".format(topic_name=topic_name, level=level),
          text = "Keep tapping Watch Now for more coins.",
          delay = delay,
          attribution = custom_attribution("WATCH NOW"),
          keyboards = welcome_keyboard()
        )

  except pymysql.Error as err:
    print("MySQL DB error:%s" % (err))

  finally:
    if conn:
      conn.close()
      
  return _message
  
  

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
    
    kik.send_messages([
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "Chat with millions of players with GameBots! Connect Steam to win daily rewards.",
        type_time = 500,
        keyboards = welcome_keyboard()
      )
    ])
    
  else:
    kik.send_messages([
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "Chat with millions of players with GameBots! Connect Steam to win daily rewards.",
        type_time = 500, 
        delay = 2150
      ),
    ])
    
    default_content_reply(message, random.choice(topic_names), random.choice(topic_levels))
    send_player_help_message(message=message, topic_name=random.choice(topic_names), level=random.choice(topic_levels))
    kik.send_messages([
      LinkMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        pic_url = "https://i.imgur.com/CctmFz0.png",
        url = "http://gamebots.chat/bot.html?t=s&u={from_user}".format(from_user=message.from_user),
        #title = "{topic_name}: {level}".format(topic_name=row['topic_name'], level=row['level']),
        text = "Connect Steam account for more features. (1000 coins)",
        attribution = custom_attribution("CHAT NOW"),
        keyboards = welcome_keyboard()
      )
    ])
    
  modd.utils.send_evt_tracker(category="video-message", action=message.chat_id, label=message.from_user)
  modd.utils.send_evt_tracker(category="player-message", action=message.chat_id, label=message.from_user)
  modd.utils.send_evt_tracker(category="steam-button", action=message.chat_id, label=message.from_user)
  modd.utils.send_evt_tracker(category="message", action=message.chat_id, label=message.from_user)
  
    
  return


def start_help(message):
  print("start_help(message=%s)" % (message))
  modd.utils.send_evt_tracker(category="Session", action=message.chat_id, label=message.from_user)
  
  #-- data obj/ now in active session
  help_convos[message.chat_id] = {
    'chat_id'       : message.chat_id,
    'username'      : message.from_user,
    'game'          : gameHelpList[message.from_user],
    'level'         : message.body,
    'ignore_streak' : 0,
    'started'       : int(time.time()),
    'last_message'  : int(time.time()),
    'idle_timer'    : None,
    'messages'      : [],
    'replies'       : [],
    'im_channel'    : "",
    'session_id'    : 0
  }
  
  
  kik.send_messages([    
    TextMessage(
      to = message.from_user,
      chat_id = message.chat_id,
      body = "Tap below to watch {topic_name} videos & chat with live players.".format(topic_name=help_convos[message.chat_id]['game']),
      type_time = 500
    ),
    message_for_topic_level(message.from_user, message.chat_id, help_convos[message.chat_id]['game'], help_convos[message.chat_id]['level'])
  ])
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur = conn.cursor()

      cur.execute("INSERT INTO `kikbot_sessions` (`username`, `topic_name`, `level`, `chat_id`, `added`) VALUES (%s, %s, %s, %s, UTC_TIMESTAMP())", (message.from_user, help_convos[message.chat_id]['game'], help_convos[message.chat_id]['level'], message.chat_id))
      conn.commit()
      help_convos[message.chat_id]['session_id'] = cur.lastrowid
      cur.close()
      
      player_help_for_topic_level(message.from_user, message.chat_id, gameHelpList[message.from_user], message.body)

  except pymysql.Error as err:
      print("MySQL DB error:%s" % (err))

  finally:
    if conn:
      conn.close()
  
  del gameHelpList[message.from_user]
  modd.utils.slack_send(help_convos[message.chat_id], message.body, message.from_user)
  
  return


def end_help(to_user, chat_id, user_action=True):
  print("end_help(to_user=\'%s\', chat_id=\'%s\', user_action=%d)" % (to_user, chat_id, user_action))
  
  if not user_action:
    kik.send_messages([
      TextMessage(
        to = to_user,
        chat_id = chat_id,
        body = "This %s help session is now closed." % (help_convos[chat_id]['game']),
        type_time = 250,
      )
    ])
  
  if chat_id in help_convos:
    if user_action:
      modd.utils.slack_im(help_convos[chat_id], "Help session closed.")
    
      #-- if timer exists, end it plz
      idle_activity_ends(chat_id, False)
    
    del help_convos[chat_id]
  
  time.sleep(3)
  cancel_session(to_user, chat_id)
  
  return


def cancel_session(to_user, chat_id):
  print("cancel_session(to_user=\'%s\', chat_id=\'%s\')" % (to_user, chat_id))
  
  #-- send to kik user
  kik.send_messages([
    TextMessage(
      to = to_user,
      chat_id = chat_id,
      body = "Ok, Thanks for using GameBots!",
      type_time = 250,
    )
  ])
  
  if to_user in gameHelpList:
    del gameHelpList[to_user]
  
  if chat_id in help_convos:
    del help_convos[chat_id]
  
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
#        kik.send_messages([
#          TextMessage(
#            to = message.from_user,
#            chat_id = message.chat_id,
#            body = "GameBots chat key successfully unlocked. One moment please…",
#            type_time = 500,
#            keyboards = [
#              SuggestedResponseKeyboard(
#                hidden = False,
#                responses = [
#                  TextResponse(u"\U0001F3C6 FREE CS:GO SKIN"),
#                  TextResponse(u"\U0001F46B CHAT NOW"),
#                  TextResponse(u"\U0001F47E GET GAME HELP")
#                ]
#              )
#            ]
#          ),
#        ])
        default_text_reply(message=message)
        
        self.set_status(200)
        return
        
      
      # -=-=-=-=-=-=-=-=- FRIEND PICKER MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, FriendPickerMessage):  
        modd.utils.send_evt_tracker(category="friend", action=message.chat_id, label=message.from_user)
        
        conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
        try:
          with conn.cursor() as cur:
            cur = conn.cursor()
            cur.execute("INSERT IGNORE INTO `kikbot_logs` (`username`, `chat_id`, `body`) VALUES (%s, %s, %s)", (message.from_user, message.chat_id, "__{PICKER}__%s" % (",".join(message.picked).encode('utf-8'))))
            conn.commit()
            cur.close()
          
        except pymysql.Error as err:
            print("MySQL DB error:%s" % (err))
      
        finally:
          if conn:
            conn.close()
            
            
        for friend in message.picked:
          modd.utils.send_evt_tracker(category="friend-picker", action=message.chat_id, label=message.from_user)
          modd.utils.send_evt_tracker(category="message", action=message.chat_id, label=message.from_user)
          modd.utils.send_evt_tracker(category="reply", action=message.chat_id, label=message.from_user)
            
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "One moment..",
            type_time = 500
          )
        ])
        modd.utils.send_evt_tracker(category="message", action=message.chat_id, label=message.from_user)
        
        # response = requests.get("http://api.snapcontacts.pw/kik_user.php?amt={tot}&tick=1".format(tot=20))
        # mentions = ", @".join(response.json())
        # 
        # kik.send_messages([
        #   TextMessage(
        #     to = message.from_user,
        #     chat_id = message.chat_id,
        #     body = "@{mentions}".format(mentions=mentions),
        #     type_time = len(mentions) * 10
        #   )
        # ])
        
      
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
        conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
        try:
          with conn.cursor() as cur:
            cur = conn.cursor()
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
        self.set_status(200)
        return
        
      
      # -=-=-=-=-=-=-=-=- TEXT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, TextMessage):
        print("=-= TextMessage =-= ")
        
        # -=-=-=-=-=-=-=-=-=- MENTIONS -=-=-=-=-=-=-=-=-
        if message.mention is not None:
          if message.body == "Start Chatting":
            modd.utils.send_evt_tracker(category="Subscribe", action=message.chat_id, label=message.from_user)
            
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
        
        # -=-=-=-=-=-=-=-=-=- END SESSION -=-=-=-=-=-=-=-
        if message.body.lower() == "!end" or message.body.lower() == "cancel" or message.body.lower() == "quit":
          print("-=- ENDING HELP -=-")
          end_help(message.from_user, message.chat_id)
          self.set_status(200)
          return
        
          
        #-- reset timeout
        #if message.chat_id in help_convos:
        #  annul_idle_activity(message.chat_id)
        
        
        # -=-=-=-=-=-=-=-=- DEFAULT TOPIC BTNS -=-=-=-=-=-=-=-=-
        if message.body in topic_names:
          if message.from_user not in gameHelpList:
            modd.utils.send_evt_tracker(category="{topic_name}-select".format(topic_name=message.body), action=message.chat_id, label=message.from_user)
            modd.utils.send_evt_tracker(category="message", action=message.chat_id, label=message.from_user)
            modd.utils.send_evt_tracker(category="reply", action=message.chat_id, label=message.from_user)
            
            gameHelpList[message.from_user] = message.body
          
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Select Level...",
                type_time = 500,
                keyboards = levels_keyboard()
              )
            ])
          
          self.set_status(200)
          return
        
        
        
        
        
          
        # -=-=-=-=-=-=-=-=- WATCH NOW BTN -=-=-=-=-=-=-=-=-
        if message.body == "Next Video (50 coins)":
          modd.utils.send_evt_tracker(category="video-message", action=message.chat_id, label=message.from_user)
          # topic_level = topic_level_for_chat_id(message.chat_id)
          # if topic_level is not None:
          # default_content_reply(message, topic_level['topic'], topic_level['level'])
          default_content_reply(message, random.choice(topic_names), random.choice(topic_levels))
          
          self.set_status(200)
          return
          
          
        # -=-=-=-=-=-=-=-=- CHAT NOW BTN -=-=-=-=-=-=-=-=-
        if message.body == "Next Player (100 coins)":
          modd.utils.send_evt_tracker(category="player-message", action=message.chat_id, label=message.from_user)
          
          if message.chat_id in help_convos:
            send_player_help_message(message=message, topic_name=help_convos[message.chat_id]['game'], level=help_convos[message.chat_id]['level'])
            # player_help_for_topic_level(username=message.from_user, chat_id=message.chat_id, topic_name=help_convos[message.chat_id]['game'], level=help_convos[message.chat_id]['level'])
            
          else:
            send_player_help_message(message=message, topic_name=random.choice(topic_names), level=random.choice(topic_levels))
            # player_help_for_topic_level(username=message.from_user, chat_id=message.chat_id, topic_name="Hearthstone", level="Intro")
            
            
          self.set_status(200)
          return
          

        # -=-=-=-=-=-=-=-=- STEAM BTN -=-=-=-=-=-=-=-=-
        if message.body == "Steam (1000 coins)":
          modd.utils.send_evt_tracker(category="steam-button", action=message.chat_id, label=message.from_user)
          
          kik.send_messages([
            LinkMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              pic_url = "https://i.imgur.com/CctmFz0.png",
              url = "http://gamebots.chat/bot.html?t=s&u={from_user}".format(from_user=message.from_user),
              title = "Sign in through Stream",
              text = "Connect Steam to win 1000 coins & access daily rewards",
              attribution = custom_attribution("SIGN IN"),
              keyboards = welcome_keyboard()
            )
          ])
          
          self.set_status(200)
          return
          
          
            
            
            
        # -=-=-=-=-=-=-=-=- LEVEL GAME BTNS -=-=-=-=-=-=-=-=-    
        elif message.body in topic_levels:
          if message.from_user in gameHelpList:
            modd.utils.send_evt_tracker(category="{level}-select".format(level=message.body), action=message.chat_id, label=message.from_user)
            modd.utils.send_evt_tracker(category="message", action=message.chat_id, label=message.from_user)
            modd.utils.send_evt_tracker(category="reply", action=message.chat_id, label=message.from_user)
            start_help(message)
            
          self.set_status(200)
          return
        
                  
        # -=-=-=-=-=-=-=-=- CHAT NOW BTN -=-=-=-=-=-=-=-=-      
        elif message.body == "Pick 3 Friends" or message.body == "Share":
          modd.utils.send_evt_tracker(category="reply", action=message.chat_id, label=message.from_user)
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Help our community grow. Pick friends.",
              type_time = 250,
              keyboards = default_friend_picker()
            )
          ])
          
          self.set_status(200)
          return
          
          
        # -=-=-=-=-=-=-=-=- ANOTHER TOPIC VIDEO BTN -=-=-=-=-=-=-=-=-      
        elif message.body == u"\U0001F4FA ANOTHER CLIP":
          modd.utils.send_evt_tracker(category="video-message", action=message.chat_id, label=message.from_user)
          
          topic_level = topic_level_for_chat_id(message.chat_id)
          if topic_level is not None:
            default_content_reply(message, topic_level['topic'], topic_level['level'])
                    
          self.set_status(200)
          return
          
          
        # -=-=-=-=-=-=-=-=- CHAT W/ PLAYER BTN -=-=-=-=-=-=-=-=-      
        elif message.body == u"\U0001F46B CHAT NOW":
          modd.utils.send_evt_tracker(category="player-message", action=message.chat_id, label=message.from_user)
          modd.utils.send_evt_tracker(category="chat", action=message.chat_id, label=message.from_user)
          
          if message.chat_id in help_convos:
            send_player_help_message(message=message, topic_name=help_convos[message.chat_id]['game'], level=help_convos[message.chat_id]['level'])
            player_help_for_topic_level(username=message.from_user, chat_id=message.chat_id, topic_name=help_convos[message.chat_id]['game'], level=help_convos[message.chat_id]['level'])
            
          else:
            send_player_help_message(message=message, topic_name="Hearthstone", level="Intro")
            player_help_for_topic_level(username=message.from_user, chat_id=message.chat_id, topic_name="Hearthstone", level="Intro")
            
          self.set_status(200)
          return
        
        
        # -=-=-=-=-=-=-=-=- GAME HELP BTN -=-=-=-=-=-=-=-=-
        elif message.body == u"\U0001F47E GET GAME HELP" or message.body == "No Thanks":
          modd.utils.send_evt_tracker(category="no-thanks", action=message.chat_id, label=message.from_user)
          default_text_reply(message=message)
          self.set_status(200)
          return
          
          
        # -=-=-=-=-=-=-=-=- CS:GO SKIN BTN -=-=-=-=-=-=-=-=-
        elif message.body == u"\U0001F3C6 FREE CS:GO SKIN":
          modd.utils.send_evt_tracker(category="reward", action=message.chat_id, label=message.from_user)
          
          kik.send_messages([
            PictureMessage(
              to = message.from_user, 
              chat_id = message.chat_id,
              pic_url = "http://i.imgur.com/N7YDEqH.png",
              keyboards = default_friend_picker(),
              attribution = custom_attribution("Invite 5 friends to claim reward."), 
            )
          ])
          self.set_status(200)
          return
          
        
        # -=-=-=-=-=-=-=-=- RELOAD BOT BTN -=-=-=-=-=-=-=-=-
        elif message.body == "Reload Bot":
          if message.from_user in gameHelpList:
            del gameHelpList[message.from_user]
            
          if message.chat_id in help_convos:
            del help_convos[message.chat_id]
          
          welcome_intro_seq(message)
          self.set_status(200)
          return
        
        
        
        # -=-=-=-=-=-=-=-=-=- FAQ BUTTONS -=-=-=-=-=-=-=-=-=-
        elif message.body == "More Details":
          if message.chat_id in help_convos:
            faq_arr = fetch_faq(help_convos[message.chat_id]['game'])
            print("faq_arr:%s" % (faq_arr))
            
            messages = []
            for entry in faq_arr:
              messages.append(
                TextMessage(
                  to = message.from_user, 
                  chat_id = message.chat_id,
                  body = entry, 
                  type_time = 2500
                )
              )
              
              #-- only get 2 max
              if len(messages) == 2:
                break;
                
            
            # send 0ff first faq element
            kik.send_messages([
              messages[0]
            ])
            
            time.sleep(2)
            end_help(message.from_user, message.chat_id)
                          
          
          #-- gimme outta here
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
            
            self.set_status(200)
            return
            
          
          
          # -=-=-=-=-=-=-=-=-=- CONTIUNE SESSION -=-=-=-=-=-=-=-
          else:
          
            #-- respond with waiting msg
            topic_level = topic_level_for_chat_id(message.chat_id)
            if topic_level is not None:
              default_content_reply(message, topic_level['topic'], topic_level['level'])
            
            #-- route to slack api, guy
            modd.utils.slack_im(help_convos[message.chat_id], message.body)
          
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


class TopicNotify(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

  def post(self):
    print("=-=-=-=-=-=-=-=-=-=-= TOPIC NOTIFY =-=-=-=-=-=-=-=-=-=-=")
    print("self.request.body:{request_body}".format(request_body=self.request.body))

    chat_id = self.get_argument('chat_id', "")
    if self.get_argument('token', "") == Const.NOTIFY_TOKEN:
      
      
      topic_level = topic_level_for_chat_id(chat_id)
      if topic_level is not None:
        kik.send_messages([
          message_for_topic_level(topic_level['username'], chat_id, topic_level['topic'], topic_level['level'], delay=0)
        ])
        
      self.set_status(200)
      
    else:
      self.set_status(403)
      
    return
    

# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class ConnectPlayer(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

  def post(self):
    print("=-=-=-=-=-=-=-=-=-=-= CONNECT PLAYER =-=-=-=-=-=-=-=-=-=-=")
    print("self.request.body:{request_body}".format(request_body=self.request.body))

    chat_id = self.get_argument('chat_id', "")
    to_user = self.get_argument('to_user', "")
    
    if self.get_argument('token', "") == Const.CONNECT_TOKEN:
      kik.send_messages([
        PictureMessage(
          to = to_user,
          chat_id = chat_id,
          pic_url = "http://profilepics.kik.com/acV09p0BEgu3dBSU7MdAJh-3pMs/orig.jpg",
          
          attribution = CustomAttribution(
            name = "Chat now", 
            icon_url = "http://gamebots.chat/img/icon/favicon-96x96.png"
          )
        ),
        TextMessage(
          to = to_user,
          chat_id = chat_id,
          body = "I am new to Overwatch, can someone help?\nkik.me/alexamaria.i?s=1"
        )
      ])
        
      self.set_status(200)
      
    else:
      self.set_status(403)
      
    return
    

# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class Slack(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
  
  def post(self):
    print("=-=-=-=-=-=-=-=-=-=-= SLACK RESPONSE =-=-=-=-=-=-=-=-=-=-= @%d\n%s" % (int(time.time()), self.get_argument('text', "")))
    
    if self.get_argument('token', "") == Const.SLACK_TOKEN:
      _arr = self.get_argument('text', "").split(' ')
      _arr.pop(0)
      
      chat_id = _arr[0]
      _arr.pop(0)
      
      message = " ".join(_arr).replace("'", "")
      to_user = ""
      
      if chat_id in help_convos:
        conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
        try:
          with conn.cursor() as cur:
            cur.execute("SELECT `username`, `body` FROM `kikbot_logs` WHERE `chat_id` = %s ORDER BY `added` DESC LIMIT 1;", (chat_id))
    
            if cur.rowcount == 1:
              row = cur.fetchone()
      
              print("help_convos:%s" % (help_convos))
              
              help_convos[chat_id]['ignore_streak'] = -1
              to_user = row['username']
      
              if message == "!end" or message.lower() == "cancel" or message.lower() == "quit":
                print("-=- ENDING HELP -=-")
                end_help(to_user, chat_id, False)
      
              else:
                help_convos[chat_id]['replies'].append(message)
                #annul_idle_activity(chat_id)
          
                kik.send_messages([
                  TextMessage(
                    to = to_user,
                    chat_id = chat_id,
                    body = "%s player:\n%s" % (help_convos[chat_id]['game'], message),
                    type_time = 250
                  )
                ])
    
        except pymysql.Error as err:
          print("MySQL DB error:%s" % (err))
  
        finally:
          if conn:
            conn.close()
    
    self.set_status(200)
    return


# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class InstantMessage(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
  
  def post(self):
    print("=-=-=-=-=-=-=-=-=-=-= SLACK IM =-=-=-=-=-=-=-=-=-=-=")
    data = tornado.escape.json_decode(self.request.body)
    print("payload:%s -(%d)" % (data, data['chat_id'] in help_convos))
    
    if data['chat_id'] in help_convos:
      help_convos[data['chat_id']]['im_channel'] = data['channel']
    
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
    
    if self.get_argument('token', "") == Const.BROADCAST_TOKEN:
      kik.send_messages([
        PictureMessage(
          to = self.get_argument('username', ""),
          chat_id = self.get_argument('chat_id', ""),
          pic_url = self.get_argument('img_url', ""),
          keyboards = default_friend_picker(),
          attribution = CustomAttribution(
            name = self.get_argument('attribution', ""), 
            icon_url = "http://gamebots.chat/img/icon/favicon-96x96.png"
          )
        )
      ])
        
      self.set_status(200)
        
    else:
      self.set_status(403)
    
    return
    
    


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



gameHelpList = {}
help_convos = {}


#Const.KIK_API_CONFIG = {
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
    'receiveDeliveryReceipts' : True,
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
#     'receiveDeliveryReceipts' : True,
#     'receiveReadReceipts'     : True
#   }
# }




# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #
# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #




#-=:=- Start + Config Kik -=:=-#
#-=:=--=:=--=:=--=:=--=:=--=:=--=:=--=:=--=:=--=:=-#

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
  (r"/topic-notify", TopicNotify),
  (r"/connect-player", ConnectPlayer),
  (r"/message", Message),
  (r"/slack", Slack),
  (r"/im", InstantMessage)
])


#-- server starting
if __name__ == "__main__":
  application.listen(int(Const.KIK_API_CONFIG['WEBHOOK']['PORT']))
  tornado.ioloop.IOLoop.instance().start()
  print("tornado start" % (int(time.time())))
