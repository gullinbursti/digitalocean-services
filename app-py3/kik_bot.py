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

def default_keyboard():
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = False,
      responses = [
        #TextResponse("Become a Moderator"),
        TextResponse("Pokémon Go"),
        TextResponse("Dota 2"),
        TextResponse("League of Legends"),
        #TextResponse("CS:GO"),
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
  

def default_text_reply(message, delay=0, type_time=500):
  print("default_text_reply(message=%s)" % (message))
  
  return TextMessage(
    to = message.from_user,
    chat_id = message.chat_id,
    body = "Select a game that you need help with. Type cancel anytime to end this conversation.",
    keyboards = default_keyboard(),
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

def fetch_topics():
  print("fetch_topics()")
  _arr = []
  
  try:
    conn = sqlite3.connect("%s/data/sqlite3/kikbot.db" % (os.getcwd()))
    c = conn.cursor()
    c.execute("SELECT display_name FROM topics WHERE enabled = 1;")
    
    for row in c.fetchall():
      _arr.append(row[0])
      key_name = re.sub( '\s+', "_", row[0])
      print("UTF-8 ENCODED : [%s]" % (quote(row[0].key_name.encode('utf-8')).toLower()))
    
    conn.close()
  
  except:
    pass
  
  finally:
    pass
  
  print("_arr:%s" % (_arr))
  return _arr
  

def fetch_slack_webhooks():
  print("fetch_slack_webhooks()")
  _obj = {}
  
  try:
    conn = sqlite3.connect("%s/data/sqlite3/kikbot.db" % (os.getcwd()))
    c = conn.cursor()
    c.execute("SELECT topics.display_name, slack_channels.channel_name, slack_channels.webhook FROM slack_channels INNER JOIN topics ON topics__slack_channels.slack_channel_id = topics.id INNER JOIN topics__slack_channels ON topics__slack_channels.topic_id = topics.id AND topics__slack_channels.slack_channel_id = slack_channels.id WHERE slack_channels.enabled = 1;")
    
    for row in c.fetchall():
      _obj[row[0]] = {
        'channel_name'  : row[1],
        'webhook'       : row[2]
      }
    
    conn.close()
  
  except:
    pass
  
  finally:
    pass
  
  print("_obj:%s" % (_obj))
  return _obj
  

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
  
  modd.utils.send_evt_tracker(action="welcome", label=message.chat_id)
  
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
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "Welcome to GameBots! - Super fast chat help for gamers! Select a game that you need help with...",
        type_time = 333, 
      ), 
      default_text_reply(message=message, delay=2500)
    ])

  return


def start_help(message):
    print("start_help(message=%s)" % (message))
    modd.utils.send_evt_tracker(action="question", label=message.chat_id)
    gameHelpList[message.from_user] = message.body
    
    kik.send_messages([
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "What level are you on?",
        type_time = 500,
        keyboards = [
          SuggestedResponseKeyboard(
            hidden = False,
            responses = [
              TextResponse("Level 1"),
              TextResponse("Level 2-6"),
              TextResponse("Level 7-15"),
              TextResponse("Level 16+"),
              TextResponse("Cancel")
            ]
          )
        ]
      )
    ])
    
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
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "I'm sorry, I cannot understand that type of message.",
            type_time = 250
          ),
          default_text_reply(message=message)
        ])
        
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
        
        modd.utils.send_evt_tracker(action="read", label=message.chat_id)
        self.set_status(200)
        return
         
      
      # -=-=-=-=-=-=-=-=- START CHATTING -=-=-=-=-=-=-=-=-
      elif isinstance(message, StartChattingMessage):
        print("-= StartChattingMessage =-= ")
        
        welcome_intro_seq(message)
        self.set_status(200)
        return
        
      
      # -=-=-=-=-=-=-=-=- TEXT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, TextMessage):
        print("=-= TextMessage =-= ")
        
        # -=-=-=-=-=-=-=-=-=- MENTIONS -=-=-=-=-=-=-=-=-
        if message.mention is not None:
          if message.body == "Start Chatting":
            modd.utils.send_evt_tracker(action="reply", label=message.chat_id)
            
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
          
              #cur.execute("INSERT IGNORE INTO `kikbot_logs` (`username`, `chat_id`, `body`) VALUES (\'%s\', \'%s\', \'%s\')" % (message.from_user, message.chat_id, quote(message.body.encode('utf-8'))))
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
          
        
        # -=-=-=-=-=-=-=-=-=- END SESSION -=-=-=-=-=-=-=-
        if message.body.lower() == "!end" or message.body.lower() == "cancel" or message.body.lower() == "quit":
          print("-=- ENDING HELP -=-")
          end_help(message.from_user, message.chat_id)
          self.set_status(200)
          return
        
          
        #-- reset timeout
        #if message.chat_id in help_convos:
        #  annul_idle_activity(message.chat_id)
        
        
        if message.body == "Become a Moderator":
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "Great, we'll get back to you",
            type_time = 500
          )
          
          if message.chat_id in help_convos:
            del help_convos[message.chat_id]
            
          self.set_status(200)
          return
        
        
        # -=-=-=-=-=-=-=-=- DEFAULT GAME BTNS -=-=-=-=-=-=-=-=-
        if message.body == "Pokémon Go" or message.body == "CS:GO" or message.body == "Dota 2" or message.body == "League of Legends":
          if len(gameHelpList) == 0:
            #modd.utils.send_evt_tracker(action="signup", label=message.chat_id)
            modd.utils.send_evt_tracker(action="opengame", label=message.body)
            start_help(message)
            
            print("SUBSCRIBING \"%s\" TO \"%s\" --> %s" % (message.from_user, quote(message.body.lower().encode('utf-8')), message.chat_id))
            
            
            _sub = urllib.request.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=%s&username=%s&cid=%s' % (quote(message.body.lower().encode('utf-8')), message.from_user, message.chat_id))
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
          modd.utils.send_evt_tracker(action="subscribe", label=message.chat_id)
          
          
          #-- data obj/ now in active session
          help_convos[message.chat_id] = {
            'chat_id'       : message.chat_id,
            'username'      : message.from_user,
            'game'          : gameHelpList[message.from_user],
            'ignore_streak' : 0,
            'started'       : int(time.time()),
            'last_message'  : int(time.time()),
            'idle_timer'    : None,
            'messages'      : [],
            'replies'       : [],
            'im_channel'    : ""
          }

          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Locating %s coaches..." % (gameHelpList[message.from_user]),
              type_time = 250
            ),
            
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Pro tip: Keep asking questions, each will be added to your queue! Type Cancel to end the conversation.",
              type_time = 1500,
              delay = 1500
            )
          ])
          
          
          modd.utils.slack_send(help_convos[message.chat_id], message.body, message.from_user)
          
          del gameHelpList[message.from_user]
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
            kik.send_messages([default_wait_reply(message)])

            
            #-- route to slack api, guy
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
          #cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute("SELECT `username`, `body` FROM `kikbot_logs` WHERE `chat_id` = %s ORDER BY `added` DESC LIMIT 1;", (chat_id))
    
            if cur.rowcount == 1:
              row = cur.fetchone()
      
              print("help_convos:%s" % (help_convos))
              
              help_convos[chat_id]['ignore_streak'] = -1
              to_user = row['username']
      
              #print "to_user=%s, to_user=%s, chat_id=%s, message=%s" % (to_user, chat_id, message)
      
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
  
  def get(self):
    print("=-=-=-=-=-=-=-=-=-=-= DIRECT MESSAGE =-=-=-=-=-=-=-=-=-=-=")
    print("self.get_argument('chat_id'):%s" % (self.get_argument('chat_id', "")))
    
    if self.get_argument('chat_id', ""):
      kik.send_messages([
        TextMessage(
          to = "KdwgZ",
          chat_id = "f01aad68aea6c6b0c38866449d72d30222fa5d093630a0c7501f7e018da8bf83",#self.get_argument('chat_id', ""),
          body = "YOO",#self.get_argument('message', ""),
          type_time = 250
        )
      ])
        
    self.set_status(200)
    return



#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



gameHelpList = {}
help_convos = {}

topics = fetch_topics()
#slack_webhooks = fetch_slack_webhooks()



##Const.KIK_API_CONFIG = {
##   'USERNAME' : "streamcard",
##   'API_KEY'  : "aa503b6f-dcda-4817-86d0-02cfb110b16a",
##   'WEBHOOK'  : {
##     'HOST' : "http://76.102.12.47",
##     'PORT' : 8080,
##     'PATH' : "kik"
##   },
##
##   'FEATURES' : {
##     'receiveDeliveryReceipts'  : True,
##     'receiveReadReceipts'      : True
##   }
## }


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
