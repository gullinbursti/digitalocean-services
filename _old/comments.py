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



class GetComments(tornado.web.RequestHandler):
	def getPopular(self):
		popStreamers = []
		conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_tw_usr', passwd='f4zeHUga.age', db='db4086_twitch')
		cur = conn.cursor()
		cur.execute("SELECT * FROM `top_cohort`")
		for r in cur:
			print r[1]
			percent = self.retrieveStreamerPercent(r[1].lower())
			popStreamers.append([r[1].lower(),percent])
		cur.close()
		conn.close()
		return popStreamers
        def get(self):
                popularStreamers = self.getPopularStreamers()
		print(popularStreamers)
		def getKey(item):
			return item[1]
		popularStreamers = sorted(popularStreamers, key=getKey, reverse=True)
                response = json.dumps(popularStreamers)
                self.write(response)


class PostComment(tornado.web.RequestHandler):
        def serialize(self, _from, _to, _body):
                conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_tw_usr', passwd='f4zeHUga.age', db='db4086_twitch')
                cur=conn.cursor()
                cur.execute("SELECT chatters FROM stream_chatters WHERE channel_name  = \'" + streamer + "\' ORDER BY added DESC LIMIT 2")
		#cur.execute("INSERT INTO `comments` (`id`, `channel_name`, `stream_id`, `commenter_name`, `message`, `added`) VALUES (NULL, \'" + channelName + "\', \'" + streamID + "\', \'" + commenterName + "\', \'" + message + "\', NOW())")

                cur.close()
                conn.close()
                return 1
        def get(self):
		#3 params - 
                serialize(self.get_arguments("from")[0], self.get_arguments("to")[0], self.get_arguments("messageBody")[0])
                 
                response = { 'cohort': retention }
                self.write(response)

application = tornado.web.Application([(r"/postComment", PostComment), (r"/getComments", GetComments)])
if __name__ == "__main__":
    application.listen(8892)
    tornado.ioloop.IOLoop.instance().start()

