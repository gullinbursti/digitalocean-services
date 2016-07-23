import os
import sys
import json
import MySQLdb as mdb
import sys
import json
import time
import requests
import netifaces as ni
import urllib2
import logging
import grequests
import threading
import random
import sqlite3
import re


from datetime import date, datetime
from urllib2 import quote

import modd
import const as Const

from flask import Flask, request

app = Flask(__name__)

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler('/var/log/FacebookBot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)



Const.DB_HOST = 'external-db.s4086.gridserver.com'
Const.DB_NAME = 'db4086_modd'
Const.DB_USER = 'db4086_modd_usr'
Const.DB_PASS = 'f4zeHUga.age'

Const.VERIFY_TOKEN = "ae9118876b91ea88def1259cc13ff2ca"
Const.ACCESS_TOKEN = "EAAXFDiMELKsBAOGORxGCuAEI1iMikfMaJAaQC9SoEjAeegGysjjeydYK1eaqqzJ1K7X2bI1XhZByjggh6ofPr8qC5dfkZCSEfmvTV6CiSSOmfLwAdWcNjplMR5W7OKogdKHG1pDkZAVgKm7eGoJZCK4E947g3ZBfEdstfWTRa7JXEN5zYpZCvS"

Const.MAX_REPLIES = 4


#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


class AsyncHTTPHandler(urllib2.HTTPHandler):
  def http_response(self, req, response):
    print "response.geturl(%s)" % (response.geturl())
    return response
    

def send_tracker(category, action, label):
  print "send_tracker(category=%s, action=%s, label=%s)" % (category, action, label) 
  try:
    _response = urllib2.urlopen("http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (str(category), str(action), str(label)))
  
  except:
    print "GA ERROR!"
        
    return
    # _o = urllib2.build_opener(AsyncHTTPHandler())
    # _t = threading.Thread(target=_o.open, args=("http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (str(category), str(action), str(label)),))
    # _t.start()
  
    # print "--> AsyncHTTPHandler :: _o=%s" % (_o)
  return
  
  
def slack_send(channel, webhook, message_txt, from_user="game.bots"):
  print "slack_send(channel=%s, webhook=%s, message_txt=%s, from_user=%s)" % (channel, webhook, message_txt, from_user)
  payload = json.dumps({
    'channel': "#" + channel, 
    'username': from_user,
    'icon_url': "http://i.imgur.com/ETxDeXe.jpg",
    'text': message_txt
  })

  _rs = (grequests.post(i, data={'payload': payload}) for i in [webhook])
  grequests.map(_rs)

  print "--> async grequests.post(i=%s, data=%s)" % (webhook, payload)


def start_help(message):
  print "%d\tstart_help(message=%s)" % (int(time.time()), message)
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
      _obj = slack_webhooks[help_convos[chat_id]['game']]
      print "%d\t_obj FOR help_convos[\'%s\'][\'%s\'] : %s" % (int(time.time()), chat_id, help_convos[chat_id]['game'], _obj)
      modd.utils.slack_send(_obj['channel_name'], _obj['webhook'], u"_Help session closed_ : *%s*" % (chat_id), to_user)
      del help_convos[chat_id]

  time.sleep(3)
  kik.send_messages([
    TextMessage(
      to = to_user,
      chat_id = chat_id,
      body = "Select a game you need help with...",
      keyboards = default_keyboard()
    )
  ])

  return
  
  
def fetch_topics():
  print "%d\tfetch_topics()" % (int(time.time()))
  _obj = {}

  try:
    conn = sqlite3.connect("%s/data/sqlite3/kikbot.db" % (os.getcwd()))
    c = conn.cursor()
    c.execute("SELECT key_name, display_name FROM topics WHERE enabled = 1;")

    for row in c.fetchall():
      _obj[row[0]] = row[1]
    conn.close()

  except:
    pass

  finally:
    pass

  print "%d\_obj:%s" % (int(time.time()), _obj)
  return _obj


def fetch_slack_webhooks():
  print "%d\tfetch_slack_webhooks()" % (int(time.time()))
  _obj = {}

  try:
    conn = sqlite3.connect("%s/data/sqlite3/fb_bot.db" % (os.getcwd()))
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
    conn = sqlite3.connect("%s/data/sqlite3/fb_bot.db" % (os.getcwd()))
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


def help_session_state(sender_id):
  print "%d\thelp_session_state(sender_id=%s)" % (int(time.time()), sender_id)
  state = -1

  try:
    conn = sqlite3.connect("%s/data/sqlite3/fb_bot.db" % (os.getcwd()))
    c = conn.cursor()
    c.execute("SELECT state FROM help_sessions WHERE sender_id = \'%s\' AND state < 3 ORDER BY added DESC LIMIT 1;")

    if c.rowcount == 1:
      row = c.fetchone()
      state = int(row[0])

    conn.close()

  except:
    pass

  finally:
    pass

  return state


def get_help_session(sender_id):
  print "%d\tget_help_session(sender_id=%s)" % (int(time.time()), sender_id)
  _obj = {}

  try:
    conn = sqlite3.connect("%s/data/sqlite3/fb_bot.db" % (os.getcwd()))
    c = conn.cursor()
    c.execute("SELECT id, state, topic, started, ended, addded FROM help_sessions WHERE sender_id = \'%s\' ORDER BY added DESC LIMIT 1;")

    if c.rowcount == 1:
      row = c.fetchone()
      _obj = {
        'id': int(row[0]),
        'state': int(row[1]),
        'topic': row[2],
        'started': row[3],
        'ended': row[4],
        'added': row[5]
      }

    conn.close()

  except:
    pass

  finally:
    pass

  return _obj
  
  
def set_help_session(session_obj):
  print "%d\tset_help_session(session_obj=%s)" % (int(time.time()), session_obj)
  action = "NONE"
  
  try:
    conn = sqlite3.connect("%s/data/sqlite3/fb_bot.db" % (os.getcwd()))  
    c = conn.cursor()
  
    if session_obj['id'] == 0:
      cur.execute("INSERT INTO help_sessions (id, sender_id, topic) VALUES (NULL, \'%s\', \'%s\')" % (session_obj['sender_id'], session_obj['topic']))
      session_obj['id'] = int(c.lastrowid)

    else:
      cur.execute("UPDATE help_sessions state = %d, topic = \%s\, started = \'%s\', ended = \'%s\' WHERE id = %d LIMIT 1;" % (session_obj['state'], session_obj['topic'], session_obj['started'], session_obj['ended'], session_obj['id']))
  
  except:
    pass

  finally:
    pass
    
  return get_help_session(session_obj['sender_id'])


def getStreamers():
  streamers = []
  return streamers


@app.route('/slack', methods=['POST'])
def slack():
  print "%d\t=-=-=-=-=-=-=-=-=-=-= SLACK RESPONSE =-=-=-=-=-=-=-=-=-=-=\n" % (int(time.time()), request.form)  
  if request.form.get('token') == "uKA7dgfnfadLN4QApLYmmn4m":
    help_session = {}
    
    _arr = request.form.get('text').split(' ')
    _arr.pop(0)
    
    chat_id = _arr[0]
    _arr.pop(0)
    
    message = " ".join(_arr).replace("'", "")
    to_user = ""
    
    try:
      conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
      with conn:
        cur = conn.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT `username` FROM `fbbot_logs` WHERE `chat_id` = '%s' ORDER BY `added` DESC LIMIT 1;" % (chat_id))

        if cur.rowcount == 1:
          row = cur.fetchone()
          
          print "%d\thelp_convos:%s" % (int(time.time()), help_convos)
          if chat_id in help_convos:
            help_convos[chat_id]['ignore_streak'] = -1
            to_user = row['username']

            #print "%d\tto_user=%s, to_user=%s, chat_id=%s, message=%s" % (int(time.time()), to_user, chat_id, message)

            if message == "!end":
              print "%d\t-=- ENDING HELP -=-"
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
      print "%d\tError %d: %s" % (e.args[0], e.args[1])

    finally:
      if conn:    
        conn.close()
        
  return "OK", 200
  

@app.route('/notify', methods=['GET'])
def notify():
  logger.info("-=- /notify -=- ")

  streamerName = request.args.get('streamer')
  fbMessage = request.args.get('message')
  logger.info("streamer:%s\nmessage:%s" % (streamerName, fbMessage))

  link_pic = getStreamerContent("http://beta.modd.live/api/live_streamer.php?channel=" + streamerName)
  fbSubscribers = subscribersForStreamer[streamerName]
  for chat in fbSubscribers:
    send_tracker("bot", "send", "facebook")
    send_text(chat['chat_id'], fbMessage)
    send_picture(chat['chat_id'], link_pic[0], link_pic[1])

  return "OK", 200


@app.route('/', methods=['GET'])
def verify():
  logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= VERIFY (%s)-> %s\n" % (request.args.get('hub.mode'), request.args.get('hub.verify_token')))
  if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
    if not request.args.get('hub.verify_token') == Const.VERIFY_TOKEN:
      return "Verification token mismatch", 403
    return request.args['hub.challenge'], 200

  return "Hello world", 200



@app.route('/', methods=['POST'])
def webook():
  logger.info("webhook")

  data = request.get_json()
  #logger.info(data)

  if data['object'] == "page":
    for entry in data['entry']:
      for messaging_event in entry['messaging']:
        if messaging_event.get("delivery"):  # delivery confirmation
          logger.info("%d\t -=- DELIVERY CONFIRM -=-" % (int(time.time())))
          return "ok", 200
          
        if messaging_event.get("read"):  # read confirmation
          logger.info("%d\t -=- READ CONFIRM -=-" % (int(time.time())))
          send_tracker("bot", "read", "facebook")
          return "ok", 200

        if messaging_event.get("optin"):  # optin confirmation
          logger.info("%d\t -=- OPT-IN -=-" % (int(time.time())))
          return "ok", 200

        if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
          logger.info("%d\t -=- POSTBACK RESPONSE -=-" % (int(time.time())))
          return "ok", 200
        
        
        #-- actual message
        if messaging_event.get('message'):
          logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECIEVED ->\n%s" % (messaging_event['message']))
          
          #------- IMAGE MESSAGE
          #if messaging_event['message']['type'] == "image":
          #  return "ok", 200

          # MESSAGE CREDENTIALS
          sender_id = messaging_event['sender']['id']        # the facebook ID of the person sending you the message
          recipient_id = messaging_event['recipient']['id']  # the recipient's ID, which should be your page's facebook ID
          message_id = messaging_event['message']['mid']
          message_text = messaging_event['message']['text']  # the message's text
          timestamp = messaging_event['timestamp']
          quick_reply = messaging_event['message']['quick_reply']['payload']
          
          
          #-- insert to log
          try:
            conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
            with conn:
              cur = conn.cursor()
              cur.execute("INSERT IGNORE INTO `fbbot_logs` (`id`, `message_id`, `chat_id`, `body`) VALUES (NULL, \'%s\', \'%s\', \'%s\')" % (message_id, sender_id, message_text))
              
          except mdb.Error, e:
            print "%d\tMySqlError %d: %s" % (int(time.time()), e.args[0], e.args[1])

          finally:
            if conn:    
              conn.close()
              
          
          help_state = help_session_state(sender_id)
          logger.info("%d\thelp_state=%d" % (help_state))
          
          #-- non-existant
          if help_state == -1:
            help_session = set_help_session({
              'id': 0,
              'sender_id': sender_id,
              'topic': ""
            })
            
            
          
          #-- started
          if help_state == 0:
            pass
          
          #-- requesting help
          elif help_state == 1:
            send_text(sender_id, "Locating top %s coach..." % (help_session['topic_name']))
            send_text(sender_id, "Type '!end' to close this help session.")
            
          #-- in session
          elif help_state == 2:
            # TODO send to slack
            pass
         
          
          #-- HELP LOOKUP
          if len(help_session) != 0:
            if help_session['state'] == 1:
              send_text(sender_id, "Locating top %s player..." % (help_session['topic_name']))
              send_text(sender_id, "Type '!end' to close this help session.")

              payload = json.dumps({
                'channel': "#fb-help", 
                'username': sender_id,
                'text': "Requesting help for *%s*:\n%s\n_\"%s\"_" % (help_session['topic_name'], sender_id, message_text.replace("\'", ""))
              })

              response = requests.post("https://hooks.slack.com/services/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", data={'payload': payload})

              try:
                conn = mdb.connect('external-db.s4086.gridserver.com', 'db4086_modd_usr', 'f4zeHUga.age', 'db4086_modd');
                with conn:
                  cur = conn.cursor()
                  cur.execute("UPDATE `help_sessions` SET `state` = 2 WHERE `id` = %s LIMIT 1;" % (help_session['id']))

              except mdb.Error, e:
                logger.info("Error %d: %s" % (e.args[0], e.args[1]))

              finally:
                if conn:    
                  conn.close()

              return "ok", 200
              
            elif help_session['state'] == 2 or help_session['state'] == 3:
              if message_text == "!end":
                print "-=- ENDING HELP -=-"
                send_text(sender_id, "You have closed this %s help session." % (help_convos["%s_%s" % (sender_id, sender_id)]['game']))
                send_text(sender_id, "Please tell me a game or player name you want to subscribe to.")
                del help_convos["%s_%s" % (sender_id, sender_id)]

                payload = json.dumps({
                  'channel': "#kik-help", 
                  'username': sender_id,
                  'text': "*Help session closed*"
                })

                try:
                  conn = mdb.connect('external-db.s4086.gridserver.com', 'db4086_modd_usr', 'f4zeHUga.age', 'db4086_modd');
                  with conn:
                    cur = conn.cursor()
                    cur.execute("UPDATE `help_sessions` SET `state` = 4 WHERE `id` = %s LIMIT 1;" % (help_session['id']))

                except mdb.Error, e:
                  logger.info("Error %d: %s" % (e.args[0], e.args[1]))

                finally:
                  if conn:    
                    conn.close()

              else: 
                payload = json.dumps({
                  'channel': "#kik-help", 
                  'username': sender_id,
                  'text': "_\"%s\"_" % (message_text.replace("\'", ""))
                })

              response = requests.post("https://hooks.slack.com/services/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", data={'payload': payload})
              return "ok", 200

            else:
              return "ok", 200
            
          
          if 'quick_reply' in messaging_event["message"]:
            payload = messaging_event["message"]["quick_reply"]["payload"]
            
            if payload.startswith("hlp_"):
              logger.info("Starting help...")
              game_name = payload.split("_")[1]
              
              send_text(sender_id, "Ok, describe what you are having trouble with in %s." % (game_name))
              
              try:
                conn = mdb.connect('external-db.s4086.gridserver.com', 'db4086_modd_usr', 'f4zeHUga.age', 'db4086_modd');
                with conn:
                  cur = conn.cursor()
                  cur.execute("UPDATE `help_sessions` SET `state` = 5 WHERE `sender_id` = \'%s\' AND `topic_name` = \'%s\' AND `messenger` = \'facebook\' AND `state` < 4 LIMIT 1;" % (sender_id, game_name))
                  cur.execute("INSERT INTO `help_sessions` (`id`, `topic_name`, `chat_id`, `sender_id`, `sender_name`, `messenger`, `added`) VALUES(NULL, \'%s\', \'%s\', \'%s\', \'%s\', \'facebook\', NOW());" % (game_name, sender_id, sender_id, sender_id))

              except mdb.Error, e:
                logger.info("Error %d: %s" % (e.args[0], e.args[1]))

              finally:
                if conn:    
                  conn.close()
                  
            return "ok", 200
          
          # -- !all MESSAGE
          if streamerLowerCase.encode('utf8') == '!all':
            logger.info("found all")
            streamerArray = getStreamers()
            for s in streamerArray:
              subscribersForStreamer[s.lower()].append({'chat_id':sender_id})
              send_text(sender_id, "Your phone will now blow up in 3.. 2.. 1..")
            return "ok", 200
          
          # -- !list MESSAGE
          if streamerLowerCase.encode('utf8') == '!list':
            logger.info("found list")
            streamerString = ''
            streamerArray = getStreamers()
            for s in streamerArray:
              for x in subscribersForStreamer[s.lower()]:
                if x['chat_id'] == sender_id:
                  streamerString = streamerString + " "  + s.lower()
                  send_text(sender_id, streamerString)
            return "ok", 200
             
          # -- FOUND STREAMER
          if streamerLowerCase in subscribersForStreamer:
            send_tracker("bot", "subscribe", "facebook")
            _ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=fb&channel=%s&cid=%s' % (streamerLowerCase, sender_id))
            subscribersForStreamer[streamerLowerCase].append({'chat_id':sender_id})
            if isStreamerOnline(streamerLowerCase):
              link_pic = getStreamerContent("http://beta.modd.live/api/live_streamer.php?channel=" + streamerLowerCase)
              fbSubscribers = subscribersForStreamer[streamerLowerCase]
              send_text(sender_id, "Awesome, " + message_text + " was found and is streaming live! You will begin receiving updates. http://gbots.cc/channel/" + streamerLowerCase)
              send_picture(sender_id, link_pic[0], link_pic[1])
              send_text(sender_id, "Provide me with the name of your favorite player, team, or game and I will subscribe you to more updates like this!")
            
            else:
              send_text(sender_id, "Awesome, " + message_text + " was found and you will begin receiving updates when they go live. http://gbots.cc/channel/" + message_text)
              
              _qr = [{
                'content_type': "text",
                'title': "Overwatch",
                'payload': "hlp_Overwatch"
              }, {
                'content_type': "text",
                'title': "CS:GO",
                'payload': "hlp_CS:GO"
              }, {
                'content_type': "text",
                'title': "League of Legends",
                'payload': "hlp_League of Legends"
              }, {
                'content_type': "text",
                'title': "Dota2",
                'payload': "hlp_Dota2"
              }]

              send_text(sender_id, "Do you currently need help with any of these games?", _qr)
              
          else:
            send_text(sender_id, "Oh no!, " + message_text + " was not found. Provide me with the name of your favorite player, team, or game.")


        

  return "ok", 200


def send_text(recipient_id, message_text, quick_replies=[]):
  logger.info("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))
  data = {
    "recipient": {
      "id": recipient_id
    },
    "message": {
      "text": message_text
    }
  }
  
  if len(quick_replies) > 0:
    data['message']['quick_replies'] = quick_replies
  
  send_message(json.dumps(data))
  

def send_picture(recipient_id, streamerTitle, imageUrl, quick_replies=[]):
  data = {
    "recipient": {
      "id": recipient_id
    },
    "message": {
      "attachment": {
        "type": "template",
        "payload": {
          "template_type": "generic",
          "elements": [{
            "title": "streamcard.tv",
            "subtitle": streamerTitle,
            "item_url": "http://gbots.cc/channel/" + streamerTitle,
            "image_url": imageUrl
          }]
        }
      }
    }
  }
  
  if len(quick_replies) > 0:
    data['message']['quick_replies'] = quick_replies
  
  send_message(json.dumps(data))
  

def send_message(data):
  params = {
    "access_token": Const.ACCESS_TOKEN
  }
  
  headers = {
    "Content-Type": "application/json"
  }

  _r = requests.post("https://graph.facebook.com/v2.6/me/messages", params = params, headers = headers, data = data)
  if _r.status_code != 200:
    logger.info("Error! %s - %s" % (_r.status_code, _r.text))



gameHelpList = {}
help_convos = {}

topics = fetch_topics()
slack_webhooks = fetch_slack_webhooks()


if __name__ == '__main__':
  app.run(debug=True)