from datetime import date
import csv
import tornado.escape
import tornado.ioloop
import tornado.web
import pymysql
import pycurl
import sys
import cStringIO
import json
import time
import random
from datetime import datetime
from kik.messages import messages_from_json, TextMessage, StartChattingMessage, LinkMessage, VideoMessage, SuggestedResponseKeyboard, TextResponse, CustomAttribution, ReadReceiptMessage
from kik import KikApi, Configuration
import urllib
import urllib2


def sendTracker(category, action, label):
   buf = cStringIO.StringIO()
   c = pycurl.Curl()
   c.setopt(c.URL, "http://beta.modd.live/api/bot_tracker.php?category=" + str(category) + "&action=" + str(action) + "&label=" + str(label))
   c.setopt(c.WRITEFUNCTION, buf.write)
   try:
      c.perform()
   except:
      print("GA ERROR!")
   return True

def getStreamers():
#   print("getStreamers ")

   streamers = []
   conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
   cur = conn.cursor()
   cur.execute("SELECT `username` FROM `users` WHERE `type` = 'streamer';")
   for r in cur:
      streamers.append(r[0])
   cur.close()
   conn.close()
#   print("return getStreamers")
   return streamers

def isStreamerOnline(streamerName):
#   print("isStreamerOnline " + str(streamerName))
   buf = cStringIO.StringIO()
   c = pycurl.Curl()
   c.setopt(c.URL, "https://api.twitch.tv/kraken/streams/" + str(streamerName))
   c.setopt(c.WRITEFUNCTION, buf.write)
   try:
      c.perform()
      j = json.loads(buf.getvalue())
   except:
#      print("return isStreamerOnline Fasle")
      return False
   try:
      if j['stream']:
#         print("return isStreamerOnline True")
         return True
   except:
                  return False
   return False

def getFollowers(streamerName):
#   print("checking online status")
   buf = cStringIO.StringIO()
   c = pycurl.Curl()
   c.setopt(c.URL, "https://api.twitch.tv/kraken/channels/" + str(streamerName))
   c.setopt(c.WRITEFUNCTION, buf.write)
   try:
      c.perform()
      j = json.loads(buf.getvalue())
   except:
      pass 
#   print("exception")
   try:
      return j['followers']
   except:
      pass
#   print("exception")

def getTimeOnline(streamerName):
   buf = cStringIO.StringIO()
   c = pycurl.Curl()
   c.setopt(c.URL, "https://api.twitch.tv/kraken/streams/" + str(streamerName))
   c.setopt(c.WRITEFUNCTION, buf.write)
   try:
      c.perform()
      j = json.loads(buf.getvalue())
   except:
      return False
   try:
      if j['stream']:
         start = j['stream']['created_at']
         tdelta = datetime.utcnow() - datetime.strptime(start, '%Y-%m-%dT%H:%M:%SZ')
#         print tdelta
         return tdelta
   except:
      pass
#   print("exception")


def getViewers(streamerName):
   buf = cStringIO.StringIO()
   c = pycurl.Curl()
   c.setopt(c.URL, "https://api.twitch.tv/kraken/streams/" + streamerName)
   c.setopt(c.WRITEFUNCTION, buf.write)
   try:
      c.perform()
      j = json.loads(buf.getvalue())
   except:
      return False
   try:
      if j['stream']:
         return j['stream']['viewers']
   except:
      pass
#      print("exception")


def getStreamerNameLink(theurl):
#   print("getStreamerNameLink" + str(theurl))
   buf = cStringIO.StringIO()
   c = pycurl.Curl()
   c.setopt(c.URL, theurl) #"http://beta.modd.live/api/top_streamer.php")
   c.setopt(c.WRITEFUNCTION, buf.write)
   try:
      c.perform()
      j = json.loads(buf.getvalue())
   except:
#      print("getStreamerNameLink exception")
      pass
   try:
#      print("return getStreamerNameLink")
      return [j['channel'],j['preview_img'], j['player_url']]
   except:
#      print("getStreamerNameLink exception")
      pass
#   print("exception")

def getGameInfo(theurl):
#   print("getStreamerNameLink" + str(theurl))
   buf = cStringIO.StringIO()
   c = pycurl.Curl()
   c.setopt(c.URL, theurl) #"http://beta.modd.live/api/top_streamer.php")
   c.setopt(c.WRITEFUNCTION, buf.write)
   try:
      c.perform()
      j = json.loads(buf.getvalue())
   except:
#      print("getStreamerNameLink exception")
      pass
   try:
#      print("return getStreamerNameLink")
      return j[0]
   except:
#      print("getStreamerNameLink exception")
      pass
#   print("exception")
   
def getNextTopGameInfo(theurl):
#   print("getStreamerNameLink" + str(theurl))
   buf = cStringIO.StringIO()
   c = pycurl.Curl()
   c.setopt(c.URL, theurl) #"http://beta.modd.live/api/top_streamer.php")
   c.setopt(c.WRITEFUNCTION, buf.write)
   try:
      c.perform()
      j = json.loads(buf.getvalue())
   except:
#      print("getStreamerNameLink exception")
      pass
   try:
#      print("return getStreamerNameLink")
      return random.choice(j)
   except:
#      print("getStreamerNameLink exception")
      pass
#   print("exception")

def getTimeOnlineMessage(streamerName):
#   print("getTimeOnlineMessage" + str(streamerName))
   delta = getTimeOnline(streamerName)
   m, s = divmod(delta.seconds, 60)
   h, m = divmod(m, 60)
   return ("%dh %02dm %02ds" % (h, m, s))


subscribersForStreamer = {}

streamerArray = getStreamers()
for s in streamerArray:
#   print("making lowercase keys:  " + str(s))
   subscribersForStreamer[s.lower()] = []
#print("done making lowercase keys")


x = urllib2.urlopen("http://beta.modd.live/api/subscriber_list.php?type=kik").read()

r = x.split("\n")
#print(x)
#print("__________")
#print(r)
#f = open('htt)
#print("xxxxxxxxxxxxxx")
for row in r:
   c = row.split(",")
#   print("-------c: ")
   if len(c) == 3:
#      print(c[0])
#      print(c[1])
#      print(c[2])
      subscribersForStreamer[c[0].lower()].append({'kikUser':c[1],'chat_id':c[2]})
#print(subscribersForStreamer)
#subscribersForStreamer = {"matty_devdev":[], "faroutrob":[]}


class Notify(tornado.web.RequestHandler):
   def set_default_headers(self):
      self.set_header("Access-Control-Allow-Origin", "*")
      self.set_header("Access-Control-Allow-Headers", "x-requested-with")
      self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
   def get(self):
#      print("Notify get") 
      streamerName = self.get_arguments('streamer')[0]
      kikMessage = self.get_arguments('message')[0]
#      print("Notify get - streamerName:kikMessage = " + streamerName + ":" + kikMessage)
#      print(streamerName)
#      print(kikMessage)
      link_pic = getStreamerNameLink("http://beta.modd.live/api/live_streamer.php?channel=" + streamerName)
      kikSubscribers = subscribersForStreamer[streamerName]
      for chat in kikSubscribers:
         print("SENDING CONVO - TO: " + chat['kikUser'] + " CHAT_ID: " + chat['chat_id'])
         sendTracker("bot", "send", "kik")   
#         print("Notify get -> sending kik message x3")
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
                attribution = CustomAttribution(name = 'Streamcard.tv', icon_url = 'http://streamcard.tv/img/icon/favicon-32x32.png')
            ),
            TextMessage(
               to = chat['kikUser'],
               chat_id = chat['chat_id'],
               body = 'Do you want to notified when other players go online today?',
               keyboards = [
                  SuggestedResponseKeyboard(
                     hidden = False,
                     responses = [
                        TextResponse('Yes'),
                        TextResponse('No')
                     ]
                  )
               ],
         )])


class Message(tornado.web.RequestHandler):
   def set_default_headers(self):
      self.set_header("Access-Control-Allow-Origin", "*")
      self.set_header("Access-Control-Allow-Headers", "x-requested-with")
      self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
      
   def post(self):
      print("=-=-=-=-=-=-=-=-=-=-= MESSAGE BROADCAST =-=-=-=-=-=-=-=-=-=-=")
      username = self.get_body_argument('recipient', '')
      body = self.get_body_argument('body', '')
      url = self.get_body_argument('url', '')
      image_url = self.get_body_argument('image_url', '')
      video_url = self.get_body_argument('video_url', '')
      message_type = self.get_body_argument('type', '')
      
      conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
      cur = conn.cursor()
      cur.execute("SELECT `chat_id` FROM `kikbot_logs` WHERE `username` = '" + username + "' LIMIT 1;")
      result = cur.fetchone()
      cur.close()
      conn.close()
      
      if len(result) > 0:
         print("RECIPIENT: " + username + " (" + result[0] + ")")
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
               attribution = CustomAttribution(name = 'gamebots.chat', icon_url = 'http://gamebots.chat/img/icon/favicon-32x32.png')
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
#      print("Message post")
      data_json = tornado.escape.json_decode(self.request.body)
      print(data_json)
#       if data_json['type'] == "start-chatting": #                       print("strea")
      messages = messages_from_json(data_json["messages"])
      print(messages)
      for message in messages:
         # -=-=-=-=-=-=-=-=- READ RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
         if isinstance(message, ReadReceiptMessage):
            sendTracker("bot", "read", "kik")
            return
         
         # -=-=-=-=-=-=-=-=- START CHATTING -=-=-=-=-=-=-=-=-
         if isinstance(message, StartChattingMessage):
            conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
            cur = conn.cursor()
            cur.execute("SELECT `channel_name` FROM `notify` WHERE `viewer_kik` = '" + message.from_user + "' LIMIT 1;")
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            if len(result) > 0:
               top_game = getNextTopGameInfo("http://beta.modd.live/api/top_games.php?list=1")

               print("NEXT TOP: " + top_game['name'])
               _ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=' + top_game['name'] + '&username=' + message.from_user + '&cid=' + message.chat_id)
               sendTracker("bot", "subscribe", "kik")
               
               kik.send_messages([
                  TextMessage(
                     to = message.from_user,
                     chat_id = message.chat_id,
                     body = "Awesome you have been subscribed to " + result[0] + "'s GameBot."
                  ),
                  LinkMessage(
                      to = message.from_user,
                     chat_id = message.chat_id,
                     title = top_game['name'],
                     pic_url = top_game['box_image'],
                     url = "http://kik.me/streamcard",
                     attribution = CustomAttribution(
                        name = 'gamebots.chat',
                        icon_url = 'http://gamebots.chat/img/icon/favicon-32x32.png'
                     )
                  ),
                  TextMessage(
                     to = message.from_user,
                     chat_id = message.chat_id,
                     body = "Do you also like " + top_game['name'] + "?",
                     keyboards = [
                        SuggestedResponseKeyboard(
                           hidden = False,
                           responses = [
                              TextResponse('OK'),
                              TextResponse('No thanks')
                           ]
                        )
                     ]
                  )
               ])
            
            else:
               link_pic = getStreamerNameLink("http://beta.modd.live/api/top_streamer.php")
               _ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=' + link_pic[0] + '&username=' + message.from_user + "&cid=" + message.chat_id)
               print("Message post (StartChattingMessage recieved) -> sending kik message x3 (" + message.chat_id + ")")
               kik.send_messages([
                  TextMessage(
                     to = message.from_user,
                     chat_id = message.chat_id,
                     body = "Welcome to the Stream Card chatbot!"
                  ),
                  LinkMessage(
                     to = message.from_user,
                     chat_id = message.chat_id,
                     title = link_pic[0],
                     pic_url = link_pic[1],
                     url = link_pic[2],
                     attribution = CustomAttribution(name = 'Streamcard.tv', icon_url = 'http://streamcard.tv/img/icon/favicon-32x32.png')
                  ),
                  TextMessage(
                     to = message.from_user,
                     chat_id = message.chat_id,
                     body = "Provide me with the name of your favorite player, and I will subscribe you to more updates like this!"
               )])
            
         
         if isinstance(message, TextMessage):
            # -=-=-=-=-=-=-=-=- SUBSCRIBE ALL -=-=-=-=-=-=-=-=-
            if message.body.lower() == '!all':
               kik.send_messages([
                  TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = "Subscribing to all..."
               )])
               for s in streamerArray:
                  print("SUBSCRIBING TO: " + s.lower())
                  _ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=' + s.lower() + '&username=' + message.from_user + "&cid=" + message.chat_id)
                  subscribersForStreamer[s.lower()].append({'kikUser':message.from_user,'chat_id':message.chat_id})
            else:
               pass
            
            
            # -=-=-=-=-=-=-=-=- BUTTON OK/No thanks -=-=-=-=-=-=-=-=-
            if message.body.lower() == 'ok' or message.body.lower() == 'no thanks':
               top_game = getNextTopGameInfo("http://beta.modd.live/api/top_games.php?list=1")
               
               #_ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=' + urllib.urlencode(str(top_game['name'])) + '&username=' + message.from_user + "&cid=" + message.chat_id)
               sendTracker("bot", "subscribe", "kik")
               
               kik.send_messages([
                  TextMessage(
                     to = message.from_user,
                     chat_id = message.chat_id,
                     body = "Awesome you have been subscribed!"
                  )#,
                  #LinkMessage(
                  #to=message.from_user,
                  #   chat_id = message.chat_id,
                  #   title = top_game['name'],
                  #   pic_url = top_game['box_image'],
                  #   url = "http://kik.me/streamcard",
                  #   attribution = CustomAttribution(
                  #      name = 'gamebots.chat',
                  #      icon_url = 'http://gamebots.chat/img/icon/favicon-32x32.png'
                  #   )
                  #),
                  #TextMessage(
                  #   to = message.from_user,
                  #   chat_id = message.chat_id,
                  #   body = "Do you also like " + top_game['name'] + "?",
                  #   keyboards = [
                  #      SuggestedResponseKeyboard(
                  #         hidden = False,
                  #         responses = [
                  #            TextResponse('OK'),
                  #            TextResponse('No thanks')
                  #         ]
                  #      )
                  #   ]
                  #)
               ])
               return
            else:
               pass
            
               
            # -=-=-=-=-=-=-=-=- BUTTON Y/N -=-=-=-=-=-=-=-=-
            if message.body.lower() == 'yes' or message.body.lower() == 'no':
               response = urllib2.urlopen('http://beta.modd.live/api/notify_enable.php?username=' + message.from_user)
 #                                       print("Message post (TextMessage User replied 'yes' to Updates recieved) -> sending kik message x1")
               kik.send_messages([
                  TextMessage(
                     to = message.from_user,
                     chat_id = message.chat_id,
                     body = "OK. All set!"
               )])
#               print("Message post return")
               return
            else:
               pass
            #######THIS IS FOR RECONSTRUCTING WHO SIGNED UP FOR NOTIFICATIONS####
            conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
            cur = conn.cursor()
            try:
               cur.execute("INSERT IGNORE INTO `kikbot_logs` (`username`, `chat_id`, `body`, `added`) VALUES (\'" + message.from_user + "\', \'" + message.chat_id + "\', \'" + message.body + "\',  NOW())")
            except:
#               print("exception")
#               print("Message post return")

               return
            cur.close()
            conn.close()

            # -=-=-=-=-=-=-=-=-=- MENTIONS -=-=-=-=-=-=-=-=-
            if message.mention is not None:
               #print ("MENTION: " + message.mention)
               participants = message.participants
               participants.remove(message.from_user)
               game_info = getGameInfo("http://beta.modd.live/api/top_games.php?game=" + message.body + "&amt=1")

               print("CHAT ID: " + message.chat_id)
               print("FROM: " + message.from_user)
               print("PARTICIPANT: " + participants[0])
               
               _ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=' + game_info['name'] + '&username=' + participants[0] + "&cid=" + message.chat_id)
               sendTracker("bot", "subscribe", "kik")
               
               kik.send_messages([
                  LinkMessage(
                  to = message.from_user,
                     chat_id = message.chat_id,
                     title = game_info['name'],
                     pic_url = game_info['box_image'],
                     url = "http://kik.me/" + message.mention,
                     attribution = CustomAttribution(
                        name = 'gamebots.chat',
                        icon_url = 'http://gamebots.chat/img/icon/favicon-32x32.png'
                     )
                  ),
                  TextMessage(
                     to = message.from_user,
                     chat_id = message.chat_id,
                     body = "Do you like " + game_info['name'] + "?",
                     keyboards = [
                        SuggestedResponseKeyboard(
                           hidden = False,
                           responses = [
                              TextResponse('Yes'),
                              TextResponse('No')
                           ]
                        )
                     ]
                  )
               ])

               return
            else:
               pass

            # -=-=-=-=-=-=-=-=-=- SUBSCRIBING -=-=-=-=-=-=-=-
            streamerLowerCase = message.body.lower()
            if streamerLowerCase in subscribersForStreamer:
               print("SUBSCRIBING TO: " + message.chat_id)
               _ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=' + message.body + '&username=' + message.from_user + "&cid=" + message.chat_id)
               subscribersForStreamer[streamerLowerCase].append({'kikUser':message.from_user,'chat_id':message.chat_id})
               sendTracker("bot", "subscribe", "kik")
               if isStreamerOnline(streamerLowerCase):
                  #timeOnlineMSG = getTimeOnlineMessage(streamerLowerCase)
                  #followers = getFollowers(streamerLowerCase)
                  #viewers = getViewers(streamerLowerCase)
#                  print("Message post (TextMessage valid user recieved) -> sending kikMessage x1")
                  link_pic = getStreamerNameLink("http://beta.modd.live/api/live_streamer.php?channel=" + message.body)

                  kik.send_messages([
                  TextMessage(
                     to = message.from_user,
                     chat_id = message.chat_id,
                     body = "Awesome, " + message.body + " was found and is streaming live! You will begin receiving updates. scard.tv/channel/" + message.body
                  ), 
                  LinkMessage(
                     to = message.from_user,
                     chat_id = message.chat_id,
                     title = link_pic[0],
                     pic_url = link_pic[1],
                     url = link_pic[2],
                     attribution = CustomAttribution(name = 'Streamcard.tv', icon_url = 'http://streamcard.tv/img/icon/favicon-32x32.png')
                  )
                  ])
               else:
                  _ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=kik&channel=' + message.body + '&username=' + message.from_user + '&cid=' + message.chat_id)
#                  print("Message post (TextMessage valid user recieved(offline)) -> sending kikMessage x1")
                  kik.send_messages([
                     TextMessage(
                     to = message.from_user,
                     chat_id = message.chat_id,
                     body = "Awesome, " + message.body + " was found and you will begin receiving updates when they go live. scard.tv/channel/" + message.body
                  )])
            else:
#               print("Message post (TextMessage NO valid user found recieved) -> sending kikMessage x1")
               kik.send_messages([
               TextMessage(
                  to = message.from_user,
                  chat_id = message.chat_id,
                  body = "Oh no! That entry was not found. Provide me with the name of your favorite player."
               )])

kik = KikApi("streamcard", "aa503b6f-dcda-4817-86d0-02cfb110b16a")
kik.set_configuration(Configuration(webhook="http://159.203.250.4:8891/kik", features={"receiveReadReceipts":True, "receiveDeliveryReceipts":True}))

application = tornado.web.Application([(r"/kik", KikBot), (r"/kikNotify", Notify), (r"/message", Message)])
if __name__ == "__main__":

## TODO reconstruct who subscribed for what from  into subscribersForStreamer
    application.listen(8891)
    tornado.ioloop.IOLoop.instance().start()
    print("tornado start")
