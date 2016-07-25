import os
import sys
import json
import MySQLdb as mdb
import json
import time
import requests
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

websocket.enableTrace(True)


Const.DB_HOST = 'external-db.s4086.gridserver.com'
Const.DB_NAME = 'db4086_modd'
Const.DB_USER = 'db4086_modd_usr'
Const.DB_PASS = 'f4zeHUga.age'



def on_message(ws, message):
  logger.info("WS:MESSAGE :::::::::::::{message}".format(message=message))
  message_json = json.loads(message)
  
  if 'user' in message_json and 'channel' in message_json and 'text' in message_json:
    if message_json['user'] == "U1REBEF53":
      payload = json.dumps({
        'id': int(time.time()),
        'type': "message",
        'channel': message_json['channel'],
        'text': message_json['text']
      })
      ws.send(payload)
      # ws.close()

def on_error(ws, error):
  logger.info("WS:ERROR :::::::::::::{error}".format(error=error))

def on_close(ws):
  logger.info("WS:CLOSED :::::::::::::")

def on_open(ws):
  def run(*args):
    pass
        
  thread.start_new_thread(run, ())
    

def open_ws(channel):
  logger.info("WS:INIT :::::::::::::{channel}".format(channel=channel))
  
  response = requests.get("https://slack.com/api/rtm.start?token=xoxb-62712469858-QAmGTuRLktyYuMI79193Kfow&pretty=1")
  if response.status_code == 200:
    rtm_data = json.loads(response.text)
    logger.info("RTAPI:%s" % (rtm_data['url']))
    
    ws = websocket.WebSocketApp(rtm_data['url'], on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever()
    sockets[channel] = ws
  


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
  if data['token'] == "gh8BzyQqu0tVK2cot58iqJFN":
    
    user_id = data['user']['id']
    username = data['user']['name']
    action = data['actions'][0]['value']
    org_message = data['original_message']['attachments'][0]['text']
    topic_name = data['original_message']['text'].split(" ")[0]
    response_url = data['response_url']
    
    if action == "yes":
      messenger = ""
      chat_id = data['callback_id'].split("_")[-1]
      
      if data['callback_id'].split("_")[0] == "fb":
        messenger = "Facebook"
        
      elif data['callback_id'].split("_")[0] == "kik":
        messenger = "Kik"
    
      response_txt = "{username} has checked out the {topic_name} question _\"{org_message}\"_.".format(username=username, topic_name=topic_name, org_message=org_message)
      dm_txt = quote("Now replying to _{chat_id}_ from *{messenger}*:".format(chat_id=chat_id, messenger=messenger))
      
      
      response = requests.get("https://slack.com/api/chat.postMessage?token=xoxb-62712469858-QAmGTuRLktyYuMI79193Kfow&channel={user_id}&text={message}&as_user=true&pretty=1".format(user_id=user_id, message=dm_txt))
      if response.status_code != 200:
        logger.info("POST MESSAGE ERROR:")
        
      else:
        logger.info("postMessage:%s" % (json.loads(response.text)))
        post_json = json.loads(response.text)
        im_channel = post_json['channel']
      
      
      thread.start_new_thread(open_ws, (im_channel,))
      
      return response_txt, 200
        
    else:
      return "", 200
    
  else:
    return "Unknown referer", 200



@app.route("/command/<command>", methods=['POST'])
def commands(command):
  logger.info("=-=-=-=-=-=-=-=-=-=-= command/{command} =-=-=-=-=-=-=-=-=-=-=".format(command=command))  
  logger.info("{form}".format(form=request.form))
  
  if request.form['token'] == "gh8BzyQqu0tVK2cot58iqJFN":
    if request.form['command'] == "/done":
      ws = sockets[request.form['channel_id']]
      ws.close()
    
    return "OK", 200
    
  else:
    return "", 200
  


sockets = {}


if __name__ == "__main__":
  app.run()
