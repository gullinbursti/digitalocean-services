import pymysql
import pycurl
import sys
import cStringIO
import json
import time

streamerIdCache = {}


def logChattersForStreamer(streamerName, chatters):
#	print "logging chatters for streamer!!!"
	id = streamerIdCache[streamerName]
#	print type(id)
#	print id
	if id == None:
		id = streamerName	
	chattersList = list(chatters)
	asciichatterList = [str(cx) for cx in chattersList]
	mylist = ",".join(asciichatterList)

#	print streamerName + " " + id + " " + mylist
	conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
	cur = conn.cursor()
#	cur.execute("INSERT INTO `stream_chatters` (`channel_name`, `stream_id`, `chatters`, `added`) VALUES (" + streamerName + ", " + id + ", " +  chattersString + ", NOW())")
	cur.execute("INSERT INTO `stream_chatters` (`channel_name`, `stream_id`, `chatters`, `added`) VALUES (\'" + streamerName + "\', \'" + id + "\', \'" +  mylist + "\', NOW())")
	cur.close()
	conn.close()

def getOnlineStreamers():
	onlineStreamers = []
	conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
	cur = conn.cursor()
	cur.execute("SELECT `username` FROM `users` WHERE `type` = 'streamer';")
	for r in cur:
		buf = cStringIO.StringIO()
#		print(r[0])
		c = pycurl.Curl()
		c.setopt(c.URL, "https://api.twitch.tv/kraken/streams/" + r[0])
		c.setopt(c.WRITEFUNCTION, buf.write)
		try:
			c.perform()
		
#			print(buf.getvalue())
			j = json.loads(buf.getvalue())
		except:
#			print 'curl failed'
			buf.close()
			c.close()
			continue
		buf.close()
		c.close()
		try:
			if j['stream']:
#				print r[0]
				onlineStreamers.append(r[0])
				streamerIdCache[str(r[0])] = str(j['stream']['_id'])
		except:
			pass
#	print 'could not decode stream object'	
	cur.close()
	conn.close()

	return onlineStreamers

def getChattersForStreamer(streamerName):
	#print 'getting chatters for ' + str(streamerName)
	viewerArray = []
	chatterBuf = cStringIO.StringIO()
	chatterCurl = pycurl.Curl()
	chatterCurl.setopt(chatterCurl.URL, "https://tmi.twitch.tv/group/user/" + streamerName.lower() + "/chatters")
	chatterCurl.setopt(chatterCurl.WRITEFUNCTION, chatterBuf.write)
	try:
		chatterCurl.perform()
	except: 
		#print 'curl failed'
		chatterBuf.close()
		chatterCurl.close()
		return []
	try:
		chatterJ = json.loads(chatterBuf.getvalue())
	except:
		#print 'loading json faild'
		chatterBuf.close()
		chatterCurl.close()
		return []
		#print chatterJ
	m = chatterJ['chatters']['moderators']
	v = chatterJ['chatters']['viewers']
	viewerArray.extend(chatterJ['chatters']['moderators'])
	viewerArray.extend(chatterJ['chatters']['viewers'])

	chatterBuf.close()
	chatterCurl.close()
	#print len(viewerArray)
	return viewerArray
prevStreamerSet = set(getOnlineStreamers())
chatterTable = {}

for streamer in prevStreamerSet:
	chatters =  getChattersForStreamer(streamer)	
	chatterTable[streamer] = set(chatters)
#print chatterTable
#print len(prevStreamerSet)
#print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
while True:
	newStreamerSet = set(getOnlineStreamers())
#	print len(newStreamerSet)
#	print 'streamers that went online:'	
	onlineSet =  newStreamerSet - prevStreamerSet
#	print onlineSet
	for streamer in onlineSet:
        	chatters =  getChattersForStreamer(streamer)
        	chatterTable[streamer] = set(chatters)
	
################
#	print 'streamers that went offline:'	
	offlineSet = prevStreamerSet - newStreamerSet
#	print offlineSet
	for streamer in offlineSet:
		logChattersForStreamer(streamer, chatterTable[streamer])
#	print '_____________________________________________'
	prevStreamerSet.difference_update(offlineSet)


	for streamer in prevStreamerSet:
		chatterTable[streamer] |= set(getChattersForStreamer(streamer))
	prevStreamerSet.update(onlineSet)
