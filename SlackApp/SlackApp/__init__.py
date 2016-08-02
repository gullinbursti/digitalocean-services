import os
import sys
import json
import json
import time
import requests
import unirest
import urllib
import urllib2
import logging
import random
import sqlite3

import websocket
import thread

import pycurl

from datetime import date, datetime
from urllib2 import quote

import const as Const

from flask import Flask, request
app = Flask(__name__)



logger = logging.getLogger(__name__)
hdlr = logging.FileHandler('/var/log/SlackApp.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)

#websocket.enableTrace(True)


Const.DB_HOST = 'external-db.s4086.gridserver.com'
Const.DB_NAME = 'db4086_modd'
Const.DB_USER = 'db4086_modd_usr'
Const.DB_PASS = 'f4zeHUga.age'

Const.WEBHOOK_KIKBOT = 'http://159.203.250.4:8080'
Const.WEBHOOK_FBBOT = 'https://gamebot.tv'

Const.SLACK_FORM_TOKEN = 'gh8BzyQqu0tVK2cot58iqJFN'
Const.SLACK_AUTH_TOKEN = 'xoxb-62712469858-QAmGTuRLktyYuMI79193Kfow'

Const.WEBHOOK_CSGO = 'https://hooks.slack.com/services/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'
Const.WEBHOOK_DOTA2 = 'https://hooks.slack.com/services/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'
Const.WEBHOOK_POKEMON = 'https://hooks.slack.com/services/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'
Const.WEBHOOK_LOL = 'https://hooks.slack.com/services/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'
Const.WEBHOOK_GENERAL = 'https://hooks.slack.com/services/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'

def on_message(ws, message):
  logger.info("WS:MESSAGE :::::::::::::{message}".format(message=message))
  message_json = json.loads(message)
  
  # message contains a user / channel / text
  if 'user' in message_json and 'channel' in message_json and 'text' in message_json:  
    try:
      conn = sqlite3.connect("{script_path}/data/sqlite3/slackbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
      cur = conn.cursor()
      cur.execute("SELECT id, user_id, username, org_message, topic_name, messenger, chat_id, response_url, im_channel, added FROM sessions WHERE user_id = \'{user_id}\' ORDER BY added DESC LIMIT 1".format(user_id=message_json['user']))

      row = cur.fetchone()
      if row is not None:
        payload = {
          'token': "IJApzbM3rVCXJhmkSzPlsaS9",
          'text': "%s %s %s" % (row[5], row[6], message_json['text'])
        }
        
        response = requests.post("{webhook}/slack".format(webhook=Const.WEBHOOK_KIKBOT), data=payload)
        
        
        # payload = json.dumps({
        #   'id': int(time.time()),
        #   'type': "message",
        #   'channel': message_json['channel'],
        #   'text': message_json['text']
        # })
        # ws.send(payload)

      conn.close()

    except sqlite3.Error as er:
      logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

    finally:
      pass
    
    
def on_error(ws, error):
  logger.info("WS:ERROR :::::::::::::{error}".format(error=error))

def on_close(ws):
  logger.info("WS:CLOSED :::::::::::::")

def on_open(ws):
  def run(*args):
    pass
        
  thread.start_new_thread(run, ())
    
    
def open_ws():
  logger.info("WS:INIT :::::::::::::")
  
  response = requests.get("https://slack.com/api/rtm.start?token={auth_token}&pretty=1".format(auth_token=Const.SLACK_AUTH_TOKEN))
  if response.status_code == 200:
    rtm_data = json.loads(response.text)
    logger.info("RTAPI:%s" % (rtm_data['url']))
    
    ws = websocket.WebSocketApp(rtm_data['url'], on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()
  


@app.route("/", methods=['GET'])
def root():
  logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= ROOT =-=-=-=-=-=-=-=-=-=-=-=-=")
  logger.info("{request}".format(request=request))
  return "OK", 200



@app.route("/oauth", methods=['GET'])
def oauth():
  logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= OAUTH =-=-=-=-=-=-=-=-=-=-=-=-=")
  logger.info("{request}".format(request=request))
  return "OK", 200



@app.route("/button", methods=['POST'])
def button():
  logger.info("=-=-=-=-=-=-=-=-=-=-= SLACK BUTTON =-=-=-=-=-=-=-=-=-=-=")  
  logger.info("{payload}".format(payload=json.loads(request.form['payload'])))
  
  data = json.loads(request.form['payload'])
  action = data['actions'][0]['value']
  
  if data['token'] == Const.SLACK_FORM_TOKEN:
    if action == "yes":
      user_id = data['user']['id']
      username = data['user']['name']    
      org_message = data['original_message']['attachments'][0]['text']
      topic_name = data['original_message']['text'].split(" ")[2]
      response_url = data['response_url']
    
      messenger = ""
      chat_id = data['callback_id'].split("_")[1]
      from_user = data['callback_id'].split("_")[-1]
      
      if data['callback_id'].split("_")[0] == "fb":
        messenger = "Facebook"
        
      elif data['callback_id'].split("_")[0] == "kik":
        messenger = "Kik"
    
    
    
      response_txt = "{username} has checked out *{from_user}*\'s question:\n_\"{org_message}\"_".format(username=username, from_user=from_user, org_message=org_message)
      dm_txt = quote("Now replying to *{from_user}* from _{messenger}_:\n_\"{org_message}\"_".format(from_user=from_user, messenger=messenger, org_message=org_message))
      
      
      
      response = requests.get("https://slack.com/api/chat.postMessage?token={auth_token}&channel={user_id}&text={message}&as_user=true&pretty=1".format(auth_token=Const.SLACK_AUTH_TOKEN, user_id=user_id, message=dm_txt))
      if response.status_code != 200:
        logger.info("POST MESSAGE ERROR:")
        
      else:
        logger.info("postMessage:%s" % (json.loads(response.text)))
        post_json = json.loads(response.text)
        im_channel = post_json['channel']
        
        
        payload = json.dumps({
          'chat_id': chat_id, 
          'channel': im_channel
        })
        
        thread = unirest.post("{webhook}/im".format(webhook=Const.WEBHOOK_KIKBOT), params=payload)
        #response = requests.post("{webhook}/im".format(webhook=Const.WEBHOOK_KIKBOT), data=payload)
        
        
        try:
          conn = sqlite3.connect("{script_path}/data/sqlite3/slackbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
          cur = conn.cursor()

          try:
            cur.execute("INSERT INTO sessions (id, user_id, username, org_message, topic_name, messenger, chat_id, response_url, im_channel, added) VALUES (NULL, ?, ?, ? ,?, ?, ?, ?, ?, ?)", (user_id, username, org_message, topic_name, messenger, chat_id, response_url, im_channel, int(time.time())))
            conn.commit()

          except sqlite3.Error as er:
              logger.info("::::::[cur.execute] sqlite3.Error - {message}".format(message=er.message))

          conn.close()

        except sqlite3.Error as er:
          logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))

        finally:
          pass
          
      return response_txt, 200
        
    else:
      return "OK", 200
    
  else:
    return "Unknown referer", 200



@app.route("/command/<command>", methods=['POST'])
def commands(command):
  logger.info("=-=-=-=-=-=-=-=-=-=-= command/{command} =-=-=-=-=-=-=-=-=-=-=".format(command=command))  
  logger.info("{form}".format(form=request.form))
  
  if request.form['token'] == Const.SLACK_FORM_TOKEN:
    payload = {}
    
    if request.form['command'] == "/done":
      user_id = request.form['user_id']
      
      im_channel = request.form['channel_id']
      
      # try:
      #         conn = sqlite3.connect("{script_path}/data/sqlite3/slackbot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
      #         cur = conn.cursor()
      #         cur.execute("SELECT id, user_id, username, org_message, topic_name, messenger, chat_id, response_url, im_channel, added FROM sessions WHERE user_id = \'{user_id}\' ORDER BY added DESC LIMIT 1".format(user_id=user_id))
      # 
      #         row = cur.fetchone()
      #         if row is not None:
      #           payload = {
      #             'token': "IJApzbM3rVCXJhmkSzPlsaS9",
      #             'text': "%s %s %s" % (row[5], row[6], "quit")
      #           }
      #           
      url = "https://slack.com/api/chat.postMessage?token=xoxb-62712469858-QAmGTuRLktyYuMI79193Kfow&channel={im_channel}&as_user=true&text=Your%20session%20with%20{topic_name}%20has%20been%20closed...&attachments=%5B%7B'text'%3A%22Please%20add%20tags%20%26%20vote%20the%20quality%20of%20this%20session%22%2C'fallback'%3A%22Please%20add%20tags%20%26%20vote%20the%20quality%20of%20this%20session%22%2C'callback_id'%3A%22kik_0000_username%22%2C'color'%3A%22%233AA3E3%22%2C'attachment_type'%3A%22default%22%2C'actions'%3A%5B%7B'name'%3A%22Button1%22%2C'text'%3A%221%20Star%22%2C'type'%3A%22button%22%2C'value'%3A%22btn1%22%7D%2C%7B'name'%3A%22Button2%22%2C'text'%3A%222%20Star%22%2C'type'%3A%22button%22%2C'value'%3A%22btn2%22%7D%2C%7B'name'%3A%22Button3%22%2C'text'%3A%223%20Star%22%2C'type'%3A%22button%22%2C'value'%3A%22btn3%22%7D%2C%7B'name'%3A%22Button4%22%2C'text'%3A%224%20Star%22%2C'type'%3A%22button%22%2C'value'%3A%22btn4%22%7D%2C%7B'name'%3A%22Button5%22%2C'text'%3A%225%20Star%22%2C'type'%3A%22button%22%2C'value'%3A%22btn5%22%7D%5D%7D%5D&pretty=1".format(im_channel=im_channel, topic_name="_Kik_")
      thread = unirest.get(url)
        
      #   conn.close()
      # 
      # except sqlite3.Error as er:
      #   logger.info("::::::[sqlite3.connect] sqlite3.Error - {message}".format(message=er.message))
      # 
      # finally:
      #   pass
      #     
      # if payload is not None:
      #   thread = unirest.post("{webhook}/slack".format(webhook=Const.WEBHOOK_KIKBOT), params=payload)
      #   #response = requests.post("{webhook}/slack".format(webhook=Const.WEBHOOK_KIKBOT), data=payload)
        
      return "_Help session closed._", 200
    
    return "", 200
  return "", 200
  


@app.before_first_request
def before_first_request():
  thread.start_new_thread(open_ws, ())
  
  
@app.after_request
def after_request(response):
    # Do something with the response (invalidate cache, alter response object, etc)
    return response
  


if __name__ == "__main__":
  app.secret_key = "\xef\xf0\xe9c\x9d}4\x8c\x03oZ$\x85v\x89t\x8b\xe9\xc5o.\x0f\xe2\xb9"
  app.run()
