import os
import sys
import json
import pymysql
import sys
import json
import time
import requests
import urllib2
import logging
from datetime import datetime

from flask import Flask, request

app = Flask(__name__)

def sendTracker(category, action, label):
  try:
    _response = urllib2.urlopen("http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (str(category), str(action), str(label)))
  
  except:
    print "GA ERROR!"
        
  return


def getStreamerContent(url):
  _response = urllib2.urlopen(url, timeout=5)
  _json = json.load(_response, 'utf-8')
  
  return [_json['channel'], _json['preview_img'], _json['player_url']]
  

def getStreamers():
  streamers = []
  conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
  cur = conn.cursor()
  cur.execute("SELECT `channel_name` FROM `subscribe_topics` WHERE `type` = 'streamer' OR `type` = 'game';")
  
  for r in cur:
    streamers.append(r[0])
  cur.close()
  conn.close()
  
  return streamers


def isStreamerOnline(streamerName):
#	logger.info("isStreamerOnline " + str(streamerName))
  
  _response = urllib2.urlopen("https://api.twitch.tv/kraken/streams/%s" % (streamerName))
  _json = json.load(_response, 'utf-8')

  try:
    if _json['stream']:
      return True
      
  except:
    return False
    
  return False


@app.route('/slack', methods=['POST'])
def slack():
  logger.info("-=- /slack\n%s" % (request.form))
  if request.form.get('token') == "uKA7dgfnfadLN4QApLYmmn4m":
    logger.info("help_convos:\n%s" % (help_convos))
    
    _arr = request.form.get('text').split(' ')
    _arr.pop(0)

    sender_id = _arr[0]
    _arr.pop(0)

    message = " ".join(_arr).replace("'", "")

    logger.info("SenderID: %s\nMessage: %s" % (sender_id, message))

    if "%s_%s" % (sender_id, sender_id) in help_convos:
      if message == "!end":
        print "-=- ENDING HELP -=-"
        send_text(sender_id, "Closed this %s help session." % (help_convos["%s_%s" % (sender_id, sender_id)]['game']))
        send_text(sender_id, "Please tell me a game or player name you want to subscribe to.")
        del help_convos["%s_%s" % (sender_id, sender_id)]

      else:
        send_text(sender_id, "Helper says:\n%s" % (message))

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
    sendTracker("bot", "send", "facebook")
    send_text(chat['chat_id'], fbMessage)
    send_picture(chat['chat_id'], link_pic[0], link_pic[1])

  return "OK", 200


@app.route('/', methods=['GET'])
def verify():
  logger.info(request.args)
  # when the endpoint is registered as a webhook, it must
  # return the 'hub.challenge' value in the query arguments
  if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
    if not request.args.get("hub.verify_token") == "ae9118876b91ea88def1259cc13ff2ca":
      return "Verification token mismatch", 403
    return request.args["hub.challenge"], 200

  return "Hello world", 200



@app.route('/', methods=['POST'])
def webook():
  logger.info("webhook")

  # endpoint for processing incoming messaging events

  data = request.get_json()
  logger.info(data)  # you may not want to log every incoming message in production, but it's good for testing

  if data["object"] == "page":
    for entry in data["entry"]:
      for messaging_event in entry["messaging"]:
        if messaging_event.get("message"):  # someone sent us a message
          logger.info("message recieved!!!")
          
          #------- IMAGE MESSAGE
          #if messaging_event["message"]["type"] == "image":
          #  return "ok", 200

          # MESSAGE CREDENTIALS 
          sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
          recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
          message_text = messaging_event["message"]["text"]  # the message's text
          timestamp = messaging_event["timestamp"]
          
          streamerLowerCase = message_text.lower()
          logger.info("gameHelpList: %s" % (gameHelpList))
          logger.info("help_convos: %s" % (help_convos))
          
          
          if 'quick_reply' in messaging_event["message"]:
            payload = messaging_event["message"]["quick_reply"]["payload"]
            
            if payload.startswith("hlp_"):
              logger.info("Starting help...")
              game_name = payload.split("_")[1]
              gameHelpList["%s_%s" % (sender_id, sender_id)] = game_name
              logger.info("gameHelpList: %s" % (gameHelpList))
              
              send_text(sender_id, "Ok, describe what you are having trouble with in %s." % (game_name))
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
             
          #-- HELP LOOKUP
          if "%s_%s" % (sender_id, sender_id) in gameHelpList:
            help_convos["%s_%s" % (sender_id, sender_id)] = {
              'sender_id': sender_id,
              'game': gameHelpList["%s_%s" % (sender_id, sender_id)]
            }

            send_text(sender_id, "Locating top %s player..." % (gameHelpList["%s_%s" % (sender_id, sender_id)]))
            send_text(sender_id, "Type '!end' to close this help session.")

            payload = json.dumps({
              'channel': "#fb-help", 
              'username': sender_id,
              'text': "Requesting help for *%s*:\n%s\n_\"%s\"_" % (gameHelpList["%s_%s" % (sender_id, sender_id)], sender_id, message_text.replace("\'", ""))
            })

            response = requests.post("https://hooks.slack.com/services/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", data={'payload': payload})
            
            logger.info("help_convos: %s" % (help_convos))
            del gameHelpList["%s_%s" % (sender_id, sender_id)]
            return "ok", 200

          #-- HELP SESSION
          if "%s_%s" % (sender_id, sender_id) in help_convos:
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

            else: 
              payload = json.dumps({
                'channel': "#kik-help", 
                'username': sender_id,
                'text': "_\"%s\"_" % (message_text.replace("\'", ""))
              })

            response = requests.post("https://hooks.slack.com/services/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", data={'payload': payload})
            return "ok", 200
            
          # -- FOUND STREAMER
          if streamerLowerCase in subscribersForStreamer:
            sendTracker("bot", "subscribe", "facebook")
            _ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=fb&channel=%s&cid=%s' %(message_text, sender_id))
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

              #send_text(sender_id, "Do you currently need help with any of these games?", _qr)
              
          else:
            send_text(sender_id, "Oh no!, " + message_text + " was not found. Provide me with the name of your favorite player, team, or game.")


        if messaging_event.get("delivery"):  # delivery confirmation
          logger.info("DELIVERY CONFIRM")
          return "ok", 200
          
        if messaging_event.get("read"):  # read confirmation
          logger.info("READ CONFIRM")
          sendTracker("bot", "read", "facebook")
          return "ok", 200

        if messaging_event.get("optin"):  # optin confirmation
          logger.info("OPT-IN")
          return "ok", 200

        if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
          logger.info("POSTBACK RESPONSE")
          return "ok", 200

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
    #"access_token": "EAAMTIib1ptABACigFnLMI5r719FGu8TM0COYg9qNs0nj97DNuwrHCtonI5rwLom60ElDgzRkPADf7Rp8sCVBFsHp4EHFUBbgeyStNxJB502LesoY4dKjZCUbki8U8t52oqZBr3RQdTeZABIZA6KU8ayLh7Ukqyjb83MheenIagZDZD"
    "access_token": "EAAXFDiMELKsBAJCy4kCwLcVMoXDG441SSvbnq1cDSmbiWLNE8Rsjv8GtLyZCSgnZBlQVWf9ipmfT2ye80Ld8hxxJ1puqvjIZAvXlw1LNerEMbrDODm1R6ZA4RQ6Nx4bPzSiIOT17AhvWEyotZBhKgZAelhwZBRL1AKHa9wRDOjpqZAOFn3nE1yhC"
  }
  
  headers = {
    "Content-Type": "application/json"
  }

  _r = requests.post("https://graph.facebook.com/v2.6/me/messages", params = params, headers = headers, data = data)
  if _r.status_code != 200:
    logger.info("Error! %s - %s" % (_r.status_code, _r.text))



global subscribersForStreamer
subscribersForStreamer = {}

global gameHelpList
gameHelpList = {}

global help_convos
help_convos = {}

streamerArray = getStreamers()
for s in streamerArray:
  subscribersForStreamer[s.lower()] = []


x = urllib2.urlopen("http://beta.modd.live/api/subscriber_list.php?type=fb").read()

r = x.split("\n")
for row in r:
  c = row.split(",")
  if len(c) == 3:
    logger.info(c[0])
    logger.info(c[1])
    logger.info(c[2])
    subscribersForStreamer[c[0].lower()].append({'chat_id':c[2]})
#subscribersForStreamer = {"matty_devdev":[], "faroutrob":[]}

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler('/var/log/FacebookBot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)

if __name__ == '__main__':
  app.run(debug=True)
