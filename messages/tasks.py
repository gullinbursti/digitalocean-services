import os, os.path
import sys

import requests
import urllib2
import locale
import csv
import json

from celery import group
from celery.task import task
from unidecode import unidecode
from urllib2 import quote, unquote
# --#--#--#--#--#--#--#--#--#--#--#--#--#--#-- #


def curl_json(url, encoding='utf-8'):
  try:
    _response = urllib2.urlopen(url, timeout=5)

  except Exception:
    return json.load("", encoding)

  return json.load(_response, encoding)

def script_dir():
  return os.path.split(os.path.abspath(__file__))[0]

def int_frmt(val):
  return locale.format('%d', int(val), grouping=True)


@task
def ranged_streams(start=0, inc=100):
  stream_arr = []
  _json = curl_json("https://api.twitch.tv/kraken/streams/?limit=%d&offset=%d" % (inc, start))
  for stream in _json['streams']:
    if len(_json) == 0:
      break

    stream_arr.append(stream)

  return stream_arr


@task(ignore_result=True)
def update_streams(amt=30000):
  DEV_MODD_API	= "http://beta.modd.live/api/import_streamers.php"

  inc = 100
  csv_path = "%s/var/live_streams.csv" % (script_dir())

  tot = curl_json("https://api.twitch.tv/kraken/streams/?limit=1&offset=0")['_total']
  amt = min(amt, tot)
  pgs = int(amt / inc) + 1

  print "Fetching %s streams, %d at a time..." % (int_frmt(amt), inc)

  _arr = []
  for i in range(0, pgs):
    _json = curl_json("https://api.twitch.tv/kraken/streams/?limit=%d&offset=%d" % (inc, (i * inc)))

    if len(_json) == 0:
      break

    print "#[%03d/%03d] - %s" % ((len(_arr) / inc), pgs, (int_frmt(len(_arr))))
    for stream in _json['streams']:
      _arr.append({
        'stream_id'     : str(stream['_id']).encode('utf-8'),
        'channel_id'    : str(stream['channel']['_id']).encode('utf-8'),
        'display_name'  : unicode(stream['channel']['display_name']).encode('utf-8'),
        'channel_logo'  : str(stream['channel']['logo']).encode('utf-8'),
        'game_name'     : unicode(stream['game']).encode('utf-8'),
        'viewers'       : stream['viewers'],
        'channel_views' : stream['channel']['views'],
        'followers'     : stream['channel']['followers'],
        'created_at'    : str(stream['created_at']).encode('utf-8')
      })

  if os.path.isfile(csv_path):
    os.remove(csv_path)

  for _obj in _arr:
    with open(csv_path, 'a') as _csv:
      writer = csv.writer(_csv)
      writer.writerow([_obj['stream_id'], _obj['channel_id'], _obj['display_name'], _obj['channel_logo'], _obj['game_name'], _obj['viewers'], _obj['channel_views'], _obj['followers'], _obj['created_at']])

  print "\nTOTAL      : %s" % (int_frmt(len(_arr)))
  print "Submitting CSV --> %s" % (DEV_MODD_API)
  files = {'streams': open(csv_path, 'rb')}
  _r = requests.post(DEV_MODD_API, files=files)
  print "Upload success!\n%s" % (_r.json())


@task
def channel_info(channel_name):
  return curl_json("http://127.0.0.1:8081/channel/%s" % (channel_name.lower()))


@task
def stream_info(channel_name):
  return curl_json("http://127.0.0.1:8081/stream/%s" % (channel_name.lower()))


@task
def team_info(channel_name):
  return curl_json("http://127.0.0.1:8081/teams/%s" % (channel_name.lower()))


@task
def chatters_info(channel_name):
  return curl_json("http://127.0.0.1:8081/chatters/%s" % (channel_name.lower()))



#-- locale en_US
locale.setlocale(locale.LC_ALL, 'en_US')



#-- invoke
#if len(sys.argv) > 1:
#  print update_streams(sys.argv[1])
