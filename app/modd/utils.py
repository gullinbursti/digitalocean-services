#!/usr/bin/env python

import threading
import json

import urllib2
import grequests


def lan_ip():
  
  
  return "0.0.0.0"


class AsyncHTTPHandler(urllib2.HTTPHandler):
  def http_response(self, req, response):
    print "response.geturl(%s)" % (response.geturl())
    return response


def sendTracker(category, action, label):
  print "sendTracker(category=%s, action=%s, label=%s)" % (category, action, label)  
  try:
    _response = urllib2.urlopen("http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (str(category), str(action), str(label)))

  except:
    print "GA ERROR!"

  return
  
  
    # _o = urllib2.build_opener(AsyncHTTPHandler())
    # _t = threading.Thread(target=_o.open, args=("http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (str(category), str(action), str(label)),))
    # _t.start()
    
    # print "--> AsyncHTTPHandler :: _o=%s" % (_o)
  return


def slack_send(channel, webhook, message_txt, from_user="game.bots"):
  print "slack_send(channel=%s, webhook=%s, message_txt=%s, from_user=%s)" % (channel, webhook, message_txt, from_user)
  payload = json.dumps({
    'channel': "#" + channel, 
    'username': from_user,
    'icon_url': "http://i.imgur.com/ETxDeXe.jpg",
    'text': message_txt
  })
  
  _rs = (grequests.post(i, data={'payload': payload}) for i in [webhook])
  grequests.map(_rs)
  
  print "--> async grequests.post(i=%s, data=%s)" % (webhook, payload)
  