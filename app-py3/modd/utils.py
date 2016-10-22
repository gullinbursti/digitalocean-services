#!/usr/bin/env python

import hashlib
import json
import time

import grequests
import requests

def lan_ip():
  return "0.0.0.0"


def send_evt_tracker(category="", action="", label="", value=0):
  print("send_evt_tracker(category=%s, action=%s, label=%s, value=%d)" % (category, action, label, value))
  
  urls = [
    "http://beta.modd.live/api/user_tracking.php?username={username}&chat_id={chat_id}".format(username=label, chat_id=action),
    "http://beta.modd.live/api/bot_tracker.php?src=kik&category={category}&action={action}&label={label}&value={value}&cid={cid}".format(category=category, action=hashlib.md5(label.encode()).hexdigest(), label=label, value=value, cid=hashlib.md5(label.encode()).hexdigest())
  ]
  
  responses = (grequests.get(u) for u in urls)
  grequests.map(responses)
  
  # response = requests.get("http://beta.modd.live/api/user_tracking.php?username={username}&chat_id={chat_id}".format(username=label, chat_id=action))
  # response = requests.get("http://beta.modd.live/api/bot_tracker.php?src=kik&category={category}&action={action}&label={label}&value={value}&cid={cid}".format(category=category, action=hashlib.md5(label.encode()).hexdigest(), label=label, value=value, cid=hashlib.md5(label.encode()).hexdigest()))
  # if response.status_code != 200:
  #   print("GA ERROR!!")
  #   
  # return response.status_code == 200
  

def async_send_evt_tracker(urls):
  print("send_evt_tracker(len(urls)=%d)" % (len(urls)))
  
  responses = (grequests.get(u) for u in urls)
  grequests.map(responses)  
  

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
    