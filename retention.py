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

class Retention(tornado.web.RequestHandler):
	def set_default_headers(self):
		self.set_header("Access-Control-Allow-Origin", "*")
		self.set_header("Access-Control-Allow-Headers", "x-requested-with")
		self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

        def retrieveStreamerPercent(self, streamer):
                conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
                cur=conn.cursor()
                cur.execute("SELECT chatters FROM stream_chatters WHERE channel_name  = \'" + streamer + "\' ORDER BY added DESC LIMIT 2")
                table = []

                for r in cur:
                        table.append(set(r[0].split(",")))
#                print(table)
                if len(table) > 1:
                        cur.close()
                        conn.close()

                        return float(len( table[1] & table[0])) / float(len(table[1]))
                cur.close()
                conn.close()
                return 1
        def get(self):
                retention = self.retrieveStreamerPercent(self.get_arguments("streamer")[0])
                #for s in streamers:
                #        lastRetention = self.retrieveStreamerPercent(s)
                        #logRetention(s,lastRetention))
                #hypdwhenDate = id.split('-')
                response = { 'percent':retention  }
                self.write(response)
	
	def options(self):
		# no body
		self.set_status(204)
		self.finish()

class Cohort(tornado.web.RequestHandler):
	def set_default_headers(self):
		self.set_header("Access-Control-Allow-Origin", "*")
		self.set_header("Access-Control-Allow-Headers", "x-requested-with")
		self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

        def getStreamersFromDate(self, date, streamerName):
                conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
                cur = conn.cursor()
                cur.execute("SELECT `stream_id`, `chatters` FROM `stream_chatters` WHERE `channel_name` = \'" + str(streamerName) + "\' AND `added` >= \'" + str(date) +  "\'")
                streamerList = []

                for r in cur:
#                        print str(r)
                        streamerList.append(set(r[1].split(",")))
                streamerGraph = []
                for i in range(len(streamerList)):
			if i == 0:
                                continue
                        streamerGraph.append({"id":r[0] , "percent":float(len( streamerList[i] & streamerList[0])) / float(len(streamerList[0]))})
		return streamerGraph

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
                        return float(len( table[1] & table[0])) / float(len(table[1]))
                cur.close()
                conn.close()
                return 1
        def get(self):
                retention = self.getStreamersFromDate(self.get_arguments("date")[0], self.get_arguments("streamer")[0])
                if len(retention) == 0:
			self.write({'error' : 'no sessions found'})
			return
		response = { 'cohort': retention }
                self.write(response)
	def options(self):
		# no body
		self.set_status(204)
		self.finish()


class CohortChart(tornado.web.RequestHandler):
        def getStreamersWithLogs(self):
                conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_modd_usr', passwd='f4zeHUga.age', db='db4086_modd')
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT channel_name from stream_chatters")
                streamerList = []
                for r in cur:
                        streamerList.append(r[0])
                return streamerList

application = tornado.web.Application([(r"/retention", Retention), (r"/cohort", Cohort)])
if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()



