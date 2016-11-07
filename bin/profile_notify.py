#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import csv
import hashlib
import json
import os
import shutil
import sys
import time

import grequests
import requests


bot_webhook = "http://159.203.250.4:8080/profile-notify"
#bot_webhook = "http://98.248.37.68:8080/profile-notify"

queue_dir = "/opt/kik_bot/queue"
sent_dir = "/opt/kik_bot/queue/sent"

tracking_urls = []

for (dirpath, dirnames, filenames) in os.walk(queue_dir):
  if dirpath == queue_dir:
    for csv_file in filenames:
      messages = []
      with open("{queue_dir}/{filename}".format(queue_dir=queue_dir, filename=csv_file), 'r') as f:
        reader = csv.reader(f)
        for row in reader:
          tracking_urls.append("http://beta.modd.live/api/user_tracking.php?username={username}&chat_id={chat_id}".format(username=row[1], chat_id=row[2]))
          tracking_urls.append("http://beta.modd.live/api/bot_tracker.php?src=kik&category=player-message&action={action}&label={label}&value=0&cid={cid}".format(action=row[1], label=row[2], cid=hashlib.md5(row[1].encode()).hexdigest()))
        
          messages.append({
            'target_id'     : row[0],
            'from_user'     : row[1],
            'from_chat_id'  : row[2],
            'to_user'       : row[3],
            'to_chat_id'    : row[4],
            'game_name'     : row[5],
            'img_url'       : row[6]
          })
        
      payload = json.dumps({
        'token'     : "1b9700e13ea17deb5a487adac8930ad2",
        'messages'  : messages
      })
      
      response = requests.post(bot_webhook, data=payload)
      shutil.move("{queue_dir}/{filename}".format(queue_dir=queue_dir, filename=csv_file), "{sent_dir}/{filename}".format(sent_dir=sent_dir, filename=csv_file))


responses = (grequests.get(url) for url in tracking_urls)
grequests.map(responses)
