import pymysql
import pycurl
import sys
import cStringIO
import json
import time

streamerIdCache = {}


def addStreamerToDb(streamerName):
	conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_tw_usr', passwd='f4zeHUga.age', db='db4086_twitch')
	cur = conn.cursor()
	cur.execute("INSERT INTO `top_cohort` (`id`, `channel`, `added`) VALUES (NULL, \'" + streamerName + "\', NOW())")
	cur.close()
	conn.close()

def getTopStreamers():
	print("getting top stramers")
	for num in range(0, 10):
		print(num)
		buf = cStringIO.StringIO()
#		print(r[0])
		c = pycurl.Curl()
		c.setopt(c.URL, "https://api.twitch.tv/kraken/streams?limit=100&offset=" + str(num*100))
		c.setopt(c.WRITEFUNCTION, buf.write)
		try:
			c.perform()
		
#			print(buf.getvalue())
			j = json.loads(buf.getvalue())
		except:
			print 'curl failed'
			buf.close()
			c.close()
			continue
		buf.close()
		c.close()
		try:
			streams = j['streams']
			for stream in streams:

				displayName = stream["channel"]["display_name"]
				addStreamerToDb(displayName)
		except:
			print 'could not decode stream object'



getTopStreamers()