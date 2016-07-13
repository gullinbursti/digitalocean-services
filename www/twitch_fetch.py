import sys
import json
import urllib, urllib2
import tornado.escape, tornado.ioloop, tornado.web

from datetime import date, datetime


def curl_json(url):
  _response = urllib2.urlopen(url)
  _json = json.load(_response, 'utf-8')

  return _json


class ChannelFetch(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

  def get(self, channel_name):
    print "ChannelFetch:[%s]" % (channel_name)
    _json = curl_json("https://api.twitch.tv/kraken/channels/%s" % (channel_name.lower()))
    self.write(json.dumps(_json))


class StreamFetch(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

  def get(self, channel_name):
    print "StreamFetch:[%s]" % (channel_name)
    _json = curl_json("https://api.twitch.tv/kraken/streams/%s" % (channel_name.lower()))
    self.write(json.dumps(_json))


class TeamsFetch(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

  def get(self, channel_name):
    print "TeamsFetch:[%s]" % (channel_name)
    _json = curl_json("https://api.twitch.tv/kraken/channels/%s/teams" % (channel_name.lower()))
    self.write(json.dumps(_json))


class ChattersFetch(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

  def get(self, channel_name):
    print "ChattersFetch:[%s]" % (channel_name)
    _json = curl_json("http://tmi.twitch.tv/group/user/%s/chatters" % (channel_name.lower()))
    self.write(json.dumps(_json))

class ChannelStreaming(tornado.web.RequestHandler):
  def set_default_headers(self):
    self.set_header("Access-Control-Allow-Origin", "*")
    self.set_header("Access-Control-Allow-Headers", "x-requested-with")
    self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

  def get(self, channel_name):
    print "ChannelStreaming:[%s]" % (channel_name)
    _json = curl_json("https://api.twitch.tv/kraken/streams/%s" % (channel_name.lower()))
    #_json = curl_json("http://127.0.0.1:8081/stream/%s" % (channel_name.lower()))

    if _json['stream'] is not None:
      self.write(json.dumps({'result': True}))

    else:
      self.write(json.dumps({'result': False}))



#-- register endpts
application = tornado.web.Application([(r"/channel/([A-Za-z0-9\._]+)", ChannelFetch), (r"/stream/([A-Za-z0-9\._]+)", StreamFetch), (r"/streaming/([A-Za-z0-9\._]+)", ChannelStreaming), (r"/teams/([A-Za-z0-9\._]+)", TeamsFetch), (r"/chatters/([A-Za-z0-9\._]+)", ChattersFetch)])


#-- start server
if __name__ == "__main__":
  application.listen(8081)
  tornado.ioloop.IOLoop.instance().start()
  print "Starting Tornado..."
