import os
import sys
import json
import pymysql
import pycurl
import sys
import cStringIO
import json
import time
import urllib2
import logging
from datetime import datetime


import requests
from flask import Flask, request

app = Flask(__name__)

def sendTracker(category, action, label):
	buf = cStringIO.StringIO()
	c = pycurl.Curl()
	c.setopt(c.URL, "http://beta.modd.live/api/bot_tracker.php?category=" + str(category) + "&action=" + str(action) + "&label=" + str(label))
	c.setopt(c.WRITEFUNCTION, buf.write)
	try:
		c.perform()
	except:
		logger.info("GA ERROR!")
	return True

def getStreamerNameLink(theurl):
#	logger.info("getStreamerNameLink" + str(theurl))
	buf = cStringIO.StringIO()
	c = pycurl.Curl()
	c.setopt(c.URL, theurl) #"http://beta.modd.live/api/top_streamer.php")
	c.setopt(c.WRITEFUNCTION, buf.write)
	try:
		c.perform()
		j = json.loads(buf.getvalue())
	except:
#		logger.info("getStreamerNameLink exception")
		pass
	try:
#		logger.info("return getStreamerNameLink")
		return [j['channel'],j['preview_img'], j['player_url']]
	except:
#		logger.info("getStreamerNameLink exception")
		pass
#	logger.info("exception")

def getStreamers():
#	logger.info("getStreamers ")

	streamers = []
	conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
	cur = conn.cursor()
	cur.execute("SELECT `username` FROM `users` WHERE `type` = 'streamer';")
	for r in cur:
		streamers.append(r[0])
		cur.close()
		conn.close()
#		logger.info("return getStreamers")
		return streamers

def isStreamerOnline(streamerName):
#	logger.info("isStreamerOnline " + str(streamerName))
	buf = cStringIO.StringIO()
	c = pycurl.Curl()
	c.setopt(c.URL, "https://api.twitch.tv/kraken/streams/" + str(streamerName))
	c.setopt(c.WRITEFUNCTION, buf.write)
	try:
		c.perform()
		j = json.loads(buf.getvalue())
	except:
#		logger.info("return isStreamerOnline Fasle")
		return False
	try:
		if j['stream']:
#			logger.info("return isStreamerOnline True")
			return True
	except:
		return False
	return False


subscribersForStreamer = {}

streamerArray = getStreamers()
for s in streamerArray:
#	logger.info("making lowercase keys:  " + str(s))
	subscribersForStreamer[s.lower()] = []
#logger.info("done making lowercase keys")


x = urllib2.urlopen("http://beta.modd.live/api/subscriber_list.php?type=fb").read()

r = x.split("\n")
#logger.info(x)
#logger.info("__________")
#logger.info(r)
#f = open('htt)
#logger.info("xxxxxxxxxxxxxx")
for row in r:
	c = row.split(",")
#	logger.info("-------c: ")
	if len(c) == 3:
		logger.info(c[0])
		logger.info(c[1])
		logger.info(c[2])
		subscribersForStreamer[c[0].lower()].append({'chat_id':c[2]})
#logger.info(subscribersForStreamer)
#subscribersForStreamer = {"matty_devdev":[], "faroutrob":[]}

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler('/var/log/FacebookBot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)


@app.route('/notify', methods=['GET'])
def notify():
	logger.info("notify")

	streamerName = request.args.get('streamer')
	fbMessage = request.args.get('message')
#	logger.info("Notify get - streamerName:kikMessage = " + streamerName + ":" + kikMessage)
#	logger.info(streamerName)
#	logger.info(kikMessage)

	link_pic = getStreamerNameLink("http://beta.modd.live/api/live_streamer.php?channel=" + streamerName)
	fbSubscribers = subscribersForStreamer[streamerName]
	for chat in fbSubscribers:
		sendTracker("bot", "send", "facebook")
		send_message(chat['chat_id'], fbMessage)
		send_picture(chat['chat_id'], link_pic[0], link_pic[1])

	return "OK", 200


@app.route('/', methods=['GET'])
def verify():
	logger.info(request.args)
	# when the endpoint is registered as a webhook, it must
	# return the 'hub.challenge' value in the query arguments
	if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
		if not request.args.get("hub.verify_token") == "ea899efdbdedfa8a50990d7d4b5bf451":
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
					#	return "ok", 200

					# MESSAGE CREDENTIALS 
					sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
					recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
					message_text = messaging_event["message"]["text"]  # the message's text
					streamerLowerCase = message_text.lower()
					logger.info(streamerLowerCase)
					
					# -- !all MESSAGE
					if streamerLowerCase.encode('utf8') == '!all':
						logger.info("found all")
						streamerArray = getStreamers()
						for s in streamerArray:
							subscribersForStreamer[s.lower()].append({'chat_id':sender_id})
							send_message(sender_id, "Your phone will now blow up in 3.. 2.. 1..")
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
									send_message(sender_id, streamerString)
						return "ok", 200

					# -- FOUND STREAMER
					if streamerLowerCase in subscribersForStreamer:
						sendTracker("bot", "subscribe", "facebook")
						_ = urllib2.urlopen('http://beta.modd.live/api/streamer_subscribe.php?type=fb&channel=' + message_text)
						subscribersForStreamer[streamerLowerCase].append({'chat_id':sender_id})
						if isStreamerOnline(streamerLowerCase):
							link_pic = getStreamerNameLink("http://beta.modd.live/api/live_streamer.php?channel=" + streamerLowerCase)
							fbSubscribers = subscribersForStreamer[streamerLowerCase]
							send_message(sender_id, "Awesome, " + message_text + " was found and is streaming live! You will begin receiving updates. http://scard.tv/channel/" + streamerLowerCase)
							send_picture(sender_id, link_pic[0], link_pic[1])
							send_message(sender_id, "Provide me with the name of your favorite player, team, or game and I will subscribe you to more updates like this!")
						else:
							send_message(sender_id, "Awesome, " + message_text + " was found and you will begin receiving updates when they go live. http://scard.tv/channel/" + message_text)
					else:
						send_message(sender_id, "Oh no!, " + message_text + " was not found. Provide me with the name of your favorite player, team, or game.")


				if messaging_event.get("delivery"):  # delivery confirmation
					logger.info("DELIVERY CONFIRM")
					sendTracker("bot", "read", "facebook")
					pass

				if messaging_event.get("optin"):  # optin confirmation
					logger.info("OPT-IN")
					pass

				if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
					logger.info("POSTBACK RESPONSE")
					pass

	return "ok", 200


def send_message(recipient_id, message_text):
	logger.info("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))
	params = {
		#"access_token": "EAAMTIib1ptABACigFnLMI5r719FGu8TM0COYg9qNs0nj97DNuwrHCtonI5rwLom60ElDgzRkPADf7Rp8sCVBFsHp4EHFUBbgeyStNxJB502LesoY4dKjZCUbki8U8t52oqZBr3RQdTeZABIZA6KU8ayLh7Ukqyjb83MheenIagZDZD"
        "access_token": "EAAXFDiMELKsBAJCy4kCwLcVMoXDG441SSvbnq1cDSmbiWLNE8Rsjv8GtLyZCSgnZBlQVWf9ipmfT2ye80Ld8hxxJ1puqvjIZAvXlw1LNerEMbrDODm1R6ZA4RQ6Nx4bPzSiIOT17AhvWEyotZBhKgZAelhwZBRL1AKHa9wRDOjpqZAOFn3nE1yhC"
	}
	headers = {
		"Content-Type": "application/json"
	}
	data = json.dumps({
		"recipient": {
			"id": recipient_id
		},
		"message": {
			"text": message_text
		}
	})
	
	r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
	if r.status_code != 200:
		logger.info(r.status_code)
		logger.info(r.text)


def send_picture(recipient_id, streamerTitle, imageUrl):
	params = {
        #"access_token": "EAAMTIib1ptABACigFnLMI5r719FGu8TM0COYg9qNs0nj97DNuwrHCtonI5rwLom60ElDgzRkPADf7Rp8sCVBFsHp4EHFUBbgeyStNxJB502LesoY4dKjZCUbki8U8t52oqZBr3RQdTeZABIZA6KU8ayLh7Ukqyjb83MheenIagZDZD"
        "access_token": "EAAXFDiMELKsBAJCy4kCwLcVMoXDG441SSvbnq1cDSmbiWLNE8Rsjv8GtLyZCSgnZBlQVWf9ipmfT2ye80Ld8hxxJ1puqvjIZAvXlw1LNerEMbrDODm1R6ZA4RQ6Nx4bPzSiIOT17AhvWEyotZBhKgZAelhwZBRL1AKHa9wRDOjpqZAOFn3nE1yhC"
	}
	headers = {
		"Content-Type": "application/json"
	}
	data = json.dumps({
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
						"item_url": "http://scard.tv/channel/" + streamerTitle,
						"image_url": imageUrl
					}]
				}
			}
		}
	})
	
	r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
	if r.status_code != 200:
		logger.info(r.status_code)
		logger.info(r.text)



if __name__ == '__main__':
    app.run(debug=True)