import sys
from datetime import date, datetime
import time
import csv
import json
import random

import urllib2
import requests
import netifaces as ni
import pymysql

import tornado.escape
import tornado.ioloop
import tornado.web

from kik import KikApi, Configuration
from kik.messages import messages_from_json, TextMessage, StartChattingMessage, LinkMessage, PictureMessage, StickerMessage, ScanDataMessage, UnknownMessage, VideoMessage, SuggestedResponseKeyboard, TextResponse, CustomAttribution, ReadReceiptMessage



def sendTracker(category, action, label):
  try:
    _response = urllib2.urlopen("http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (str(category), str(action), str(label)))
  
  except:
    print "GA ERROR!"
        
  return
  
        
def getStreamers():
  streamers = []
  conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
  cur = conn.cursor()
  cur.execute("SELECT `channel_name` FROM `twitch_channels` WHERE `type` = 'streamer' OR `type` = 'game';")
  
  for r in cur:
    streamers.append(r[0])
  cur.close()
  conn.close()
 
  return streamers


def getStreamerContent(url):
  _response = urllib2.urlopen(url, timeout=5)
  _json = json.load(_response, 'utf-8')
  
  return [_json['channel'], _json['preview_img'], _json['player_url']]
  
  
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
      sendTracker("bot", "send", "kik")
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
            
        #TextMessage(
        #   to = chat['kikUser'],
        #   chat_id = chat['chat_id'],
        #   body = 'Do you want to notified when other players go online today?',
        #   keyboards = [
        #      SuggestedResponseKeyboard(
        #         hidden = False,
        #         responses = [
        #            TextResponse('Yes'),
        #            TextResponse('No')
        #         ]
        #      )
        #   ],
        #)
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
      
    conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
    cur = conn.cursor()
    cur.execute("SELECT `chat_id` FROM `kikbot_logs` WHERE `username` = '%s' LIMIT 1;" % (username))
    result = cur.fetchone()
    cur.close()
    conn.close()
      
    if len(result) > 0:
      print("RECIPIENT: %s (%s)" % (username, result[0]))
      if message_type == "TextMessage":
        print("BODY : " + body)
        kik_message = TextMessage(
          to = username,
          chat_id = result[0],
          body = body
        )
            
      elif message_type == "LinkMessage":
        print("BODY : " + body)
        print("IMG_URL : " + image_url)
        print("URL : " + url)
        kik_message = LinkMessage(
          to = username,
          chat_id = result[0],
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
          chat_id = result[0],
          video_url = video_url,
          autoplay = False,
          muted = False,
          loop = False
        )
            
      kik.send_messages([kik_message])
      

class KikBot(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
  def post(self):
    data_json = tornado.escape.json_decode(self.request.body)
    messages = messages_from_json(data_json["messages"])
    print(messages)
    
    for message in messages:
      # -=-=-=-=-=-=-=-=- UNSUPPORTED TYPE -=-=-=-=-=-=-=-=-
      if isinstance(message, LinkMessage) or isinstance(message, PictureMessage) or isinstance(message, VideoMessage) or isinstance(message, ScanDataMessage) or isinstance(message, StickerMessage) or isinstance(message, UnknownMessage):
        print("IGNORING MESSAGE")
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "I'm sorry, I cannot understand that type of message."
          ),
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "Please tell me a game or player name you want to subscribe to."
          )
        ])
        
        return
          
          
      # -=-=-=-=-=-=-=-=- READ RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
      elif isinstance(message, ReadReceiptMessage):
        sendTracker("bot", "read", "kik")
        return
         
         
      # -=-=-=-=-=-=-=-=- START CHATTING -=-=-=-=-=-=-=-=-
      elif isinstance(message, StartChattingMessage):
        print(data_json)
        conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
        cur = conn.cursor()
        cur.execute("SELECT `channel_name` FROM `notify` WHERE `viewer_kik` = '%s' LIMIT 1;" % (message.from_user))
        result = cur.fetchone()
        cur.close()
        conn.close()
            
        print("Message post (StartChattingMessage recieved) -> sending kik message x3 (" + message.chat_id + ")")
        kik.send_messages([
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "Welcome to GameBots!"
          ),
          LinkMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            title = "",
            pic_url = "http://i.imgur.com/Gadi7Gb.png",
            url = "http://taps.io/BZ3Vg",
            attribution = CustomAttribution(
              name = 'gamebots.chat', 
              icon_url = 'http://gamebots.chat/img/icon/favicon-32x32.png'
            )
          ),
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "Please tell me a game or player name you want to subscribe to."
          ),
          TextMessage(
            to = message.from_user,
            chat_id = message.chat_id,
            body = "For example... Overwatch"
          )
        ])
        return
        
        
      # -=-=-=-=-=-=-=-=- TEXT MESSAGE -=-=-=-=-=-=-=-=-   
      elif isinstance(message, TextMessage):
        print(data_json)
        conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
        cur = conn.cursor()
        try:
          cur.execute("INSERT IGNORE INTO `kikbot_logs` (`username`, `chat_id`, `body`, `added`) VALUES (\'%s\', \'%s\', \'%s\',  NOW())" % (message.from_user, message.chat_id, message.body))
        except:
          return
        
        cur.close()
        conn.close()
          
        # -=-=-=-=-=-=-=-=- SUBSCRIBE ALL -=-=-=-=-=-=-=-=-
        if message.body.lower() == '!all':            
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Subscribing to all..."
            )
          ])
          
          for s in streamerArray:
            print("SUBSCRIBING TO: " + s.lower())
            _ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=%s&username=%s&cid=%s' % (s.lower(), message.from_user, message.chat_id))
            subscribersForStreamer[s.lower()].append({'kikUser':message.from_user,'chat_id':message.chat_id})
            
          
        # -=-=-=-=-=-=-=-=- BUTTONS for Help -=-=-=-=-=-=-=-=-
        gameName = "";  
        if message.body.lower() == '1. overwatch':
          sendTracker("bot", "question", "kik")
          gameName = "Overwatch"
          gameHelpList[message.from_user] = gameName
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Ok, describe what you are having trouble with in %s." % (gameName)
            )
          ])
          return;
             
        if message.body.lower() == '2. cs:go':
          sendTracker("bot", "question", "kik")
          gameName = "CS:GO"
          gameHelpList[message.from_user] = gameName
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Ok, describe what you are having trouble with in %s." % (gameName)
            )
          ])
          return;
                   
        if message.body.lower() == '3. league of legends':
          sendTracker("bot", "question", "kik")
          gameName = "League of Legends"
          gameHelpList[message.from_user] = gameName
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Ok, describe what you are having trouble with in %s." % (gameName)
            )
          ])
          return;
             
        if message.body.lower() == '4. dota2':
          sendTracker("bot", "question", "kik")
          gameName = "Dota2"
          gameHelpList[message.from_user] = gameName
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Ok, describe what you are having trouble with in %s." % (gameName)
            )
          ])
          return;
             
        if message.body.lower() == 'no thanks':
          sendTracker("bot", "question", "kik")
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Sounds good! Your GameBot is always here if you need help."
            )
          ])
          return


        # -=-=-=-=-=-=-=-=- BUTTON Keep Receiving Y/N -=-=-=-=-=-=-=-=-
        if message.body.lower() == 'yes' or message.body.lower() == 'no':
          response = urllib2.urlopen('http://beta.modd.live/api/notify_enable.php?username=' + message.from_user)
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "OK. All set!"
            )
          ])
          return
          

        # -=-=-=-=-=-=-=-=-=- MENTIONS -=-=-=-=-=-=-=-=-
        if message.mention is not None:
          if message.body == "Start Chatting":
            return
                
          else:
            #print ("MENTION: " + message.mention)
            sendTracker("bot", "mention", "kik")
            participants = message.participants
            participants.remove(message.from_user)
             
            print("CHAT ID: " + message.chat_id)
            print("FROM: " + message.from_user)
            print("PARTICIPANT: " + participants[0])
                
            sendTracker("bot", "init", "kik")
             
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Welcome to GameBots, looks like a friend has mentioned me!"
              ),
              LinkMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                title = "",
                pic_url = "http://i.imgur.com/Gadi7Gb.png",
                url = "http://taps.io/BZ3Vg",
                attribution = CustomAttribution(
                  name = 'gamebots.chat', 
                  icon_url = 'http://gamebots.chat/img/icon/favicon-32x32.png'
                )
              ),
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Tap REPLY to become a better player.",
                keyboards = [
                  SuggestedResponseKeyboard(
                    hidden = False,
                    responses = [
                      TextResponse('Start Chatting')
                    ]
                  )
                ]
              )
            ])

            return
             
             
        # -=-=-=-=-=-=-=-=-=- HELP RESPONSE -=-=-=-=-=-=-=-
        if message.from_user in gameHelpList:
          help_convos[message.chat_id] = {
            'chat_id': message.chat_id,
            'username': message.from_user,
            'game': gameHelpList[message.from_user]
          }
             
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Locating top %s player..." % (gameHelpList[message.from_user])
            ),
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Type '!end' to close this help session."
            )
          ])
             
          payload = json.dumps({
            'channel': "#kik-help", 
            'username': message.from_user,
            'text': "Requesting help for *%s*:\n%s\n_\"%s\"_" % (gameHelpList[message.from_user], message.chat_id, message.body.replace("\'", ""))
          })
             
          response = requests.post("https://hooks.slack.com/services/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", data={'payload': payload})
             
          del gameHelpList[message.from_user]
          return
             
          
        # -=-=-=-=-=-=-=-=-=- HELP SESSION -=-=-=-=-=-=-=-
        if message.chat_id in help_convos:
          if message.body.lower() == "!end":
            print "-=- ENDING HELP -=-"
            kik.send_messages([
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "You have closed this %s help session." % (help_convos[message.chat_id]['game'])
              ),
              TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Please tell me a game or player name you want to subscribe to."
              )
            ])
              
            del help_convos[message.chat_id]
              
            payload = json.dumps({
              'channel': "#kik-help", 
              'username': message.from_user,
              'text': "*Help session closed*"
            })
               
          else: 
            payload = json.dumps({
              'channel': "#kik-help", 
              'username': message.from_user,
              'text': "_\"%s\"_" % (message.body.replace("\'", ""))
            })
             
          response = requests.post("https://hooks.slack.com/services/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", data={'payload': payload})
          return
             
        
        # -=-=-=-=-=-=-=-=-=- SUBSCRIBING -=-=-=-=-=-=-=-
        streamerLowerCase = message.body.lower()
        if streamerLowerCase in subscribersForStreamer:
          print("SUBSCRIBING TO: " + message.chat_id)
          _ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=%s&username=%s&cid=%s' % (streamerLowerCase, message.from_user, message.chat_id))
          subscribersForStreamer[streamerLowerCase].append({'kikUser':message.from_user,'chat_id':message.chat_id})
          sendTracker("bot", "subscribe", "kik")
             
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Great! Do you currently need help with any of these games?",
              keyboards = [
                SuggestedResponseKeyboard(
                  hidden = False,
                  responses = [
                    TextResponse('1. Overwatch'),
                    TextResponse('2. CS:GO'),
                    TextResponse('3. League of Legends'),
                    TextResponse('4. Dota2'),
                    TextResponse('No Thanks')
                  ]
                )
              ]
            )
          ])

        else:
          kik.send_messages([
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Oh no! I did not find any matches for that game or player name."
            ),
            TextMessage(
              to = message.from_user,
              chat_id = message.chat_id,
              body = "Please tell me a game or player name you want to subscribe to."
            )
          ])
            
           
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
      
      
      conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
      cur = conn.cursor()
      cur.execute("SELECT `username` FROM `kikbot_logs` WHERE `chat_id` = '%s' ORDER BY `added` DESC LIMIT 1;" % (chat_id))
      result = cur.fetchone()
      cur.close()
      conn.close()
      
      if len(result) > 0:
        to_user = result[0]
        
        print "%s (%s)\n%s" % (to_user, chat_id, message)
        
        if message == "!end":
          print "-=- ENDING HELP -=-"
          kik.send_messages([
            TextMessage(
              to = to_user,
              chat_id = chat_id,
              body = "Closed this %s help session." % (help_convos[chat_id]['game'])
            ),
            TextMessage(
              to = to_user,
              chat_id = chat_id,
              body = "Please tell me a game or player name you want to subscribe to."
            )
          ])
            
          del help_convos[message.chat_id]
          
        else:
          kik.send_messages([
            TextMessage(
              to = to_user,
                chat_id = chat_id,
                body = "Helper says:\n%s" % (message)
              )
          ])
      

subscribersForStreamer = {}
gameHelpList = {}
help_convos = {}

streamerArray = getStreamers()
for s in streamerArray:
   subscribersForStreamer[s.lower()] = []


x = urllib2.urlopen("http://beta.modd.live/api/subscriber_list.php?type=kik").read()

r = x.split("\n")
for row in r:
   c = row.split(",")
   if len(c) == 3 and c[0].lower() in subscribersForStreamer:
      subscribersForStreamer[c[0].lower()].append({'kikUser':c[1],'chat_id':c[2]})
      

#kik = KikApi("streamcard", "aa503b6f-dcda-4817-86d0-02cfb110b16a")
#kik.set_configuration(Configuration(webhook="http://76.102.12.47:8891/kik", features={"receiveReadReceipts":True, "receiveDeliveryReceipts":True}))

kik = KikApi("game.bots", "0fb46005-dd00-49c3-a4a5-239a0bdc1e79")
kik.set_configuration(Configuration(webhook="http://159.203.250.4:8891/kik", features={"receiveReadReceipts":True, "receiveDeliveryReceipts":True}))

## TODO reconstruct who subscribed for what from  into subscribersForStreamer

application = tornado.web.Application([
  (r"/kik", KikBot), 
  (r"/kikNotify", Notify), 
  (r"/message", Message),
  (r"/slack", Slack)
])


if __name__ == "__main__":
  application.listen(8891)
  tornado.ioloop.IOLoop.instance().start()
  print("tornado start")
