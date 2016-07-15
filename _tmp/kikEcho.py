#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import time
import csv
import json
import random
import sqlite3

import urllib2
import requests
import netifaces as ni
import MySQLdb as mdb

import tornado.escape
import tornado.ioloop
import tornado.web

import modd
import const as Const

from datetime import date, datetime
from urllib2 import quote

from kik import KikApi, Configuration
from kik.messages import messages_from_json, TextMessage, StartChattingMessage, LinkMessage, PictureMessage, StickerMessage, ScanDataMessage, UnknownMessage, VideoMessage, SuggestedResponseKeyboard, TextResponse, CustomAttribution, ReadReceiptMessage


Const.DB_HOST = 'external-db.s4086.gridserver.com'
Const.DB_NAME = 'db4086_modd'
Const.DB_USER = 'db4086_modd_usr'
Const.DB_PASS = 'f4zeHUga.age'

Const.MAX_REPLIES = 4

def getStreamers():
  streamers = []
  
  try:
    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
    with conn:
      cur = conn.cursor(mdb.cursors.DictCursor)
      cur.execute("SELECT `channel_name` FROM `subscribe_topics` WHERE `type` = 'streamer' OR `type` = 'game';")
      rows = cur.fetchall()
    
      for row in rows:
        streamers.append(row['channel_name'])  
  
  except mdb.Error, e:
    print "Error %d: %s" % (e.args[0], e.args[1])
    
  finally:
    if conn:    
      conn.close()
 
  return streamers


def getStreamerContent(url):
  _response = urllib2.urlopen(url, timeout=5)
  _json = json.load(_response, 'utf-8')
  
  return [_json['channel'], _json['preview_img'], _json['player_url']]
  


def default_keyboard():
  keyboard = [
    SuggestedResponseKeyboard(
      hidden = False,
      responses = [
        TextResponse(u"Pok\xe9mon Go"),
        TextResponse("Dota 2"),
        TextResponse("League of Legends"),
        TextResponse("CS:GO")
      ]
    )
  ]
  
  return keyboard
  

def delayed_kik_send(messages, delay=2000):
  for i in range(0, len(messages)):
    kik.send_messages([messages[i]])
    time.sleep (delay * 0.001);
    

def start_help(message):
  modd.utils.sendTracker("bot", "question", "kik")
  gameHelpList[message.from_user] = message.body
 
 kik.send_messages([
   TextMessage(
     to = message.from_user,
     chat_id = message.chat_id,
     body = "Please describe what you need help with?",
     type_time = 333
   )
 ])
  
  kik.send_messages([
    TextMessage(
      to = message.from_user,
      chat_id = message.chat_id,
      body = "Please describe what you need help with?",
      type_time = 150,
    )
  ])
  
  return
  

def end_help(to_user, chat_id, user_action=True):
  _obj = slack_webhook(help_convos[chat_id]['game'])
  
  delayed_kik_send([
    TextMessage(
      to = to_user,
      chat_id = chat_id,
      body = u"This %s help session is now closed." % (help_convos[chat_id]['game']),
      type_time = 250,
    ),
    TextMessage(
      to = to_user,
      chat_id = chat_id,
      body = "Select a game you need help with...",
      keyboards = default_keyboard()
    )
  ], 5000)
  
  print "Sending close message (%s)...\n%s" % (user_action, _obj)
  if user_action:
    payload = json.dumps({
      'channel': _obj['channel'], 
      'username': to_user,
      'icon_url': "http://i.imgur.com/ETxDeXe.jpg",
      'text': "*Help session closed*"
    })
  
    response = requests.post(_obj['webhook'], data={'payload': payload})
    
  
  del help_convos[chat_id]
  return
  
  
def slack_webhook(topic_name):
  channel_name = ""
  webhook_url = ""
  
  if topic_name == u"Pok\xe9mon Go":
    channel_name = "#pokemon-go"
    webhook_url = "https://hooks.slack.com/services/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"

  elif topic_name == "CS:GO":
    channel_name = "#csgo"
    webhook_url = "https://hooks.slack.com/services/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"

  elif topic_name == "Dota 2":
    channel_name = "#dota2"
    webhook_url = "https://hooks.slack.com/services/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"

  elif topic_name == "League of Legends":
    channel_name = "#leagueoflegends"
    webhook_url = "https://hooks.slack.com/services/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"
  
  _obj = {
    'channel': channel_name,
    'webhook': webhook_url
  }
  
  return _obj
  
  
def fetch_faq(topic_name):
  _obj = {}
  
  try:
    conn = sqlite3.connect("%s/data/sqlite3/topics.db" % (os.getcwd()))
    c = conn.cursor()
    c.execute("SELECT faq_content.content FROM `faqs` INNER JOIN `faq_content` ON faqs.id = faq_content.topic_id WHERE faqs.title = \'%s\' LIMIT 1;" % (topic_name))
        
    _obj = {
      'title': topic_name,
      'content': c.fetchone()[0].split("\\n")
    }

    conn.close()
    
  except:
    pass

  finally:
    pass
    
  return _obj


class Notify(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
  def get(self):
    streamerName = self.get_arguments('streamer')[0]
    kikMessage = self.get_arguments('message')[0]
    link_pic = getStreamerContent("http://beta.modd.live/api/live_streamer.php?channel=" + streamerName)
    kikSubscribers = subscribersForStreamer[streamerName]
    
    for chat in kikSubscribers:
      print("SENDING CONVO - TO: " + chat['kikUser'] + " CHAT_ID: " + chat['chat_id'])
      modd.utils.sendTracker("bot", "send", "kik")
      kik.send_messages([
        TextMessage(
          to = chat['kikUser'],
          chat_id = chat['chat_id'],
          body = kikMessage
        ),
        LinkMessage(
          to = chat['kikUser'],
          chat_id = chat['chat_id'],
          title = link_pic[0],
          pic_url = link_pic[1],
          url = link_pic[2],
          attribution = CustomAttribution(
            name = 'Streamcard.tv', 
            icon_url = 'http://streamcard.tv/img/icon/favicon-32x32.png'
          )
        ),
        TextMessage(
          to = chat['kikUser'],
          chat_id = chat['chat_id'],
          body = "Tap here to watch now. gbots.cc/channel/" + link_pic[0]
        )
      ])


class Message(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
  def post(self):
    print("=-=-=-=-=-=-=-=-=-=-= MESSAGE BROADCAST =-=-=-=-=-=-=-=-=-=-=")
    username = self.get_body_argument('recipient', "")
    body = self.get_body_argument('body', "")
    url = self.get_body_argument('url', "")
    image_url = self.get_body_argument('image_url', "")
    video_url = self.get_body_argument('video_url', "")
    message_type = self.get_body_argument('type', "")
    message_method = self.get_body_argument('method', "")
      
    try:
      conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
      with conn:
        cur = conn.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT `chat_id` FROM `kikbot_logs` WHERE `username` = '%s' ORDER BY `added` DESC LIMIT 1;" % (username))
        
        if cur.rowcount == 1:
          row = cur.fetchone()
          
          print("RECIPIENT: %s (%s)" % (username, row['chat_id']))
          if message_type == "TextMessage":
            print("BODY : " + body)
            kik_message = TextMessage(
              to = username,
              chat_id = row['chat_id'],
              body = body
            )

          elif message_type == "LinkMessage":
            print("BODY : " + body)
            print("IMG_URL : " + image_url)
            print("URL : " + url)
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
            print("VID_URL : " + video_url)
            kik_message = VideoMessage(
              to = username,
              chat_id = row['chat_id'],
              video_url = video_url,
              autoplay = False,
              muted = False,
              loop = False
            )

          kik.send_messages([kik_message])
                    
    except mdb.Error, e:
      print "Error %d: %s" % (e.args[0], e.args[1])

    finally:
      if conn:    
        conn.close()
        

def recipients_for_topic(topic_name):
  recipients = []
  
  try:
    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
    with conn:
      cur = conn.cursor(mdb.cursors.DictCursor)
      cur.execute("SELECT `viewer_kik`, `viewer_kik_chat_id` FROM `notify` WHERE `channel_name` = \'%s\';" % (quote(topic_name.encode('utf-8'))))
      rows = cur.fetchall()
      
      for row in rows:
        recipients.append({
          'username': row['viewer_kik'],
          'chat_id': row['viewer_kik_chat_id']
        })
  
  except mdb.Error, e:
    print "Error %d: %s" % (e.args[0], e.args[1])

  finally:
    if conn:    
      conn.close()
      
  return recipients
  
  
class KikBot(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
  def post(self):
    if not kik.verify_signature(self.request.headers.get('X-Kik-Signature'), self.request.body):
      return Response(status=403)
            
    data_json = tornado.escape.json_decode(self.request.body)
    messages = messages_from_json(data_json["messages"])
    print(messages)
    
    for message in messages:
      # -=-=-=-=-=-=-=-=- UNSUPPORTED TYPE -=-=-=-=-=-=-=-=-
      if isinstance(message, LinkMessage) or isinstance(message, PictureMessage) or isinstance(message, VideoMessage) or isinstance(message, ScanDataMessage) or isinstance(message, StickerMessage) or isinstance(message, UnknownMessage):
        print("=-= IGNORING MESSAGE =-= ")
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "I'm sorry, I cannot understand that type of message.",
            type_time = 0
          ),
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "Select a game you need help with...",
            keyboards = default_keyboard()
          )
        ])
        
        self.set_status(200)        
        return
          
          
      # -=-=-=-=-=-=-=-=- READ RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, ReadReceiptMessage):
        modd.utils.sendTracker("bot", "read", "kik")
        self.set_status(200)        
        return
         
         
      # -=-=-=-=-=-=-=-=- START CHATTING -=-=-=-=-=-=-=-=-
      elif isinstance(message, StartChattingMessage):
        print(data_json)
        
        delayed_kik_send([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = u"Welcome to GameBots!",
            type_time = 250,
          ),
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = u"Become a better eSports player with GameBots live chat support."
          ),
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "Select a game you need help with...",
            keyboards = default_keyboard()
          )
        ], 1000)
        
        self.set_status(200)        
        return
        
        
      # -=-=-=-=-=-=-=-=- TEXT MESSAGE -=-=-=-=-=-=-=-=-   
      elif isinstance(message, TextMessage):
        print(data_json)
        
        try:
          conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
          with conn:
            cur = conn.cursor()
            cur.execute("INSERT IGNORE INTO `kikbot_logs` (`username`, `chat_id`, `body`, `added`) VALUES (\'%s\', \'%s\', \'%s\',  NOW())" % (message.from_user, message.chat_id, quote(message.body.encode('utf-8'))))

        except mdb.Error, e:
          print "MySqlError %d: %s" % (e.args[0], e.args[1])

        finally:
          if conn:    
            conn.close()
            
            
        # -=-=-=-=-=-=-=-=-=- MENTIONS -=-=-=-=-=-=-=-=-
        if message.mention is not None:
          if message.body == "Start Chatting":
            self.set_status(200)            
            return
              
          else:
            participants = message.participants
            participants.remove(message.from_user)
            
            print ("MENTION:\nCHAT ID:%s\nFROM:%s\nPARTICIPANT:%s" % (message.chat_id, message.from_user, participants[0]))
            modd.utils.sendTracker("bot", "init", "kik")
          
            delayed_kik_send([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = u"Welcome to GameBots looks like a friend has mentioned me!",
                type_time = 250,
              ),
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = u"Become a better eSports player with GameBots live chat support."
              ),
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Select a game you need help with...",
                keyboards = default_keyboard()
              )
            ], 1000)
          
            self.set_status(200)          
            return
            
            
        else:
          
          help_convos["d50b421869131bfb32709dc9be757ac79a9d1a24f02ee4e8b33bbb91d376a895"] = {
            'chat_id': "d50b421869131bfb32709dc9be757ac79a9d1a24f02ee4e8b33bbb91d376a895",
            'username': "allygupps2",
            'game': u"Pok\xe9mon Go",
            'messages': ["HELP"]
          }
          
          # -=-=-=-=-=-=-=-=- DEFAULT GAMES -=-=-=-=-=-=-=-=-
          if message.body == "!STOP":
            _key = ""
            
            if message.from_user in gameHelpList:
              _key = gameHelpList[message.from_user]
              
            if message.chat_id in help_convos:
              _key = help_convos[message.chat_id]
              
            _obj = slack_webhook(_key) 
            if len(_obj) != 0:
              print "Sending close message...\n%s" % (_obj)         
              payload = json.dumps({
                'channel': _obj['channel'], 
                'username': message.from_user,
                'icon_url': "http://i.imgur.com/ETxDeXe.jpg",
                'text': "*Canceling this help session...*"
              })
            
              response = requests.post(_obj['webhook'], data={'payload': payload})
              
              
              kik.send_messages([
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = "Aborting help session...",
                  type_time = 250,
                )
              ])
              
              if message.from_user in gameHelpList:
                del gameHelpList[message.from_user]
                
              if message.chat_id in help_convos:
                del help_convos[message.chat_id]
              
              self.set_status(200)              
              return
            

          # -=-=-=-=-=-=-=-=- DEFAULT GAMES -=-=-=-=-=-=-=-=-
          if message.body == u"Pok\xe9mon Go" or message.body == "CS:GO" or message.body == "Dota 2" or message.body == "League of Legends":
            print "SUBSCRIBING \"%s\" TO \"%s\" --> %s" % (message.from_user, quote(message.body.lower().encode('utf-8')), message.chat_id)
            modd.utils.sendTracker("bot", "subscribe", "kik")
            start_help(message)
            
            _sub = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=%s&username=%s&cid=%s' % (quote(message.body.lower().encode('utf-8')), message.from_user, message.chat_id))
            self.set_status(200)            
            return
          
          # -=-=-=-=-=-=-=-=-=- FAQ BUTTONS -=-=-=-=-=-=-=-=-=- 
          if (message.body == u"Yes" or message.body == u"No"):
            
            if message.chat_id in help_convos:
              faq_obj = fetch_faq(help_convos[message.chat_id]['game'])
              del help_convos[message.chat_id]
            
              if message.body == u"Yes":  
                print "faq_obj:%s" % (faq_obj)
              
                messages = []
                for l in faq_obj['content']:
                  messages.append(
                    TextMessage(
                      to = message.from_user,
                      chat_id = message.chat_id,
                      body = l,
                      type_time = 100,
                    )
                  )
                
                messages.append(
                  TextMessage(
                    to = message.from_user,
                    chat_id = message.chat_id,
                    body = "Select a game you need help with...",
                    keyboards = default_keyboard()
                  )
                )
              
                delayed_kik_send(messages, 5000)
                self.set_status(200)
                return
              
              elif message.body == u"No":
                delayed_kik_send([
                  TextMessage(
                    to = message.from_user,
                    chat_id = message.chat_id,
                    body = "Sounds good! Your GameBot is always here if you need help.",
                    type_time = 250,
                  ),
                  TextMessage(
                    to = message.from_user,
                    chat_id = message.chat_id,
                    body = "Select a game you need help with...",
                    keyboards = default_keyboard()
                  )
                ])
            
              self.set_status(200)              
              return
          
          # -=-=-=-=-=-=-=-=-=- HELP CONNECT -=-=-=-=-=-=-=-
          if message.from_user in gameHelpList:
            help_convos[message.chat_id] = {
              'chat_id': message.chat_id,
              'username': message.from_user,
              'game': gameHelpList[message.from_user],
              'no_replies_cnt': 0,
              'messages': []
            }
            
            _obj = slack_webhook(gameHelpList[message.from_user])
            
            payload = json.dumps({
              'channel': _obj['channel'], 
              'username': message.from_user,
              'icon_url': "http://i.imgur.com/ETxDeXe.jpg",
              'text': u"_Requesting help:_ *%s*\n\"%s\"" % (message.chat_id, message.body)
            })
            response = requests.post(_obj['webhook'], data={'payload': payload})
            print "Slack payload:%s" % (payload)

            delayed_kik_send([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Locating top %s players..." % (gameHelpList[message.from_user]),
                type_time = 3330,
              ),
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Locating top %s players..." % (gameHelpList[message.from_user]),
                type_time = 3330,
              ),
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Top %s players were found & and one reply to your question shortly." % (gameHelpList[message.from_user]),
                type_time = 250,
              )
            ])
          
            del gameHelpList[message.from_user]
            self.set_status(200)            
            return


          # -=-=-=-=-=-=-=-=-=- HELP SESSION -=-=-=-=-=-=-=-
          if message.chat_id in help_convos:
            print "-=- help_convos -=-\n%s" % (help_convos)
            help_convos[message.chat_id]['messages'].append(message.body)
            _obj = slack_webhook(help_convos[message.chat_id]['game'])
            
            if help_convos[message.chat_id]['no_replies_cnt'] > Const.MAX_REPLIES:
              print "-=- ENDING HELP -=-"
              
              kik.send_messages([
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = u"Top %s players are working on a solution for your question.\nWould you like to read some details about %s? " % (help_convos[message.chat_id]['game'], help_convos[message.chat_id]['game']),
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

              # print "Sending close message...\n%s" % (_obj)              
              # payload = json.dumps({
              #   'channel': _obj['channel'], 
              #   'username': message.from_user,
              #   'icon_url': "http://i.imgur.com/ETxDeXe.jpg",
              #   'text': "*Help session closed after %s replies*" % (Const.MAX_REPLIES)
              # })
              # 
              # response = requests.post(_obj['webhook'], data={'payload': payload})
              # del help_convos[message.chat_id]
              self.set_status(200)              
              return
            
            else:
              if message.body.lower() == "!end":
                print "-=- ENDING HELP -=-"              
                end_help(message.from_user, message.chat_id)
            
              else: 
                help_convos[message.chat_id]['no_replies_cnt'] += 1
                _obj = slack_webhook(help_convos[message.chat_id]['game'])
              
                payload = json.dumps({
                  'channel': _obj['channel'], 
                  'username': message.from_user,
                  'icon_url': "http://i.imgur.com/ETxDeXe.jpg",
                  'text': "\"%s\"" % (message.body)
                })
                response = requests.post(_obj['webhook'], data={'payload': payload})
            
            self.set_status(200)            
            return
       
        
        # -=-=-=-=-=-=-=-=-=- DEFAULT -=-=-=-=-=-=-=-=-=- 
        try:
          conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
          with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute("SELECT COUNT(*) FROM `subscribe_topics` WHERE `channel_name` = \'%s\' LIMIT 1;" % (quote(message.body.lower().encode('utf-8'))))
            
            if cur.rowcount == 1:
              row = cur.fetchone()
              start_help(message)
              
            else:
              modd.utils.sendTracker("bot", "question", "kik")
              
              delayed_kik_send([
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = "No top %s was found." % (message.body)
                ),
                TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = "Would you like to read an faq about %s" % ("DERP"),
                  keyboards = default_keyboard()
                )
              ])
              
              
              #print("SUBSCRIBING TO: " + message.chat_id)
              #_ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=%s&username=%s&cid=%s' % (streamerLowerCase, message.from_user, message.chat_id))
              #subscribersForStreamer[streamerLowerCase].append({'kikUser':message.from_user,'chat_id':message.chat_id})
              #modd.utils.sendTracker("bot", "subscribe", "kik")

        except mdb.Error, e:
          print "Error %d: %s" % (e.args[0], e.args[1])

        finally:
          if conn:    
            conn.close()
            
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "Select a game you need help with...",
            type_time = 250,
            keyboards = default_keyboard()
          )
        ])
        self.set_status(200)        
        return


  
class Slack(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
    
  def post(self):
    print "=-=-=-=-=-=-=-=-=-=-= SLACK RESPONSE =-=-=-=-=-=-=-=-=-=-="
    
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
            
            print "help_convos:%s" % (help_convos)
            if chat_id in help_convos:
              help_convos[chat_id]['no_replies_cnt'] = 0
              to_user = row['username']

              print "\"%s\" (%s)\n%s" % (to_user, chat_id, message)

              if message == "!end":
                print "-=- ENDING HELP -=-"
                end_help(to_user, chat_id, False)

              else:
                kik.send_messages([
                  TextMessage(
                    to = to_user,
                      chat_id = chat_id,
                      body = "%s helper:\n%s" % (help_convos[chat_id]['game'], message),
                      type_time = 250,
                    )
                ])

      except mdb.Error, e:
        print "Error %d: %s" % (e.args[0], e.args[1])

      finally:
        if conn:    
          conn.close()
          
    self.set_status(200)          
    return
          

subscribersForStreamer = {}
gameHelpList = {}
help_convos = {}

streamerArray = getStreamers()
for s in streamerArray:
   subscribersForStreamer[s.lower()] = []
   
   

#c.execute('''CREATE TABLE `faqs` (`id` INTEGER PRIMARY KEY, `title` VARCHAR(255), `content` TEXT, `added` DATE, `updated` DATE)''')

#c.execute("INSERT INTO faqs(`id`, `title`, `content`, `added`, `updated`) VALUES (NULL, '_{TITLE}_', '_{CONTENT}_', '%s', '%s')" % (datetime.datetime.now(), datetime.datetime.now()))
#conn.commit()
#conn.close()
  


x = urllib2.urlopen("http://beta.modd.live/api/subscriber_list.php?type=kik").read()

r = x.split("\n")
for row in r:
   c = row.split(",")
   if len(c) == 3 and c[0].lower() in subscribersForStreamer:
      subscribersForStreamer[c[0].lower()].append({'kikUser':c[1],'chat_id':c[2]})
      

kik = KikApi("streamcard", "aa503b6f-dcda-4817-86d0-02cfb110b16a")
kik.set_configuration(Configuration(webhook="http://76.102.12.47:8891/kik", features={"receiveReadReceipts":True, "receiveDeliveryReceipts":True}))

#kik = KikApi("game.bots", "0fb46005-dd00-49c3-a4a5-239a0bdc1e79")
#kik.set_configuration(Configuration(webhook="http://159.203.250.4:8891/kik", features={"receiveReadReceipts":True, "receiveDeliveryReceipts":True}))

## TODO reconstruct who subscribed for what from  into subscribersForStreamer

application = tornado.web.Application([
  (r"/kik", KikBot), 
  (r"/kikNotify", Notify), 
  (r"/notify", Notify),
  (r"/message", Message),
  (r"/slack", Slack)
])


if __name__ == "__main__":
  application.listen(8891)
  tornado.ioloop.IOLoop.instance().start()
  print("tornado start")
