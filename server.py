from datetime import date
import tornado.escape
import tornado.ioloop
import tornado.web
import pymysql
import pycurl
import sys
import cStringIO
import json
import time
 
class VersionHandler(tornado.web.RequestHandler):
	def get(self):
		response = { 'version': '3.5.1','last_build':  date.today().isoformat() }
		self.write(response)
 
class AnalyticsPercent(tornado.web.RequestHandler):

	def getStreamersFromDate(self, date, streamerName):
		print str(date[0])
		print str(streamerName[0])
		conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
		cur = conn.cursor()
		cur.execute("SELECT `stream_id`, `chatters` FROM `stream_chatters` WHERE `channel_name` = \'" + str(streamerName[0]) + "\' AND `added` >= \'" + str(date[0]) +  "\'")
		streamerList = []
		for r in cur:
			print str(r)
			streamerList.append(r[0])
		return streamerList

	def getStreamersWithLogs(self):
		conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
		cur = conn.cursor()
		cur.execute("SELECT DISTINCT channel_name from stream_chatters")
		streamerList = []
		for r in cur:
			streamerList.append(r[0])
		return streamerList

	def retrieveStreamerPercent(self, streamer):
		conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
		cur=conn.cursor()
		cur.execute("SELECT chatters FROM stream_chatters WHERE channel_name  = \'" + streamer + "\' ORDER BY added DESC LIMIT 2")
		table = []
		for r in cur:
			table.append(set(r[0].split(",")))

		if len(table) > 1:
			cur.close()
			conn.close()
			return len(table[1]) / len( table[1] & table[0])
		cur.close()
		conn.close()
		return 1

	def logRetention(self, streamerName, percent):
		conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
		cur = conn.cursor()
		cur.execute("SELECT COUNT(*) from retention where channel_name=\'"+streamerName + "\' AND type = \'chatters\'")
		result = cur.fetchone()
		number_of_rows = result[0]
		if number_of_rows == 0:
			#insert
			cur.execute("INSERT INTO `retention` (`id`, `channel_name`, `type`, `value`, `updated`) VALUES (NULL, \'" + streamerName + "\', \'chatters\', " +  str(percent) + ", NOW())")
		else:
			cur.execute("UPDATE retention SET value = " + str(percent) + " WHERE channel_name=\'" + streamerName + "\' AND type = \'chatters\' LIMIT 1")
		#update
		cur.close()
		conn.close()

	def get(self):
		slist = self.getStreamersFromDate(self.get_arguments("date"), self.get_arguments("streamer")) 
		streamers = self.getStreamersWithLogs()		
		lastRetention = 0.1415
		for s in streamers:
			lastRetention = self.retrieveStreamerPercent(s)
			#logRetention(s,lastRetention))
		#hypdwhenDate = id.split('-')
       		response = { 'year': str(len(slist)),  'release_date': date.today().isoformat() }
		self.write(response)


application = tornado.web.Application([(r"/retention", AnalyticsPercent), (r"/version", VersionHandler)]) 
if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
    