#!/usr/bin/env python

import hashlib
import json
import time

import io
import requests
import pycurl


def lan_ip():
  return "0.0.0.0"


def send_evt_tracker(category="", action="", label="", value=0):
  print("send_evt_tracker(category=%s, action=%s, label=%s, value=%d)" % (category, action, label, value))
  
  response = requests.get("http://beta.modd.live/api/user_tracking.php?username={username}&chat_id={chat_id}".format(username=label, chat_id=action))
  response = requests.get("http://beta.modd.live/api/bot_tracker.php?src=kik&category={category}&action={action}&label={label}&value={value}&cid={cid}".format(category=category, action=hashlib.md5(label.encode()).hexdigest(), label=label, value=value, cid=hashlib.md5(label.encode()).hexdigest()))
  if response.status_code != 200:
    print("GA ERROR!!")
    
  return response.status_code == 200
  
  
def send_botanalytics(chat_id, txt_message):
  print("send_botanalytics(chat_id={chat_id}, txt_message={txt_message})".format(chat_id=chat_id, txt_message=txt_message))
  
  payload = {
    'recipient' : chat_id,
    'timestamp' : int(time.time()),
    'token'     : "9d75077d09e99dd37293112b82ef7b43",
    'message'   : txt_message
  }
  
  response = requests.post("http://botanalytics.co/api/v1/track", headers={ 'Content-Type' : 'application/json' }, data=json.dumps(payload))
  print(response.text)
  
def send_dashbot(to_user, from_user, chat_id, msg_type, body, direction="outgoing"):
  print("send_dashbot(to_user={to_user}, from_user={from_user}, chat_id={chat_id}, msg_type={msg_type}, body={body}, direction={direction})".format(to_user=to_user, from_user=from_user, chat_id=chat_id, msg_type=msg_type, body=body, direction=direction))
  
  params = {
    'platform'  : "kik",
    'v'         : "0.7.3-rest",
    'type'      : direction,
    'apiKey'    : "gFCj3t6ZfNyUa8ryOpewPqmzFIg54iofhD6sKUQq"
  }
  
  payload = {
    'apiKey'    :"gFCj3t6ZfNyUa8ryOpewPqmzFIg54iofhD6sKUQq",
    'username'  : from_user,
    'message'   : {
      'type'    : msg_type,
      'body'    : body,
      'to'      : to_user,
      'chatId'  : chat_id
    }
  }
  
  response = requests.post("https://tracker.dashbot.io/track", params=params, data=json.dumps(payload))
  print(response.text)
  
  
   
def slack_im(convo, message):
  print("slack_im(convo=%s, message=%s)" % (convo, message))

  message_body = "*{from_user}* from _Kik_ says:\n_\"{message}\"_".format(from_user=convo['username'], message=message)
  response = requests.get("https://slack.com/api/chat.postMessage?token=xoxb-62712469858-QAmGTuRLktyYuMI79193Kfow&channel={im_channel}&text={message_body}&as_user=true&pretty=1".format(im_channel=convo['im_channel'], message_body=message_body))
  return


def slack_send(convo, message_txt, from_user="game.bots"):
  print("slack_send(convo=%s, message_txt=%s, from_user=%s)" % (convo, message_txt, from_user))

  webhooks = {
    b'Pok\xc3\xa9mon Go'  : "https://hooks.slack.com/services/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",
    b'Dota 2'             : "https://hooks.slack.com/services/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",
    b'League of Legends'  : "https://hooks.slack.com/services/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",
    b'CS:GO'              : "https://hooks.slack.com/services/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",
    b'Hearthstone'        : "https://hooks.slack.com/services/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"
    #b'Become a Moderator' : "https://hooks.slack.com/services/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"
  }

  payload = json.dumps({
    'text'        : "*%s* from _Kik_ is requesting %s help..." % (from_user, convo['game']), 
    'attachments' : [{
      'text'            : message_txt,
      'fallback'        : message_txt,
      'callback_id'     : "kik_{chat_id}_{from_user}".format(chat_id=convo['chat_id'], from_user=from_user),
      'color'           : "#3AA3E3",
      'attachment_type' : "default",
      'actions'         : [{
        'name'  : "Yes",
        'text'  : "Yes",
        'type'  : "button",
        'value' : "yes"
      }, {
        'name'  : "No",
        'text'  : "No",
        'type'  : "button",
        'value' : "no"
      }]
    }]
  })
  
  response = requests.post(webhooks[convo['game'].encode('utf-8')], data=payload)
  return
    