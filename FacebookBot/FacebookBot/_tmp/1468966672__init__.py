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
Const.ACCESS_TOKEN = "EAAXFDiMELKsBAAqYxESxt9ZBQRaA29Elb4gYfWZCPXFZCAh9kZCE9u0H4Va5LBBW5YIZCy1ikwRc8qSpShvSdkSsZAOuLOWkZBoVB0hUTZArwqSCv2xo68ikbKs873iXR9dvj04Kj91Rb2mR9aTupzEZCtTNr8ZCMS8M3ZChVDNj88HLzHIONK2NqbF"

Const.MAX_IGNORES = 4


#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


class AsyncHTTPHandler(urllib2.HTTPHandler):
  def http_response(self, req, response):
    logger.info("AsyncHTTPHandler.response.geturl({url})".format(url=response.geturl()))
    return response
    

def send_tracker(category, action, label):
  logger.info("send_tracker(category={category}, action={action}, label={label})".format(category=category, action=action, label=label))
  try:
    _response = urllib2.urlopen("http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (str(category), str(action), str(label)), timeout=1)
  
  except urllib2.URLError as e:
    logger.info("GA ERROR! {error}".format(error=e))
        
    return
    # _o = urllib2.build_opener(AsyncHTTPHandler())
    # _t = threading.Thread(target=_o.open, args=("http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (str(category), str(action), str(label)),))
    # _t.start()
  
    # logger.info("--> AsyncHTTPHandler :: _o={obj}".format(obj=_o))
  return
  
  
def slack_send(topic_name, message_txt, from_user="game.bots"):
  _obj = fetch_slack_webhook(topic_name)
  
  payload = json.dumps({
    'channel': "#" + _obj['channel_name'], 
    'username': from_user,
    'icon_url': "http://i.imgur.com/08JS1F5.jpg",
    'text': message_txt
  })

  response = requests.post(_obj['webhook'], data={'payload': payload})
  
  
def fetch_topics():
  logger.info("fetch_topics()")
  _arr = []

  try:
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    cur = conn.cursor()
    cur.execute("SELECT key_name, display_name FROM topics WHERE enabled = 1")

    for row in cur.fetchall():
      _arr.append({
        'key_name': row[0],
        'display_name': row[1]
      })

    conn.close()
    
  except sqlite3.Error as er:
    logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

  finally:
    pass

  return _arr


def fetch_slack_webhook(display_name):
  logger.info("fetch_slack_webhook(display_name={display_name})".format(display_name=display_name))
  _obj = {}
  
  try:
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    cur = conn.cursor()
    cur.execute("SELECT slack_channels.channel_name, slack_channels.webhook FROM slack_channels INNER JOIN topics ON topics__slack_channels.slack_channel_id = topics.id INNER JOIN topics__slack_channels ON topics__slack_channels.topic_id = topics.id AND topics__slack_channels.slack_channel_id = slack_channels.id WHERE topics.display_name = \'{display_name}\';".format(display_name=display_name))

    row = cur.fetchone()
    if row is not None:
      _obj = {
        'channel_name': row[0],
        'webhook': row[1]
      }

    conn.close()
    
  except sqlite3.Error as er:
    logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

  finally:
    pass

  return _obj
  

def topic_quick_replies():
  _arr = []

  for topic in fetch_topics():
    logger.info("QR - {topic}".format(topic=topic))
    _arr.append({
      'content_type': "text",
      'title': topic['display_name'],
      'payload': "hlp_%s" % (topic['display_name'])  
    })

  return _arr


def faq_quick_replies():
  return [{
    'content_type': "text",
    'title': "Yes",
    'payload': "faq_yes"
  }, {
    'content_type': "text",
    'title': "No",
    'payload': "faq_no"
  }]


def fetch_faq(topic_name):
  logger.info("fetch_faq(topic_name={topic_name})".format(topic_name=topic_name))

  _arr = []

  try:
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    cur = conn.cursor()
    cur.execute("SELECT faq_content.entry FROM faqs JOIN faq_content ON faqs.id = faq_content.faq_id WHERE faqs.title = \'%s\'" % (topic_name))

    for row in cur.fetchall():
      _arr.append(row[0])
  
    conn.close()
  
  except sqlite3.Error as er:
    logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

  finally:
    pass

  return _arr


def help_session_state(sender_id):
  logger.info("help_session_state(sender_id={sender_id})".format(sender_id=sender_id))
  help_state = -1

  try:
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    cur = conn.cursor()
    cur.execute("SELECT state FROM help_sessions WHERE sender_id = \'{sender_id}\' AND state < 4 ORDER BY added DESC LIMIT 1".format(sender_id=sender_id))
    row = cur.fetchone()
    
    if row is not None:
      help_state = row[0]

    conn.close()
    logger.info("help_state={help_state}".format(help_state=help_state))
    
  except sqlite3.Error as er:
      logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

  finally:
    pass

  return help_state

def get_help_session(sender_id):
  logger.info("get_help_session(sender_id={sender_id})".format(sender_id=sender_id))
  _obj = {}

  try:
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    cur = conn.cursor()
    cur.execute("SELECT id, state, topic, ignore_count, started, ended, added FROM help_sessions WHERE sender_id = \'{sender_id}\' ORDER BY added DESC LIMIT 1".format(sender_id=sender_id))

    row = cur.fetchone()
    if row is not None:
      _obj = {
        'id': int(row[0]),
        'state': int(row[1]),
        'sender_id': sender_id,
        'topic': row[2].encode('utf-8'),
        'ignore_count': row[3],
        'started': row[4],
        'ended': row[5],
        'added': row[6]
      }

    conn.close()
    
  except sqlite3.Error as er:
    logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

  finally:
    pass

  return _obj
  
  
def set_help_session(session_obj):
  logger.info("set_help_session(session_obj={session_obj})".format(session_obj=session_obj))
  action = "NONE"
  
  try:
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    cur = conn.cursor()
    
    if session_obj['id'] == 0:
      try:
        cur.execute("INSERT INTO help_sessions (id, sender_id, topic) VALUES (NULL, ?, ?)", (session_obj['sender_id'], session_obj['topic']))
        conn.commit()
        
      except sqlite3.Error as er:
          logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

    else:
      try:
        cur.execute("UPDATE help_sessions SET state = {state}, topic = \'{topic}\', ignore_count=\'{ignore_count}\', started = \'{started}\', ended = \'{ended}\' WHERE id = {id} LIMIT 1".format(state=session_obj['state'], topic=session_obj['topic'], ignore_count=session_obj['ignore_count'], started=session_obj['started'], ended=session_obj['ended'], id=session_obj['id']))
        conn.commit()
        
      except sqlite3.Error as er:
          logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))
      
    conn.close()
      
  except sqlite3.Error as er:
    logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

  finally:
    pass
    
  return get_help_session(session_obj['sender_id'])


def start_chat(sender_id):
  session_obj = set_help_session({
    'id': 0,
    'state': 0,
    'sender_id': sender_id,
    'topic': ""
  })
  
  help_session = get_help_session(sender_id)
  logger.info("help_session={help_session}".format(help_session=help_session))
  send_text(sender_id, "Select a game you need help with...", topic_quick_replies())



def end_chat(session_obj, from_user=True):
  logger.info("end_chat(session_obj={session_obj})".format(session_obj=session_obj))
  
  if (from_user):
    slack_send(session_obj['topic'], "_Help session closed_ : *%s*" % (session_obj['sender_id']), session_obj['sender_id'])
    
  session_obj = set_help_session({
    'id': session_obj['id'],
    'state': 4,
    'sender_id': session_obj['sender_id'],
    'ignore_count': session_obj['ignore_count'],
    'started': session_obj['started'],
    'ended': time.strftime("%Y-%m-%d %H:%M:%S"),
    'topic': session_obj['topic']
  })
  send_text(session_obj['sender_id'], "This %s help session is now closed." % (session_obj['topic']))
  

def send_text(recipient_id, message_text, quick_replies=[]):
  logger.info("send_text(recipient_id={recipient_id}, message_text={message_text}, quick_replies={quick_replies})".format(recipient_id=recipient_id, message_text=message_text, quick_replies=quick_replies))
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


def send_picture(recipient_id, subtitle, image_url, quick_replies=[]):
  logger.info("send_picture(recipient_id={recipient_id}, subtitle={subtitle}, image_url={image_url}, quick_replies={quick_replies})".format(recipient_id=recipient_id, subtitle=subtitle, image_url=image_url, quick_replies=quick_replies))

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
            "subtitle": subtitle,
            "item_url": "http://gbots.cc/channel/" + streamerTitle,
            "image_url": image_url
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
    logger.info("Error! {status} - {message}".format(status=_r.status_code, message=_r.text))


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #


@app.route('/slack', methods=['POST'])
def slack():
  logger.info("=-=-=-=-=-=-=-=-=-=-= SLACK RESPONSE =-=-=-=-=-=-=-=-=-=-=")  
  logger.info("{form}".format(form=request.form))
  if request.form.get('token') == "uKA7dgfnfadLN4QApLYmmn4m":
    help_session = {}
    
    _arr = request.form.get('text').split(' ')
    _arr.pop(0)
    
    sender_id = _arr[0]
    _arr.pop(0)
    
    message = " ".join(_arr).replace("'", "")
    
    try:
      conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
      with conn:
        cur = conn.cursor(mdb.cursors.DictCursor)
        cur.execute("SELECT `id` FROM `fbbot_logs` WHERE `chat_id` = '%s' ORDER BY `added` DESC LIMIT 1;" % (sender_id))

        if cur.rowcount == 1:
            help_session = get_help_session(sender_id)
            help_session = set_help_session({
              'id': help_session['id'],
              'state': 2,
              'sender_id': help_session['sender_id'],
              'ignore_count': 0,
              'started': help_session['started'],
              'ended': help_session['ended'],
              'topic': help_session['topic']
            })

            if message == "!end":
              logger.info("-=- ENDING HELP -=- ({timestamp})".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
              end_chat(help_session, False)
              time.sleep(3)
              start_chat(sender_id)

            else:
              send_text(sender_id, "%s helper:\n%s" % (help_session['topic'], message))
              

    except mdb.Error, e:
      logger.info("MySqlError {code}: {message}".format(code=e.args[0], message=e.args[1]))

    finally:
      if conn:    
        conn.close()
        
  return "OK", 200


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #


@app.route('/notify', methods=['GET'])
def notify():
  logger.info("-=- /notify -=- ")

  streamerName = request.args.get('streamer')
  fbMessage = request.args.get('message')
  logger.info("streamer:{streamer}".format(streamer=streamerName))
  logger.info("message:{message}".format(message=fbMessage))

  link_pic = getStreamerContent("http://beta.modd.live/api/live_streamer.php?channel=" + streamerName)
  fbSubscribers = subscribersForStreamer[streamerName]
  for chat in fbSubscribers:
    send_tracker("bot", "send", "facebook")
    send_text(chat['chat_id'], fbMessage)
    send_picture(chat['chat_id'], link_pic[0], link_pic[1])

  return "OK", 200


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #


@app.route('/', methods=['GET'])
def verify():
  logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= VERIFY ({mode})-> {verify_token}".format(mode=request.args.get('hub.mode'), verify_token=request.args.get('hub.verify_token')))
  if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
    if not request.args.get('hub.verify_token') == Const.VERIFY_TOKEN:
      return "Verification token mismatch", 403
    return request.args['hub.challenge'], 200

  return "Hello world", 200


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #


@app.route('/', methods=['POST'])
def webook():
  data = request.get_json()
  
  logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= [POST]-> /\n{body}".format(body=data))
  if data['object'] == "page":
    for entry in data['entry']:
      for messaging_event in entry['messaging']:
        if messaging_event.get("delivery"):  # delivery confirmation
          logger.info(" -=- DELIVERY CONFIRM -=-")
          return "ok", 200
          
        if messaging_event.get("read"):  # read confirmation
          logger.info(" -=- READ CONFIRM -=-")
          send_tracker("bot", "read", "facebook")
          return "ok", 200

        if messaging_event.get("optin"):  # optin confirmation
          logger.info(" -=- OPT-IN -=-")
          return "ok", 200

        if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
          logger.info(" -=- POSTBACK RESPONSE -=-")
          return "ok", 200
        
        #//return "ok", 200
        #-- actual message
        if messaging_event.get('message'):
          logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECIEVED ->\n{message}".format(message=messaging_event['message']))
          
          #------- IMAGE MESSAGE
          #if messaging_event['message']['type'] == "image":
          #  return "ok", 200

          # MESSAGE CREDENTIALS
          sender_id = messaging_event['sender']['id']        # the facebook ID of the person sending you the message
          recipient_id = messaging_event['recipient']['id']  # the recipient's ID, which should be your page's facebook ID
          message_id = messaging_event['message']['mid']
          message_text = messaging_event['message']['text']  # the message's text
          timestamp = messaging_event['timestamp']
          quick_reply = None
          
          if 'quick_reply' in messaging_event['message']:
            logger.info("QR --> {quick_replies}".format(quick_replies=messaging_event['message']['quick_reply']['payload'].encode('utf-8')))
            quick_reply = messaging_event['message']['quick_reply']['payload'].encode('utf-8')

          
          #-- insert to log
          try:
            conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
            with conn:
              cur = conn.cursor()
              cur.execute("INSERT IGNORE INTO `fbbot_logs` (`id`, `message_id`, `chat_id`, `body`) VALUES (NULL, \'%s\', \'%s\', \'%s\')" % (message_id, sender_id, message_text))
              
          except mdb.Error, e:
            logger.info("MySqlError {code}: {message}".format(code=e.args[0], message=e.args[1]))

          finally:
            if conn:    
              conn.close()
              
          
          help_state = help_session_state(sender_id)
          logger.info("help_state={help_state}".format(help_state=help_state))
          
          
          #-- typed '!end'
          if message_text == "!end":
            logger.info("-=- ENDING HELP -=- ({timestamp})".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
            end_chat(get_help_session(sender_id), )
            time.sleep(3)
            return "ok", 200
          
          
          #-- non-existant
          if help_state == -1:
            logger.info("----------=NEW SESSION=----------")
            
            help_session = set_help_session({
              'id': 0,
              'state': 0,
              'sender_id': sender_id,
              'topic': ""
            })
            
          
          #-- started
          elif help_state == 0:
            logger.info("----------=CREATED SESSION=----------")
            help_session = get_help_session(sender_id)
            logger.info("help_session={help_session}".format(help_session=help_session))
            
            if quick_reply is None:
              send_text(sender_id, "Select a game you need help with...", topic_quick_replies())
              
            else:
              help_session = set_help_session({
                'id': help_session['id'],
                'state': 1,
                'sender_id': help_session['sender_id'],
                'ignore_count': 0,
                'started': time.strftime("%Y-%m-%d %H:%M:%S"),
                'ended': help_session['ended'],
                'topic': quick_reply.split("_")[-1]
              })
              send_text(sender_id, "Please describe what you need help with?")
            
            
          #-- requesting help
          elif help_state == 1:
            logger.info("----------=REQUESTED SESSION=----------")
            help_session = get_help_session(sender_id)
            
            #slack_send(help_session['topic'], "Requesting help: *%s*\n_\"%s\"_" % (sender_id, message_text), sender_id)
            
            send_text(sender_id, "Locating %s coaches..." % (help_session['topic']))
            time.sleep(3)
            
            send_text(sender_id, "Locating %s coaches..." % (help_session['topic']))
            time.sleep(3)
            
            send_text(sender_id, "Your question has been added to the %s queue and will be answered shortly." % (help_session['topic']))
            send_text(sender_id, "Pro tip: you can keep asking questions, each will be added to your session and answered shortly.")
            
            help_session = set_help_session({
              'id': help_session['id'],
              'state': 2,
              'sender_id': help_session['sender_id'],
              'ignore_count': help_session['ignore_count'],
              'started': help_session['started'],
              'ended': help_session['ended'],
              'topic': help_session['topic']
            })
                    
                    
          #-- in session
          elif help_state == 2:
            logger.info("----------=STARTED SESSION=----------")
            
            help_session = get_help_session(sender_id)
            
            if help_session['ignore_count'] >= Const.MAX_IGNORES - 1:
              logger.info("-=- TOO MANY UNREPLIED - ({count}) CLOSE OUT SESSION -=-".format(count=Const.MAX_IGNORES))
              
              help_session = set_help_session({
                'id': help_session['id'],
                'state': 3,
                'sender_id': help_session['sender_id'],
                'ignore_count': help_session['ignore_count'],
                'started': help_session['started'],
                'ended': time.strftime("%Y-%m-%d %H:%M:%S"),
                'topic': help_session['topic']
              })
              
              send_text(sender_id, "Sorry this is taking so long... Would you like to read some general details about %s?" % (help_session['topic']), faq_quick_replies())
              #return "ok", 200
              
            #-- continue convo
            else:
              #slack_send(help_session['topic'], "Requesting help: *%s*\n_\"%s\"_" % (sender_id, message_text), sender_id)
            
              help_session = set_help_session({
                'id': help_session['id'],
                'state': 2,
                'sender_id': help_session['sender_id'],
                'ignore_count': help_session['ignore_count'] + 1,
                'started': help_session['started'],
                'ended': help_session['ended'],
                'topic': help_session['topic']
              })
              
          
          #-- faq pending
          elif help_state == 3:
            logger.info("----------=FAQ PENDING=----------")
            help_session = get_help_session(sender_id)
            
            if quick_reply is None:
              send_text(sender_id, " ", faq_quick_replies())
              
            else:
              faq_arr = fetch_faq(help_session['topic'])
              
              help_session = set_help_session({
                'id': help_session['id'],
                'state': 4,
                'sender_id': help_session['sender_id'],
                'ignore_count': help_session['ignore_count'],
                'started': help_session['started'],
                'ended': help_session['ended'],
                'topic': help_session['topic']
              })
              
              if quick_reply.split("_")[-1] == "yes":
                for entry in faq_arr:
                  send_text(sender_id, entry.encode('utf-8'))
                  time.sleep(4)
                                    
              time.sleep(3)
              start_chat(sender_id)
          
          
          #-- closed session
          elif help_state == 4:
            logger.info("----------=CLOSED SESSION=----------")
            start_chat(sender_id)
            
            
          #-- other state
          else:
            logger.info("----------=UNKNOWN STATE=----------")
            start_chat(sender_id)
          
          return "ok", 200
  return "ok", 200


# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #


Const.DB_HOST = 'external-db.s4086.gridserver.com'
Const.DB_NAME = 'db4086_modd'
Const.DB_USER = 'db4086_modd_usr'
Const.DB_PASS = 'f4zeHUga.age'

Const.VERIFY_TOKEN = "ae9118876b91ea88def1259cc13ff2ca"
Const.ACCESS_TOKEN = "EAAXFDiMELKsBAAqYxESxt9ZBQRaA29Elb4gYfWZCPXFZCAh9kZCE9u0H4Va5LBBW5YIZCy1ikwRc8qSpShvSdkSsZAOuLOWkZBoVB0hUTZArwqSCv2xo68ikbKs873iXR9dvj04Kj91Rb2mR9aTupzEZCtTNr8ZCMS8M3ZChVDNj88HLzHIONK2NqbF"

Const.MAX_IGNORES = 4


#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


if __name__ == '__main__':
  app.run(debug=True)
