import os
import sys
import json
import MySQLdb as mdb
import json
import time
import requests
import urllib2
import logging
import gevent
import random
import sqlite3

import pycurl
import cStringIO


from datetime import date, datetime
from urllib2 import quote
from gevent import monkey; monkey.patch_all()

import const as Const

from flask import Flask, request

app = Flask(__name__)

gevent.monkey.patch_all()

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
Const.ACCESS_TOKEN = "EAAXFDiMELKsBAGLWHgilcmDLRdnrgqwo578YsRnJhMHawMpmC7DAmOolXTFlt79GnobTq8UkXVsVCV2bMkmOiV95IVAngrWcLGmshE4OqtuqmR1rKP7ZCENx0eL6tXKc5hQdxqle4VIVfYqCATNGwLunUNTkdi9htIIHBZAzcZBfoF6TveP"

Const.MAX_IGNORES = 4


#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


def send_tracker(category, action, label):
  logger.info("send_tracker(category={category}, action={action}, label={label})".format(category=category, action=action, label=label))
  
  
  buf = cStringIO.StringIO()
  c = pycurl.Curl()
  c.setopt(c.URL, "http://beta.modd.live/api/bot_tracker.php?category={category}&action={action}&label={label}".format(category=category, action=action, label=label))
  c.setopt(c.WRITEFUNCTION, buf.write)
  c.setopt(c.CONNECTTIMEOUT, 2)
  c.setopt(c.TIMEOUT, 2)
  c.setopt(c.FAILONERROR, True)
  
  try:
    c.perform()
    logger.info("TRACKER response code: {code}".format(code=c.getinfo(c.RESPONSE_CODE)))
    c.close()
  
  except pycurl.error, error:
    errno, errstr = error
    logger.info("Tracker error: -({errno})- {errstr}".format(errno=errno, errstr=errstr))
    
  finally:
    buf.close()
  
  return True
  
  
def slack_send(topic_name, message_txt, from_user="game.bots"):
  logger.info("slack_send(topic_name={topic_name}, message_txt={message_txt}, from_user=%{from_user})".format(topic_name=topic_name, message_txt=message_txt, from_user=from_user))

  _obj = fetch_slack_webhook(topic_name)
  print "SLACK_OBJ:%s" % (_obj)

  payload = json.dumps({
    'channel': "#" + _obj['channel_name'], 
    'username': from_user,
    'icon_url': "http://i.imgur.com/08JS1F5.jpg",
    'text': message_txt
  })
  
  
  buf = cStringIO.StringIO()
  
  c = pycurl.Curl()
  c.setopt(c.HTTPHEADER, ["Content-Type: application/json"])
  c.setopt(c.URL, _obj['webhook'])
  # c.setopt(c.WRITEFUNCTION, buf.write)
  c.setopt(c.POST, 1)
  c.setopt(c.POSTFIELDS, payload)
  c.setopt(c.CONNECTTIMEOUT, 300)
  c.setopt(c.TIMEOUT, 60)
  c.setopt(c.FAILONERROR, True)
  
  try:
    c.perform()
    logger.info("SLACK response code: {code}".format(code=c.getinfo(c.RESPONSE_CODE)))
    c.close()
  
  except pycurl.error, error:
    errno, errstr = error
    print("SEND SLACK Error: -({errno})- {errstr}".format(errno=errno, errstr=errstr))
    
  finally:
    buf.close()
    
    
  return


def write_message_log(sender_id, message_id, message_txt):
  logger.info("write_message_log(sender_id={sender_id}, message_id={message_id}, message_txt={message_txt})".format(sender_id=sender_id, message_id=message_id, message_txt=message_txt))
  
  try:
    conn = mdb.connect(Const.DB_HOST, Const.DB_USER, Const.DB_PASS, Const.DB_NAME);
    with conn:
      cur = conn.cursor()
      cur.execute("INSERT IGNORE INTO `fbbot_logs` (`id`, `message_id`, `chat_id`, `body`) VALUES (NULL, \'{message_id}\', \'{sender_id}\', \'{message_txt}\')".format(message_id=message_id, sender_id=sender_id, message_txt=message_txt))
      
  except mdb.Error, e:
    logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

  finally:
    if conn:    
      conn.close()
  

def start_help(sender_id):
  logger.info("start_help(sender_id={sender_id})".format(sender_id=sender_id))
  send_tracker("bot", "init", "facebook")
  
  session_obj = set_help_session({
    'id': 0,
    'state': 0,
    'sender_id': sender_id,
    'ignore_count': 0,
    'started': time.strftime("%Y-%m-%d %H:%M:%S"),
    'ended': "0000-00-00 00:00:00",
    'topic_name': "N/A",
    'messages': []
  })
  
  send_text(sender_id, "Select a game that you need help with. Type cancel anytime to end this conversation.", topic_quick_replies())
  
  return session_obj


def end_help(session_obj, from_user=True):
  logger.info("end_help(session_obj={session_obj}, from_user={from_user})".format(session_obj=session_obj, from_user=from_user))

  if (from_user):
    slack_send(session_obj['topic_name'], "_Help session closed_ : *{sender_id}*".format(sender_id=session_obj['sender_id']))

  session_obj = set_help_session({
    'id': session_obj['id'],
    'state': 5,
    'sender_id': session_obj['sender_id'],
    'ignore_count': session_obj['ignore_count'],
    'started': session_obj['started'],
    'ended': time.strftime("%Y-%m-%d %H:%M:%S"),
    'topic_name': session_obj['topic_name']
  })
  send_text(session_obj['sender_id'], "This {topic_name} help session is now closed.".format(topic_name=session_obj['topic_name']))
  
  
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
    _arr.append({
      'content_type': "text",
      'title': topic['display_name'],
      'payload': "hlp_%s" % (topic['display_name'])  
    })

  return _arr


def faq_quick_replies():
  return [{
    'content_type': "text",
    'title': "More Details",
    'payload': "faq_more-details"
  }, {
    'content_type': "text",
    'title': "Cancel",
    'payload': "faq_cancel"
  }]


def fetch_faq(topic_name):
  logger.info("fetch_faq(topic_name={topic_name})".format(topic_name=topic_name))

  _arr = []

  try:
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    cur = conn.cursor()
    cur.execute("SELECT faq_content.entry FROM faqs JOIN faq_content ON faqs.id = faq_content.faq_id WHERE faqs.title = \'{topic_name}\';".format(topic_name=topic_name))

    for row in cur.fetchall():
      _arr.append(row[0])

    conn.close()

  except sqlite3.Error as er:
    logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

  finally:
    pass

  return _arr


def help_session_state(sender_id):
  # logger.info("help_session_state(sender_id={sender_id})".format(sender_id=sender_id))
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
        'topic_name': row[2].encode('utf-8'),
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

  try:
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    cur = conn.cursor()

    if session_obj['id'] == 0:
      try:
        cur.execute("INSERT INTO help_sessions (id, sender_id, topic) VALUES (NULL, ?, ?)", (session_obj['sender_id'], session_obj['topic_name']))
        conn.commit()

      except sqlite3.Error as er:
          logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

    else:
      try:
        cur.execute("UPDATE help_sessions SET state = {state}, topic = \'{topic}\', ignore_count=\'{ignore_count}\', started = \'{started}\', ended = \'{ended}\' WHERE id = {id} LIMIT 1".format(state=session_obj['state'], topic=session_obj['topic_name'], ignore_count=session_obj['ignore_count'], started=session_obj['started'], ended=session_obj['ended'], id=session_obj['id']))
        conn.commit()

      except sqlite3.Error as er:
          logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

    conn.close()

  except sqlite3.Error as er:
    logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

  finally:
    pass

  return get_help_session(session_obj['sender_id'])



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
              'state': help_session['state'],
              'sender_id': help_session['sender_id'],
              'ignore_count': 0,
              'started': help_session['started'],
              'ended': help_session['ended'],
              'topic_name': help_session['topic_name']
            })

            if message == "!end" or message.lower() == "cancel" or message.lower() == "quit":
              logger.info("-=- ENDING HELP -=- ({timestamp})".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
              end_chat(help_session, False)

            else:
              send_text(sender_id, "%s coach:\n%s" % (help_session['topic_name'], message))
              

    except mdb.Error, e:
      logger.info("MySqlError {code}: {message}".format(code=e.args[0], message=e.args[1]))

    finally:
      if conn:    
        conn.close()
        
  return "OK", 200
  
  


@app.route('/', methods=['GET'])
def verify():
  logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= VERIFY ({hub_mode})->{request}\n".format(hub_mode=request.args.get('hub.mode'), request=request))
  if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
    if not request.args.get('hub.verify_token') == Const.VERIFY_TOKEN:
      return "Verification token mismatch", 403
    return request.args['hub.challenge'], 200

  return "OK", 200



@app.route('/', methods=['POST'])
def webook():
  data = request.get_json()

  if data['object'] == "page":
    for entry in data['entry']:
      for messaging_event in entry['messaging']:
        if 'delivery' in messaging_event:  # delivery confirmation
          logger.info("-=- DELIVERY CONFIRM -=-")
          return "OK", 200
          
        if 'read' in messaging_event:  # read confirmation
          logger.info("-=- READ CONFIRM -=-")
          send_tracker("bot", "read", "facebook")
          return "OK", 200

        if 'optin' in messaging_event:  # optin confirmation
          logger.info("-=- OPT-IN -=-")
          return "OK", 200

        if 'postback' in messaging_event:  # user clicked/tapped "postback" button in earlier message
          logger.info("-=- POSTBACK RESPONSE -=- (%s)" % (messaging_event['postback']['payload']))
          
          if messaging_event['postback']['payload'] == "WELCOME_MESSAGE":
            sender_id = messaging_event['sender']['id']
            
            logger.info("----------=NEW SESSION @({timestamp})=----------".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
            help_session = start_help(sender_id)
            
          return "OK", 200
        
        
        #-- actual message
        if messaging_event.get('message'):
          logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECIEVED ->{message}".format(message=messaging_event['message']))
          
          #------- IMAGE MESSAGE
          if 'attachments' in messaging_event['message']:
            send_text(messaging_event['sender']['id'], "I'm sorry, I cannot understand that type of message.")
            return "OK", 200

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
          write_message_log(sender_id, message_id, quote(message_text.encode('utf-8')))
              
          
          help_state = help_session_state(sender_id)
          
          if help_state > -1:
            help_session = get_help_session(sender_id)
          
          else:
            help_session = {}
            
          logger.info(":::::::::::]- help_state={help_state}".format(help_state=help_state))
          
          
          #-- typed '!end' / 'cancel' / 'quit'
          if message_text == "!end" or message_text.lower() == "cancel" or message_text.lower() == "quit":
            logger.info("-=- ENDING HELP -=- ({timestamp})".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
            
            if help_state > -1:
              help_session = set_help_session({
                'id': help_session['id'],
                'state': 6,
                'sender_id': help_session['sender_id'],
                'ignore_count': help_session['ignore_count'],
                'started': help_session['started'],
                'ended': time.strftime("%Y-%m-%d %H:%M:%S"),
                'topic_name': help_session['topic_name']
              })
              send_text(help_session['sender_id'], "This {topic_name} help session is now closed.".format(topic_name=help_session['topic_name']))
                        
            return "OK", 200
            
            
          
          #-- non-existant
          if help_state == -1:
            logger.info("----------=NEW SESSION @({timestamp})=----------".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
            help_session = start_help(sender_id)
            
          
          #-- started
          elif help_state == 0:
            logger.info("----------=CREATED SESSION=----------")
            logger.info("help_session={help_session}".format(help_session=help_session))
            
            if quick_reply is None:
              send_text(sender_id, "Select a game that you need help with. Type cancel anytime to end this conversation.", topic_quick_replies())
              
            else:
              help_session = set_help_session({
                'id': help_session['id'],
                'state': 1,
                'sender_id': help_session['sender_id'],
                'ignore_count': 0,
                'started': time.strftime("%Y-%m-%d %H:%M:%S"),
                'ended': help_session['ended'],
                'topic_name': quick_reply.split("_")[-1]
              })
              send_text(sender_id, "Please describe what you need help with. Note your messages will be sent to %s coaches for support." % (help_session['topic_name']))
              
              send_tracker("bot", "subscribe", "facebook")
              
          
          #-- requesting help
          elif help_state == 1:
            logger.info("----------=REQUESTED SESSION=----------")
            send_tracker("bot", "question", "facebook")
            
            slack_send(help_session['topic_name'], "Requesting help: *{sender_id}*\n_\"{message_text}\"_".format(sender_id=sender_id, message_text=message_text), sender_id)
            
            send_text(sender_id, "Locating %s coaches..." % (help_session['topic_name']))
            gevent.sleep(3)
            
            send_text(sender_id, "Locating %s coaches..." % (help_session['topic_name']))
            gevent.sleep(3)
            
            send_text(sender_id, "Your question has been added to the %s queue and will be answered shortly." % (help_session['topic_name']))
            gevent.sleep(2)
            
            send_text(sender_id, "Pro tip: Keep asking questions, each will be added to your queue! Type Cancel to end the conversation.")
            
            help_session = set_help_session({
              'id': help_session['id'],
              'state': 2,
              'sender_id': help_session['sender_id'],
              'ignore_count': help_session['ignore_count'],
              'started': help_session['started'],
              'ended': help_session['ended'],
              'topic_name': help_session['topic_name']
            })
            
            
          #-- in session
          elif help_state == 2:
            logger.info("----------=IN PROGRESS SESSION=----------")
            
            if help_session['ignore_count'] >= Const.MAX_IGNORES - 1:
              logger.info("-=- TOO MANY UNREPLIED - ({count}) CLOSE OUT SESSION -=-".format(count=Const.MAX_IGNORES))
              
              help_session = set_help_session({
                'id': help_session['id'],
                'state': 3,
                'sender_id': help_session['sender_id'],
                'ignore_count': help_session['ignore_count'],
                'started': help_session['started'],
                'ended': time.strftime("%Y-%m-%d %H:%M:%S"),
                'topic_name': help_session['topic_name']
              })
              
              send_text(sender_id, "Sorry! GameBots is taking so long to answer your question. What would you like to do?", faq_quick_replies())
              
            #-- continue convo
            else:
              
              slack_send(help_session['topic_name'], "Requesting help: *{sender_id}*\n_\"{message_text}\"_".format(sender_id=sender_id, message_text=message_text), sender_id)
            
              help_session = set_help_session({
                'id': help_session['id'],
                'state': 2,
                'sender_id': help_session['sender_id'],
                'ignore_count': help_session['ignore_count'] + 1,
                'started': help_session['started'],
                'ended': help_session['ended'],
                'topic_name': help_session['topic_name']
              })
              
          
          #-- display faq
          elif help_state == 3:
            logger.info("----------=FAQ PERIOD=----------")
            
            if quick_reply is None:
              logger.info("----------=PROMPT FOR FAQ ({topic_name})=----------".format(topic_name=help_session['topic_name']))
              send_text(sender_id, "Sorry! GameBots is taking so long to answer your question. What would you like to do?", faq_quick_replies())
              
            else:
              if quick_reply.split("_")[-1] == "more-details":
                for entry in fetch_faq(help_session['topic_name']):
                  send_text(sender_id, entry.encode('utf-8'))
                  gevent.sleep(5)
                  
              else:
                pass
                
                
              send_text(sender_id, "Ok, Thanks for using GameBots!")
                
              help_session = set_help_session({
                'id': help_session['id'],
                'state': 4,
                'sender_id': help_session['sender_id'],
                'ignore_count': help_session['ignore_count'] + 1,
                'started': help_session['started'],
                'ended': help_session['ended'],
                'topic_name': help_session['topic_name']
              })
              
              if quick_reply.split("_")[-1] == "more-details":
                gevent.sleep(3)
                help_session = start_help(help_session['sender_id'])
          
          #-- completed
          elif help_state == 4:
            
            pass
          
              
          # closed by coach    
          elif help_state == 5:
            pass
            
          #-- canceled / quit
          elif help_state == 6:
            send_text(sender_id, "Ok, Thanks for using GameBots!")
            
            
          else:
            pass

  return "OK", 200


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
            "item_url": "http://gbots.cc/channel/{img_url}".format(img_url=streamerTitle),
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
  logger.info("send_message(data={payload})".format(payload=data))
  
  buf = cStringIO.StringIO()
  
  c = pycurl.Curl()
  c.setopt(c.HTTPHEADER, ["Content-Type: application/json"])
  c.setopt(c.URL, "https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Const.ACCESS_TOKEN))
  # c.setopt(c.WRITEFUNCTION, buf.write)
  c.setopt(c.POST, 1)
  c.setopt(c.POSTFIELDS, data)
  c.setopt(c.CONNECTTIMEOUT, 300)
  c.setopt(c.TIMEOUT, 60)
  c.setopt(c.FAILONERROR, True)
  
  try:
    c.perform()
    logger.info("SEND MESSAGE response code: {code}".format(code=c.getinfo(c.RESPONSE_CODE)))
    c.close()
  
  except pycurl.error, error:
    errno, errstr = error
    print("SEND MESSAGE Error: -({errno})- {errstr}".format(errno=errno, errstr=errstr))
  
  finally:
    buf.close()
    
  return True


if __name__ == '__main__':
  app.run(debug=True)
