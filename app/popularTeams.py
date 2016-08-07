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
import pprintpp
import timeit

streamerIdCache = {}


teams = {}


def getOnlineStreamers():
	onlineStreamers = []
	conn = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_tw_usr', passwd='f4zeHUga.age', db='db4086_twitch')
	cur = conn.cursor()
	cur.execute("SELECT * FROM `top_cohort`")
	for r in cur:
#		print("r = " +  str(r))
#		print(" r[1] = " + r[1].lower())
		buf = cStringIO.StringIO()
#               print(r[0])
#               print(r[1])
		c = pycurl.Curl()
		c.setopt(c.URL, "https://api.twitch.tv/kraken/channels/" + r[1].lower() + "/teams" )
		c.setopt(c.WRITEFUNCTION, buf.write)
		try:
			c.perform()
#                       print(buf.getvalue())
			j = json.loads(buf.getvalue())
		except:
#			print 'curl failed'
			buf.close()
			c.close()
			continue
		buf.close()
		c.close()
		try:
			if j['teams']:
#				print len(j['teams'])
				for foo in j['teams']:
#					statement = "INSERT IGNORE INTO `teams` (`team_name`, `member_name`, `added`) VALUES (" + foo['name']
					conn2 = pymysql.connect(host='external-db.s4086.gridserver.com', unix_socket='/tmp/mysql.sock', user='db4086_tw_usr', passwd='f4zeHUga.age', db='db4086_twitch')
					cur2 = conn2.cursor()
        				#cur.execute("SELECT * FROM `top_cohort`")
					cur2.execute("INSERT IGNORE INTO `teams` (`team_name`, `member_name`, `added`) VALUES (\"" + foo['name'] + "\", \"" + r[1].lower() + "\", NOW())")
					#if foo['name'] in teams:
#					print("appending " + r[1].lower() + " to team " + foo['name'])
					cur2.close()
					conn2.close()
					#	teams[foo['name']].append(r[1].lower())
					#else:
					#	print("adding new user " + r[1].lower() + " to team " + foo['name'])
					#	teams[foo['name']] = [r[1].lower()]
		except:
				print 'could not decode stream object'
	cur.close()
	conn.close()

#class Teams(tornado.web.RequestHandler):
#	def get(self):
#		getOnlineStreamers()
#                response = json.dumps(teams)
#                self.write(response)

#application = tornado.web.Application([(r"/teams", Teams)])
#if __name__ == "__main__":
#    application.listen(8890)
#    tornado.ioloop.IOLoop.instance().start()

while True:
	t = timeit.timeit(getOnlineStreamers())
	print(t)

#pprintpp.pprint(json.dumps(teams))

