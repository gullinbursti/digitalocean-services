#!/usr/bin/env python

import threading
import json

import httplib
import urllib2
import socket
import requests

import grequests
import pycurl
import cStringIO




def lan_ip():
  return "0.0.0.0"


class AsyncHTTPHandler(urllib2.HTTPHandler):
  def http_response(self, req, response):
    print "response.geturl(%s)" % (response.geturl())
    return response


def sendTracker(category, action, label):
  print "sendTracker(category=%s, action=%s, label=%s)" % (category, action, label)
  
  
  buf = cStringIO.StringIO()
  c = pycurl.Curl()
  c.setopt(c.URL, "http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (category, action, label))
  c.setopt(c.WRITEFUNCTION, buf.write)
  c.setopt(c.CONNECTTIMEOUT, 5)
  c.setopt(c.TIMEOUT, 8)
  c.setopt(c.FAILONERROR, True)
   
#-- POST REQ -->
  #c.setopt(c.POSTFIELDS, 'pizza=Quattro+Stagioni&extra=cheese')
   
#-- HEADER -->
  #c.setopt(c.HTTPHEADER, ['Accept: text/html', 'Accept-Charset: UTF-8'])
   
  try:
    c.perform()
    print "buf.getVal()=%s" % (buf.getValue())
    buf.close()
  
  except:
    print("GA ERROR!")
  
  return True


  # try:
  #   _response = urllib2.urlopen("http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (str(category), str(action), str(label)))
  # 
  # 
  # except urllib2.HTTPError: 
  # except urllib2.URLError: 
  # except httplib.BadStatusLine: 
  # except httplib.HTTPException: 
  # except socket.timeout: 
  # except: 
  # 
  # 
  # 
  # except (socket.error, urllib2.URLError, httplib.HTTPException), e:
  #   print "ERROR!! {err}".format(e)
  #   return
  # return  
  
  
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
  response = requests.post(webhook, data={'payload': payload})
  
  return
  