#!/usr/bin/env python

import json

import cStringIO
import requests
import pycurl


def lan_ip():
  return "0.0.0.0"


def sendTracker(category, action, label):
  print "sendTracker(category=%s, action=%s, label=%s)" % (category, action, label)
    
  buf = cStringIO.StringIO()
  c = pycurl.Curl()
  c.setopt(c.URL, "http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (category, action, label))
  c.setopt(c.WRITEFUNCTION, buf.write)
  c.setopt(c.CONNECTTIMEOUT, 5)
  c.setopt(c.TIMEOUT, 8)
  c.setopt(c.FAILONERROR, True)
   
  try:
    c.perform()
    print "buf.getVal()=%s" % (buf.getValue())
    buf.close()
  
  except:
    print("GA ERROR!")
  
  return True
  
  
def slack_im(convo, message):
  print "slack_im(convo=%s, message=%s)" % (convo, message)

  message_body = "*{from_user}* from _Kik_ says:\n_\"{message}\"_".format(from_user=convo['username'], message=message)
  response = requests.get("https://slack.com/api/chat.postMessage?token=xoxb-62712469858-QAmGTuRLktyYuMI79193Kfow&channel={im_channel}&text={message_body}&as_user=true&pretty=1".format(im_channel=convo['im_channel'], message_body=message_body))
  return


def slack_send(convo, message_txt, from_user="game.bots"):
  print "slack_send(convo=%s, message_txt=%s, from_user=%s)" % (convo, message_txt, from_user)

  webhooks = {
    'Pokemon Go'        : "https://hooks.slack.com/services/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",
    'Dota 2'            : "https://hooks.slack.com/services/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",
    'League of Legends' : "https://hooks.slack.com/services/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",
    'CS:GO'             : "https://hooks.slack.com/services/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"
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
  
  response = requests.post(webhooks[convo['game']], data=payload)
  return
    