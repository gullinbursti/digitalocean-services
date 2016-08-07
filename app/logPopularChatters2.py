import pymysql
import pycurl
import sys
import cStringIO
import json
import time
import timeit

streamerIdCache = {}


def logChattersForStreamer(streamerName, chatters):
#	print "logging chatters for streamer"
	id = streamerIdCache[streamerName.lower()]
#	print type(id)
#	print id
	if id == None:
		id = streamerName.lower()
	chattersList = list(chatters)
	asciichatterList = [str(cx) for cx in chattersList]
	mylist = ",".join(asciichatterList)

#	print streamerName + " " + id + " " + mylist
	conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_tw_usr', passwd='f4zeHUga.age', db='db4086_twitch')
	cur = conn.cursor()
#	cur.execute("INSERT INTO `stream_chatters` (`channel_name`, `stream_id`, `chatters`, `added`) VALUES (" + streamerName + ", " + id + ", " +  chattersString + ", NOW())")
	cur.execute("INSERT IGNORE INTO `stream_chatters` (`channel_name`, `stream_id`, `chatters`, `added`) VALUES (\'" + streamerName + "\', \'" + id + "\', \'" +  mylist + "\', NOW())")
	cur.close()
	conn.close()

def getOnlineStreamers():
	onlineStreamers = []
	conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_tw_usr', passwd='f4zeHUga.age', db='db4086_twitch')
	cur = conn.cursor()
	cur.execute("SELECT * FROM `top_cohort`")
	i = 0
	for r in cur:
		buf = cStringIO.StringIO()
#		print(r[0])
#		print(r[1])
#		print("yo")
		c = pycurl.Curl()
		c.setopt(c.URL, "https://api.twitch.tv/kraken/streams/" + r[1].lower())
		c.setopt(c.WRITEFUNCTION, buf.write)
		try:
			c.perform()
		
#			print(buf.getvalue())
			j = json.loads(buf.getvalue())
		except:
			#print 'curl failed'
			buf.close()
			c.close()
			continue
		buf.close()
		c.close()
		try:
			if j['stream']:
#				print r[1]
				onlineStreamers.append(r[1].lower())
				streamerIdCache[str(r[1].lower())] = str(j['stream']['_id'])
		except:
			pass
		i += 1
	cur.close()
	conn.close()

	return onlineStreamers

def getChattersForStreamer(streamerName):
	#print("getting chatters for " + streamerName)
	viewerArray = []
	chatterBuf = cStringIO.StringIO()
	chatterCurl = pycurl.Curl()
	chatterCurl.setopt(chatterCurl.URL, "https://tmi.twitch.tv/group/user/" + streamerName.lower() + "/chatters")
	chatterCurl.setopt(chatterCurl.WRITEFUNCTION, chatterBuf.write)
	try:
		chatterCurl.perform()
	except: 
	#	print 'curl failed'
		chatterBuf.close()
		chatterCurl.close()
		return []
	try:
		chatterJ = json.loads(chatterBuf.getvalue())
	except:
	#	print 'loading json faild'
		chatterBuf.close()
		chatterCurl.close()
		return []
#	print chatterJ
	try:
		m = chatterJ['chatters']['moderators']
		v = chatterJ['chatters']['viewers']
		viewerArray.extend(chatterJ['chatters']['moderators'])
		viewerArray.extend(chatterJ['chatters']['viewers'])

		chatterBuf.close()
		chatterCurl.close()
	#print len(viewerArray)
		return viewerArray
	except:
		chatterBuf.close()
		chatterCurl.close()
        #print len(viewerArray)
		return []
	
prevStreamerSet = set(getOnlineStreamers())
chatterTable = {}

for streamer in prevStreamerSet:
	chatters =  getChattersForStreamer(streamer)	
	chatterTable[streamer] = set(chatters)


def  logAllChatters():
	newStreamerSet = set(getOnlineStreamers())
	#print len(newStreamerSet)
	#print 'streamers that went online:'	
	onlineSet =  newStreamerSet - prevStreamerSet
	#print("looping through " + str(len(onlineSet)) + " online streamers")
	for streamer in onlineSet:
        	chatters =  getChattersForStreamer(streamer)
        	chatterTable[streamer] = set(chatters)
	
################
	#print 'streamers that went offline:'	
	offlineSet = prevStreamerSet - newStreamerSet
	#print offlineSet
	for streamer in offlineSet:
		logChattersForStreamer(streamer, chatterTable[streamer])
	#print '_____________________________________________'
	prevStreamerSet.difference_update(offlineSet)


	for streamer in prevStreamerSet:
		chatterTable[streamer] |= set(getChattersForStreamer(streamer))
	prevStreamerSet.update(onlineSet)
		


while True:
	logAllChatters()