#!/bin/bash -
/usr/bin/python /var/opt/SteamStats.py
root@Crusher:/var/opt# cat SteamStats.py
import steamapi
from datetime import date
import tornado.escape
import tornado.ioloop
import tornado.web
import pycurl
import sys
import cStringIO
import json
import time
from datetime import datetime



class SteamStats(tornado.web.RequestHandler):
        def get(self):
                streamerName = self.get_arguments('streamer')[0]
		steamapi.core.APIConnection(api_key="1BE173F1F7E24CA8ABD912D16D169EED")
		me =  steamapi.user.SteamUser(userurl=streamerName)
		print(me._summary)
		stats = {"level":me.level, "currently_playing":me.currently_playing, "profile_url": me.profile_url, "name":me.name}
		self.write(json.dumps(stats))


class Avatar(tornado.web.RequestHandler):
        def get(self):
                streamerName = self.get_arguments('streamer')[0]
                steamapi.core.APIConnection(api_key="1BE173F1F7E24CA8ABD912D16D169EED")
                me =  steamapi.user.SteamUser(userurl=streamerName)
                self.write(me.avatar)


application = tornado.web.Application([(r"/stats", SteamStats), (r"/avatar", Avatar)])
if __name__ == "__main__":

## TODO reconstruct who subscribed for what from  into subscribersForStreamer
    application.listen(8890)
    tornado.ioloop.IOLoop.instance().start()
