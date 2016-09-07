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

Const.DB_HOST = 'external-db.s4086.gridserver.com'
Const.DB_NAME = 'db4086_modd'
Const.DB_USER = 'db4086_modd_usr'
Const.DB_PASS = 'f4zeHUga.age'

Const.MAX_REPLIES = 4
Const.INACTIVITY_THRESHOLD = 8000


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



#--:-- Message UI / Message Part Factories --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def topics_keyboard():
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = False,
      responses = [
        #TextResponse("Pokémon Go"),
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


def default_friend_picker(min=1, max=5, message="Pick some friends!"):
  keyboard = [
    SuggestedResponseKeyboard(
      responses = [
        FriendPickerResponse(
          body = message,
          min = min,
          max = max
        ),
        TextResponse("Cancel")
      ]
    )
  ]
  
  return keyboard
  
  
def default_attribution():
  attribution = CustomAttribution(
    name = "gamebots.chat", 
    icon_url = "http://gamebots.chat/img/icon/favicon-32x32.png"
  )
  
  return attribution
  

def default_text_reply(message, delay=0, type_time=500):
  print("default_text_reply(message=%s)" % (message))
  
  return TextMessage(
    to = message.from_user,
    chat_id = message.chat_id,
    body = "Select a game that you need help with. Type cancel anytime to end this conversation.",
    keyboards = topics_keyboard(),
    type_time = type_time,
    delay = delay
  )


def default_wait_reply(message):
  print("default_wait_reply(message=%s)" % (message))
  
  topic_name = ""
  if message.from_user in gameHelpList:
    topic_name = gameHelpList[message.from_user]

  
  if message.chat_id in help_convos:
    topic_name = help_convos[message.chat_id]['game']

  
  if len(topic_name) == 0:
    return TextMessage(
      to = message.from_user,
      chat_id = message.chat_id,
      body = "Your message has been receieved, but we don't know what to make of it. Try something else.",
      type_time = 500
    )
  
  else:
    return TextMessage(
      to = message.from_user,
      chat_id = message.chat_id,
      body = "Your message has been routed to the {topic_name} coaches and is in queue to be answered shortly.".format(topic_name=topic_name),
      type_time = 500
    )

 

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


def message_for_topic_level(message, topic_name, level="Intro"):
  print("message_for_topic_level(message={message}, topic_name={topic_name}, level={level})".format(message=message, topic_name=topic_name, level=level))
  
  _message = TextMessage(
    to = message.from_user,
    chat_id = message.chat_id,
    body = "No content found for {topic_name}".format(topic_name=topic_name),
    type_time = 500
  )
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur.execute("SELECT `image_url`, `video_url` FROM `topic_content` WHERE `topic_name` = %s AND `level` = %s LIMIT 1;", (topic_name, level))

      if cur.rowcount == 1:
        row = cur.fetchone()
        
        print("row[]={row}".format(row=row))
        _message = LinkMessage(
          to = message.from_user,
          chat_id = message.chat_id,
          title = "{topic_name} - {level}".format(topic_name=topic_name, level=level),
          pic_url = row['image_url'],
          url = row['video_url'],
          attribution = default_attribution(),
          keyboards = [
            SuggestedResponseKeyboard(
              hidden = False,
              responses = [
                TextResponse("Another Clip"),
                TextResponse("Enter Server"),
                TextResponse("No Thanks")
              ]
            )
          ]
        )

  except pymysql.Error as err:
    print("MySQL DB error:%s" % (err))

  finally:
    if conn:
      conn.close()
      
  modd.utils.send_evt_tracker(action="Video Sent", label=message.chat_id)
  return _message
  


#--:-- Idle Activity timeout --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def idle_activity_timer_starts(chat_id, is_selfOffing=False):
  print("on_idle_timer(chat_id={chat_id}, is_selfOffing={is_selfOffing})".format(chat_id=chat_id, is_selfOffing=False))

  #-- if timer exists, end it plz
  idle_activity_ends(chat_id, is_selfOffing)
  
  #-- remake a new idle timer
  t = threading.Timer(Const.INACTIVITY_THRESHOLD, idle_activity_ends, [chat_id]).start()
  help_convos[chat_id]['last_message'] = datetime.now()
  help_convos[chat_id]['idle_timer'] = t
  
  s_epoch = epoch(time.time()).shift('US/Pacific').epoch
  help_convos[chat_id]['s_epoch'] = s_epoch
  help_convos[chat_id]['h_epoch'] = s_epoch
    
  self.set_status(200)
  return


def idle_activity_tics(chat_id):
  print("idle_activity_tics(chat_id={chat_id})".format(chat_id=chat_id))
  
  #-- exists
  if chat_id in help_convos:
    
    #-- epoch updates
    t_epoch = epoch(time.time()).shift('US/Pacific').epoch
    help_convos[chat_id]['t_epoch'] = t_epoch
    
    #-- past the limit, end it!
    if (help[convos[chat_id]['s_epoch']] - t_epoch) + Const.INACTIVITY_THRESHOLD < t_epoch:
      idle_activity_ends(chat_id)
      
  # self.set_status(200)
  return
    
  
def idle_activity_timer_restarts(chat_id, is_selfOffing=False):
  print("idle_activity_timer_restarts(chat_id={chat_id}, is_selfOffing={is_selfOffing})".format(chat_id=chat_id, is_selfOffing=False))

  #-- if timer exists, end it plz 
  idle_activity_ends(chat_id, is_selfOffing)

  #-- remake a new idle timer
  if chat_id in helpConvos:
    s_epoch = epoch(time.time()).shift('US/Pacific').epoch
    t = threading.Timer(Const.INACTIVITY_THRESHOLD, idle_activity_tics, [chat_id]).start()
    
    help_convos[chat_id]['idle_timer'] = t
    help_convos[chat_id]['s_epoch'] = s_epoch
    help_convos[chat_id]['h_epoch'] = s_epoch
    
  # self.set_status(200)
  return s_epoch
  
  
  
def idle_activity_ends(chat_id, is_selfOffing=True):
  print("idle_activity_ends(chat_id={chat_id}, is_selfOffing={is_selfOffing})".format(chat_id=chat_id, is_selfOffing=is_selfOffing))
  
  if chat_id in help_convos:
    if help_convos[chat_id]['idle_timer'] is not None:
      t = help_convos[chat_id]['idle_timer']
      t.cancel()
      
      
    if is_selfOffing:
      modd.utils.slack_im(help_convos[chat_id], "I've seem to have gone idle… connected for ")
      
      #-- skipp actually ending it
      #//end_chat(c)
      
  # self.set_status(200)
  return
  
  
  

#--:-- Session Subpaths / In-Session Seqs --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def welcome_intro_seq(message, is_mention=False):
  print("welcome_intro_seq(message=%s, is_mention=%d)" % (message, is_mention))
  
  if is_mention:
    print("MENTION PARTICIPANT:%s" % (message.participants[-1]))
    
    kik.send_messages([
      VideoMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        video_url = "http://app5.kikphotos.pw/gamebots-00.mp4"
      ),
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "Tap REPLY to start chatting.",
        keyboards = [
          SuggestedResponseKeyboard(
            hidden = False,
            responses = [
              TextResponse("Start Chatting")
            ]
          )
        ],
        type_time = 500,
        delay = 2750
      )
    ])
    
  else:
    kik.send_messages([
      VideoMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        video_url = "http://app5.kikphotos.pw/gamebots-00.mp4"
      ),
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "Welcome to GameBots! - Super fast chat help for gamers! Select a game that you need help with...",
        type_time = 1275, 
        delay = 2750,
        keyboards = topics_keyboard()
      )
    ])
    
  modd.utils.send_evt_tracker(action="Sent", label=message.chat_id)
  return


def start_help(message):
  print("start_help(message=%s)" % (message))
  
  modd.utils.send_evt_tracker(action="Session", label=message.chat_id)
  
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
  
  
  conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
  try:
    with conn.cursor() as cur:
      cur = conn.cursor()

      cur.execute("INSERT INTO `kikbot_sessions` (`username`, `topic_name`, `level`, `chat_id`, `added`) VALUES (%s, %s, %s, %s, NOW())", (message.from_user, help_convos[message.chat_id]['game'], help_convos[message.chat_id]['level'], message.chat_id))
      conn.commit()
      help_convos[message.chat_id]['session_id'] = cur.lastrowid
      cur.close()

  except pymysql.Error as err:
      print("MySQL DB error:%s" % (err))

  finally:
    if conn:
      conn.close()
      
  kik.send_messages([    
    TextMessage(
      to = message.from_user,
      chat_id = message.chat_id,
      body = "Locating %s coaches..." % (help_convos[message.chat_id]['game']),
      type_time = 250,
      delay = 1500
    ),
    message_for_topic_level(message, help_convos[message.chat_id]['game'], help_convos[message.chat_id]['level'])
    # TextMessage(
    #   to = message.from_user,
    #   chat_id = message.chat_id,
    #   body = "Pro tip: Keep asking questions, each will be added to your queue! Type Cancel to end the conversation.",
    #   type_time = 1500,
    #   delay = 1500
    # )
  ])
  modd.utils.send_evt_tracker(action="Sent", label=message.chat_id)
  
  
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
    modd.utils.send_evt_tracker(action="Sent", label=chat_id)
  
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
  modd.utils.send_evt_tracker(action="Sent", label=chat_id)
  
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
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "I'm sorry, I cannot understand that type of message.",
            type_time = 250
          ),
          default_text_reply(message=message)
        ])
        modd.utils.send_evt_tracker(action="Sent", label=message.chat_id)
        
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
        
        modd.utils.send_evt_tracker(action="Read", label=message.chat_id)
        self.set_status(200)
        return
         
      
      # -=-=-=-=-=-=-=-=- START CHATTING -=-=-=-=-=-=-=-=-
      elif isinstance(message, StartChattingMessage):
        print("-= StartChattingMessage =-= ")
        
        modd.utils.send_evt_tracker(action="Start Chat", label=message.chat_id)
        welcome_intro_seq(message)
        self.set_status(200)
        return
        
      
      # -=-=-=-=-=-=-=-=- TEXT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, TextMessage):
        print("=-= TextMessage =-= ")
        
        # -=-=-=-=-=-=-=-=-=- MENTIONS -=-=-=-=-=-=-=-=-
        if message.mention is not None:
          if message.body == "Start Chatting":
            modd.utils.send_evt_tracker(action="Subscribe", label=message.chat_id)
            
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
        
        
          modd.utils.send_evt_tracker(action="Reply", label=message.chat_id)
          
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
            modd.utils.send_evt_tracker(action="Subscribe", label=message.chat_id)
            
            gameHelpList[message.from_user] = message.body
          
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "What level are you on?",
                type_time = 500,
                keyboards = levels_keyboard()
              )
            ])
            modd.utils.send_evt_tracker(action="Sent", label=message.chat_id)
          
          self.set_status(200)
          return
            
            
        # -=-=-=-=-=-=-=-=- LEVEL GAME BTNS -=-=-=-=-=-=-=-=-    
        elif message.body in topic_levels:
          if message.from_user in gameHelpList:
            modd.utils.send_evt_tracker(action="Button", label=message.chat_id)
            start_help(message)
            
          self.set_status(200)
          return
          
          
        # -=-=-=-=-=-=-=-=- ANOTHER TOPIC VIDEO BTN -=-=-=-=-=-=-=-=-      
        elif message.body == "Another Clip":
          if message.chat_id in help_convos:
            modd.utils.send_evt_tracker(action="Button", label=message.chat_id)
            kik.send_messages([    
              message_for_topic_level(message, help_convos[message.chat_id]['game'], help_convos[message.chat_id]['level'])
            ])
            modd.utils.send_evt_tracker(action="Sent", label=message.chat_id)
          
          self.set_status(200)
          return
        
        
        # -=-=-=-=-=-=-=-=- GAME SERVER BTN -=-=-=-=-=-=-=-=-
        elif message.body == "Enter Server":
          if message.chat_id in help_convos:
            modd.utils.send_evt_tracker(action="Button", label=message.chat_id)
            modd.utils.send_evt_tracker(action="Sent", label=message.chat_id)
            
          self.set_status(200)
          return
          
        
        # -=-=-=-=-=-=-=-=- RELOAD BOT BTN -=-=-=-=-=-=-=-=-
        elif message.body == "Reload Bot":
          if message.from_user in gameHelpList:
            modd.utils.send_evt_tracker(action="Button", label=message.chat_id)
            del gameHelpList[message.from_user]
            
          if message.chat_id in help_convos:
            del help_convos[message.chat_id]
          
          welcome_intro_seq(message)
          self.set_status(200)
          return
        
        
        
        # -=-=-=-=-=-=-=-=-=- FAQ BUTTONS -=-=-=-=-=-=-=-=-=-
        elif message.body == "More Details":
          if message.chat_id in help_convos:
            modd.utils.send_evt_tracker(action="Button", label=message.chat_id)
            faq_arr = fetch_faq(help_convos[message.chat_id]['game'])
            print("faq_arr:%s" % (faq_arr))
            
            messages = []
            for entry in faq_arr:
              messages.append(
                TextMessage(
                  to = message.from_user, chat_id = message.chat_id,
                  body = entry, type_time = 2500, delay = 0
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
            #kik.send_messages([default_wait_reply(message)])

            
            #-- route to slack api, guy
            modd.utils.send_evt_tracker(action="Reply", label=message.chat_id)
            modd.utils.slack_im(help_convos[message.chat_id], message.body)
            
            self.set_status(200)
            return
          
          self.set_status(200)
          return
          
          
          
        # -=-=-=-=-=-=-=-=- BUTTON PROMPT -=-=-=-=-=-=-=-=
        #-- anything else, prompt with 4 topics
        if len(gameHelpList) == 0 and len(help_convos) == 0:
          kik.send_messages([
            default_text_reply(message=message)
          ])
          modd.utils.send_evt_tracker(action="Sent", label=message.chat_id)
          
          self.set_status(200)
          return
        
      self.set_status(200)
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
                    body = "%s coach:\n%s" % (help_convos[chat_id]['game'], message),
                    type_time = 250
                  )
                ])
                modd.utils.send_evt_tracker(action="Sent", label=message.chat_id)
    
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
    username = self.get_body_argument('recipient', "")
    body = self.get_body_argument('body', "")
    url = self.get_body_argument('url', "")
    image_url = self.get_body_argument('image_url', "")
    video_url = self.get_body_argument('video_url', "")
    message_type = self.get_body_argument('type', "")
    message_method = self.get_body_argument('method', "")
    
    conn = pymysql.connect(host=Const.DB_HOST, user=Const.DB_USER, password=Const.DB_PASS, db=Const.DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor);
    try:
      with conn.cursor() as cur:
        cur.execute("SELECT `chat_id` FROM `kikbot_logs` WHERE `username` = '%s' ORDER BY `added` DESC LIMIT 1;" % (username))

        if cur.rowcount == 1:
          row = cur.fetchone()
  
          print("RECIPIENT: %s (%s)" % (username, row['chat_id']))
          if message_type == "TextMessage":
            print("BODY : %s" % (body))
            kik_message = TextMessage(
              to = username,
              chat_id = row['chat_id'],
              body = body
            )

          elif message_type == "LinkMessage":
            print("BODY : %s" % (body))
            print("IMG_URL : %s" % (image_url))
            print("URL : %s" % (url))
            kik_message = LinkMessage(
              to = username,
              chat_id = row['chat_id'],
              title = body,
              pic_url = image_url,
              url = url,
              attribution = CustomAttribution(
                name = 'gamebots.chat', 
                icon_url = 'http://gamebots.chat/img/icon/favicon-32x32.png'
              )
            )

          elif message_type == "VideoMessage":
            print("ID_URL : " % (video_url))
            kik_message = VideoMessage(
              to = username,
              chat_id = row['chat_id'],
              video_url = video_url,
              autoplay = False,
              muted = False,
              loop = False
            )

          kik.send_messages([kik_message])
          
    except pymysql.Error as err:
      print("MySQL DB error:%s" % (err))

    finally:
      if conn:
        conn.close()
        
    self.set_status(200)
    return



#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



gameHelpList = {}
help_convos = {}


#Const.KIK_API_CONFIG = {
#   'USERNAME' : "streamcard",
#   'API_KEY'  : "aa503b6f-dcda-4817-86d0-02cfb110b16a",
#   'WEBHOOK'  : {
#     'HOST' : "http://76.102.12.47",
#     'PORT' : 8080,
#     'PATH' : "kik"
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
    'PATH'  : "kik"
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
#     'HOST'  : "http://76.102.12.47",
#     'PORT'  : 8080,
#     'PATH'  : "kik"
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
  # (r"/kikNotify", Notify),
  # (r"/notify", Notify),`
  (r"/message", Message),
  (r"/slack", Slack),
  (r"/im", InstantMessage)
])


#-- server starting
if __name__ == "__main__":
  application.listen(int(Const.KIK_API_CONFIG['WEBHOOK']['PORT']))
  tornado.ioloop.IOLoop.instance().start()
  print("tornado start" % (int(time.time())))
