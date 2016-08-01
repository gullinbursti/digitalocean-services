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

import urllib2
import requests
import MySQLdb as mdb

import tornado.escape
import tornado.ioloop
import tornado.web

import modd
import const as Const

from datetime import date, datetime
from urllib2 import quote

from kik.error import KikError
from kik import KikApi, Configuration
from kik.messages import messages_from_json, TextMessage, StartChattingMessage, LinkMessage, PictureMessage, StickerMessage, ScanDataMessage, UnknownMessage, VideoMessage, SuggestedResponseKeyboard, TextResponse, CustomAttribution, ReadReceiptMessage


Const.DB_HOST = 'external-db.s4086.gridserver.com'
Const.DB_NAME = 'db4086_modd'
Const.DB_USER = 'db4086_modd_usr'
Const.DB_PASS = 'f4zeHUga.age'

Const.MAX_REPLIES = 3


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#




#--:-- Message UI / Message Part Factories --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def default_keyboard():
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = False,
      responses = [
        #TextResponse(u"Pokemon Go"),
        TextResponse(u"Pokemon Go"),
        TextResponse("Dota 2"),
        TextResponse("League of Legends"),
        TextResponse("CS:GO"),
        TextResponse("Cancel")
      ]
    )
  ]
  
  return keyboard
  

def default_text_reply(message, delay=0, type_time=0):
  print "default_text_reply(message=%s)" % (message)
  
  return TextMessage(
    to = message.from_user,
    chat_id = message.chat_id,
    body = "Select a game that you need help with. Type cancel anytime to end this conversation.",
    keyboards = default_keyboard(),
    type_time = type_time,
    delay = delay
  )


def default_wait_reply(message):
  print "default_wait_reply(message=%s)" % (message)
  
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
  print "%d\tfetch_topics()" % (int(time.time()))
  _arr = []
  
  try:
    conn = sqlite3.connect("%s/data/sqlite3/kikbot.db" % (os.getcwd()))
    c = conn.cursor()
    c.execute("SELECT display_name FROM topics WHERE enabled = 1;")
    
    for row in c.fetchall():
      _arr.append(row[0])
      key_name = re.sub( '\s+', "_", row[0])
      print "UTF-8 ENCODED : [%s]" % (quote(row[0].key_name.encode('utf-8')).toLower())
    
    conn.close()
  
  except:
    pass
  
  finally:
    pass
  
  print "%d\t_arr:%s" % (int(time.time()), _arr)
  return _arr
  

def fetch_slack_webhooks():
  print "%d\tfetch_slack_webhooks()" % (int(time.time()))
  _obj = {}
  
  try:
    conn = sqlite3.connect("%s/data/sqlite3/kikbot.db" % (os.getcwd()))
    c = conn.cursor()
    c.execute("SELECT topics.display_name, slack_channels.channel_name, slack_channels.webhook FROM slack_channels INNER JOIN topics ON topics__slack_channels.slack_channel_id = topics.id INNER JOIN topics__slack_channels ON topics__slack_channels.topic_id = topics.id AND topics__slack_channels.slack_channel_id = slack_channels.id WHERE slack_channels.enabled = 1;")
    
    for row in c.fetchall():
      _obj[row[0]] = {
        'channel_name': row[1],
        'webhook':row[2]
      }
    
    conn.close()
  
  except:
    pass
  
  finally:
    pass
  
  print "%d\t_obj:%s" % (int(time.time()), _obj)
  return _obj
  

def fetch_faq(topic_name):
  print "%d\tfetch_faq(topic_name=%s)" % (int(time.time()), topic_name)
  
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

  
  #--:-- Session Subpaths / In-Session Seqs --:--#
  #-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #

def welcome_intro_seq(message):
  participants = message.participants
  participants.remove(message.from_user)
  
  print ("%s\tMENTION:\nCHAT ID:%s\nFROM:%s\nPARTICIPANT:%s" % (int(time.time()), mmessage.chat_id, message.from_user, participants[0]))
  modd.utils.sendTracker("bot", "init", "kik")
  
  kik.send_messages([
    TextMessage(
      to = message.from_user,
      chat_id = message.chat_id,
      body = u"Welcome to GameBots looks like a friend has mentioned me!",
      type_time = 333,
      delay = 1750
    ),
    
    TextMessage(
      to = message.from_user,
      chat_id = message.chat_id,
      body = u"Become a better eSports player with GameBots live chat support.",
      type_time = 333,
      delay = 2500
    ),
    default_txt_reply(message=message, delay=3500, type_time=333)
  ])

  
  return


def start_help(message):
    print "%d\tstart_help(message=%s)" % (int(time.time()), message)
    modd.utils.sendTracker("bot", "question", "kik")
    gameHelpList[message.from_user] = message.body
    
    kik.send_messages([
      TextMessage(
        to = message.from_user,
        chat_id = message.chat_id,
        body = "Please describe what you need help with. Note your messages will be sent to %s coaches for support." % (message.body),
        type_time = 333
      )
    ])
    
    return


def end_help(to_user, chat_id, user_action=True):
  print "%d\tend_help(to_user=\'%s\', chat_id=\'%s\', user_action=%d)" % (int(time.time()), to_user, chat_id, user_action)
  
  if not user_action:
    kik.send_messages([
      TextMessage(
        to = to_user,
        chat_id = chat_id,
        body = u"This %s help session is now closed." % (help_convos[chat_id]['game']),
        type_time = 250,
      )
    ])
  
  if chat_id in help_convos:
    if user_action:
      # _obj = slack_webhooks[help_convos[chat_id]['game']]
      # print "%d\t_obj FOR help_convos[\'%s\'][\'%s\'] : %s" % (int(time.time()), chat_id, help_convos[chat_id]['game'], _obj)
      #modd.utils.slack_send(_obj['channel_name'], _obj['webhook'], u"_Help session closed_ : *%s*" % (chat_id), to_user)
      modd.utils.slack_im(help_convos[chat_id], "Help session closed.")
    
    del help_convos[chat_id]
  
  time.sleep(3)
  cancel_session(to_user, chat_id)
  
  return


def cancel_session(to_user, chat_id, slack_channel=""):
  print "%d\tcancel_session(to_user=\'%s\', chat_id=\'%s\')" % (int(time.time()), to_user, chat_id)
  
  #-- send to kik user
  kik.send_messages([
    TextMessage(
      to = to_user,
      chat_id = chat_id,
      body = "Ok, Thanks for using GameBots!",#body = "Sounds good! Your GameBot is always here if you need help, just send me a message.",
      type_time = 250,
    )
  ])
  
  if len(slack_channel) > 0 :
    pass;

    
  
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
    print "%d\tself.request.headers.get('X-Kik-Signature')=%s" % (int(time.time()), self.request.headers.get('X-Kik-Signature'))
    #print "%d\tself.request.body=%s" % (int(time.time()), self.request.body)
    print "=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-="
    
    if not kik.verify_signature(self.request.headers.get('X-Kik-Signature'), self.request.body):
      print "403 Forbidden"
      self.set_status(403)
      return
    
    data_json = tornado.escape.json_decode(self.request.body)
    messages = messages_from_json(data_json["messages"])
    
    #print "%d\t:: len(messages)=%d" % (int(time.time()), len(messages))
    for message in messages:
      
      # -=-=-=-=-=-=-=-=- UNSUPPORTED TYPE -=-=-=-=-=-=-=-=-
      if isinstance(message, LinkMessage) or isinstance(message, PictureMessage) or isinstance(message, VideoMessage) or isinstance(message, ScanDataMessage) or isinstance(message, StickerMessage) or isinstance(message, UnknownMessage):
        print "%d\t=-= IGNORING MESSAGE =-=\n%s " % (int(time.time()), message)
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "I'm sorry, I cannot understand that type of message.",
            type_time = 20
          ),
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "Select a game that you need help with. Type cancel anytime to end this conversation.",
            keyboards = default_keyboard()
          )
        ])
        
        self.set_status(200)
        return
          
      
      # -=-=-=-=-=-=-=-=- READ RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, ReadReceiptMessage):
        print "%d\t-= ReadReceiptMessage =-= " % (int(time.time()))
        
        modd.utils.sendTracker("bot", "read", "kik")
        self.set_status(200)
        return
         
      
      # -=-=-=-=-=-=-=-=- START CHATTING -=-=-=-=-=-=-=-=-
      elif isinstance(message, StartChattingMessage):
        print "%d\t-= StartChattingMessage =-= " % (int(time.time()))
        
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = u"Welcome to GameBots!",
            type_time = 250,
          )
        ])
        
        time.sleep(2)
        
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = u"Become a better eSports player with GameBots live chat support."
          )
        ])
        
        time.sleep(2)
        
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "Select a game that you need help with. Type cancel anytime to end this conversation.",
            keyboards = default_keyboard()
          )
        ])
        
        self.set_status(200)
        return
        
      
      # -=-=-=-=-=-=-=-=- TEXT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, TextMessage):
        print "%d\t=-= TextMessage =-= " % (int(time.time()))
        
        try:
          conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
          with conn:
            cur = conn.cursor()
            cur.execute("INSERT IGNORE INTO `kikbot_logs` (`username`, `chat_id`, `body`) VALUES (\'%s\', \'%s\', \'%s\')" % (message.from_user, message.chat_id, quote(message.body.encode('utf-8'))))
        
        except mdb.Error, e:
          print "%d\tMySqlError %d: %s" % (int(time.time()), e.args[0], e.args[1])
        
        finally:
          if conn:
            conn.close()
        
        print "%s" % (int(time.time()))
        print "[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]"
        print "-=- gameHelpList -=-\n%s" % (gameHelpList)
        print "-=- help_convos -=-\n%s" % (help_convos)
        print "[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]"
        
        
        
        # -=-=-=-=-=-=-=-=-=- END SESSION -=-=-=-=-=-=-=-
        if message.body.lower() == "!end" or message.body.lower() == "cancel" or message.body.lower() == "quit":
          print "%d\t-=- ENDING HELP -=-"
          end_help(message.from_user, message.chat_id)
          self.set_status(200)
          return
        
        
        # -=-=-=-=-=-=-=-=-=- MENTIONS -=-=-=-=-=-=-=-=-
        if message.mention is not None:
          if message.body == "Start Chatting":
            self.set_status(200)
            return
          
          #-- other mention type -- toss messages at 'em
          else:
            welcome_intro_seq(message)
          
            
            self.set_status(200)
            return
        
        else:
          
          # -=-=-=-=-=-=-=-=- DEFAULT GAME BTNS -=-=-=-=-=-=-=-=-
          if message.body == u"Pokemon Go" or message.body == "CS:GO" or message.body == "Dota 2" or message.body == "League of Legends":
            if len(gameHelpList) == 0:
              start_help(message)
              
              print "%d\tSUBSCRIBING \"%s\" TO \"%s\" --> %s" % (int(time.time()), message.from_user, quote(message.body.lower().encode('utf-8')), message.chat_id)
              modd.utils.sendTracker("bot", "subscribe", "kik")
              
              _sub = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=%s&username=%s&cid=%s' % (quote(message.body.lower().encode('utf-8')), message.from_user, message.chat_id))
              self.set_status(200)
              return
          
          
          # -=-=-=-=-=-=-=-=-=- FAQ BUTTONS -=-=-=-=-=-=-=-=-=-
          #elif message.body.find("FAQ") > -1 or message.body == u"Ask Another Question":
          elif message.body == u"More Details":
            if message.chat_id in help_convos:
              # if message.body.find("FAQ") > -1:
              faq_arr = fetch_faq(help_convos[message.chat_id]['game'])
              print "faq_arr:%s" % (faq_arr)
              
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
            
            
            #-- gimme ouuta here
            self.set_status(200)
            return
          
          
          # -=-=-=-=-=-=-=-=-=- HELP CONNECT -=-=-=-=-=-=-=-
          if message.from_user in gameHelpList:
            
            #-- data obj/ now in active session
            help_convos[message.chat_id] = {
              'chat_id': message.chat_id,
              'username': message.from_user,
              'game': gameHelpList[message.from_user],
              'ignore_streak': 0,
              'started': int(time.time()),
              'messages': [],
              'im_channel': ""
            }
          
            
            kik.send_broadcast([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Locating %s coaches..." % (gameHelpList[message.from_user]),
                type_time = 250,
                delay = 0
              ),
              
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Pro tip: Keep asking questions, each will be added to your queue! Type Cancel to end the conversation.",
                type_time = 1500,
                delay = 1500
              )
            ])

            
            _obj = slack_webhooks[help_convos[message.chat_id]['game']]
            modd.utils.slack_send(_obj['channel_name'], _obj['webhook'], message.body, message.from_user)
            
            del gameHelpList[message.from_user]
            self.set_status(200)
            return
            
          
          
          # -=-=-=-=-=-=-=-=-=- HAS EXISTING SESSION -=-=-=-=-=-=-=-
          if message.chat_id in help_convos:
            
            #-- inc message count & log
            help_convos[message.chat_id]['ignore_streak'] += 1
            help_convos[message.chat_id]['messages'].append(message.body)
            
            # -=-=-=-=-=-=-=-=-=- SESSION GOING INACTIVE -=-=-=-=-=-=-=-
            if help_convos[message.chat_id]['ignore_streak'] >= Const.MAX_REPLIES:
              print "%d\t-=- TOO MANY UNREPLIED (%d)... CLOSE OUT SESSION -=-" % (int(time.time()), help_convos[message.chat_id]['ignore_streak'])
              
              #-- closing out session w/ 2 opts
              kik.send_messages([
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = u"Sorry! GameBots is taking so long to answer your question. What would you like to do?",
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
          #-- anytintg elsem  prompt with 4 topics
          if len(gameHelpList) == 0 and len(help_convos) == 0:
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Select a game that you need help with. Type cancel anytime to end this conversation.",
                type_time = 250,
                keyboards = default_keyboard()
              )
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
    print "%d\t=-=-=-=-=-=-=-=-=-=-= SLACK RESPONSE =-=-=-=-=-=-=-=-=-=-=" % (int(time.time()))
    
    if self.get_argument('token', "") == "IJApzbM3rVCXJhmkSzPlsaS9":
      _arr = self.get_argument('text', "").split(' ')
      _arr.pop(0)
      
      chat_id = _arr[0]
      _arr.pop(0)
      
      message = " ".join(_arr).replace("'", "")
      to_user = ""
      
      try:
        conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
        with conn:
          cur = conn.cursor(mdb.cursors.DictCursor)
          cur.execute("SELECT `username` FROM `kikbot_logs` WHERE `chat_id` = '%s' ORDER BY `added` DESC LIMIT 1;" % (chat_id))
          
          if cur.rowcount == 1:
            row = cur.fetchone()
            
            print "%d\thelp_convos:%s" % (int(time.time()), help_convos)
            if chat_id in help_convos:
              help_convos[chat_id]['ignore_streak'] = -1
              to_user = row['username']
              
              #print "%d\tto_user=%s, to_user=%s, chat_id=%s, message=%s" % (int(time.time()), to_user, chat_id, message)
              
              if message == "!end" or message.lower() == "cancel" or message.lower() == "quit":
                print "%d\t-=- ENDING HELP -=-"
                end_help(to_user, chat_id, False)
              
              else:
                kik.send_messages([
                  TextMessage(
                    to = to_user,
                      chat_id = chat_id,
                      body = "%s coach:\n%s" % (help_convos[chat_id]['game'], message),
                      type_time = 250,
                    )
                ])
      
      except mdb.Error, e:
        print "%d\tError %d: %s" % (e.args[0], e.args[1])
      
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
    print "%d\t=-=-=-=-=-=-=-=-=-=-= SLACK IM =-=-=-=-=-=-=-=-=-=-=" % (int(time.time()))
    data = tornado.escape.json_decode(self.request.body)
    print "%d\tpayload:%s" % (int(time.time()), data)
    
    help_convos[data['chat_id']]['im_channel'] = data['channel']
    

#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



#subscribersForStreamer = {}
gameHelpList = {}
help_convos = {}

# streamerArray = getStreamers()
# for s in streamerArray:
#    subscribersForStreamer[s.lower()] = []
#


topics = fetch_topics()
slack_webhooks = fetch_slack_webhooks()


# x = urllib2.urlopen("http://beta.modd.live/api/subscriber_list.php?type=kik").read()
#
# r = x.split("\n")
# for row in r:
#    c = row.split(",")
#    if len(c) == 3 and c[0].lower() in subscribersForStreamer:
#       subscribersForStreamer[c[0].lower()].append({'kikUser':c[1],'chat_id':c[2]})





##Const.KIK_API_CONFIG = {
##   'USERNAME': "streamcard",
##   'API_KEY': "aa503b6f-dcda-4817-86d0-02cfb110b16a",
##   'WEBHOOK': {
##     'HOST': "http://76.102.12.47",
##     'PORT': 8080,
##     'PATH': "kik"
##   },
##
##   'FEATURES': {
##     'receiveDeliveryReceipts': True,
##     'receiveReadReceipts': True
##   }
## }


Const.KIK_API_CONFIG = {
  'USERNAME': "game.bots",
  'API_KEY': "0fb46005-dd00-49c3-a4a5-239a0bdc1e79",
  'WEBHOOK': {
    'HOST': "http://159.203.250.4",
    'PORT': 8080,
    'PATH': "kik"
  },

  'FEATURES': {
    'receiveDeliveryReceipts': True,
    'receiveReadReceipts': True
  }
}


# Const.KIK_API_CONFIG = {
#   'USERNAME': "gamebots.beta",
#   'API_KEY': "570a2b17-a0a3-4678-a9cd-fa21edf8bb8a",
#   'WEBHOOK': {
#     'HOST': "http://76.102.12.47",
#     'PORT': 8080,
#     'PATH': "kik"
#   },
#   
#   'FEATURES': {
#     'receiveDeliveryReceipts': True,
#     'receiveReadReceipts': True
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
print "\n\n\n# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #"
print "# -= Firing up KikApi WITH =- #"
print "# -= =-=-=-=-=-=-=-=-=-=-=-= =- #"
print "USERNAME : %s\nAPI_KEY : %s\nHOST   : %s\nPORT   : %d\nPATH   : %s\nCONFIG :%s" % (
  Const.KIK_API_CONFIG['USERNAME'],
  Const.KIK_API_CONFIG['API_KEY'],
  Const.KIK_API_CONFIG['WEBHOOK']['HOST'],
  Const.KIK_API_CONFIG['WEBHOOK']['PORT'],
  Const.KIK_API_CONFIG['WEBHOOK']['PATH'],
  kik.get_configuration().to_json())
print "# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #\n\n\n"



#-- url webhooks
application = tornado.web.Application([
  (r"/kik", KikBot),
  # (r"/kikNotify", Notify),
  # (r"/notify", Notify),`
  # (r"/message", Message),
  (r"/slack", Slack),
  (r"/im", InstantMessage)
])


#-- server starting
if __name__ == "__main__":
  application.listen(int(Const.KIK_API_CONFIG['WEBHOOK']['PORT']))
  tornado.ioloop.IOLoop.instance().start()
  print "%d\ttornado start" % (int(time.time()))
  
