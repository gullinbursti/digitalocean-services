#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import csv
import glob
import json
import os
import shutil
import sys
import time

import requests


bot_webhook = "http://159.203.250.4:8080/profile-notify"
#bot_webhook = "http://98.248.37.68:8080/profile-notify"

queue_dir = "/opt/kik_bot/queue"
sent_dir = "/opt/kik_bot/queue/sent"


for (dirpath, dirnames, filenames) in os.walk(queue_dir):
  for csv_file in filenames:
    messages = []
    
    with open("{queue_dir}/{filename}".format(queue_dir=queue_dir, filename=csv_file), 'r') as f:
      reader = csv.reader(f)
      for row in reader:
        messages.append({
          'from_user'     : row[0],
          'from_chat_id'  : row[1],
          'to_user'       : row[2],
          'to_chat_id'    : row[3],
          'game_name'     : row[4],
          'img_url'       : row[5]
        })
        
    payload = json.dumps({
      'token'     : "1b9700e13ea17deb5a487adac8930ad2",
      'messages'  : messages
    })
      
    response = requests.post(bot_webhook, data=payload)
    shutil.copy2("{queue_dir}/{filename}".format(queue_dir=queue_dir, filename=csv_file), "{sent_dir}/{filename}".format(sent_dir=sent_dir, filename=csv_file))


#for f in glob.glob("{queue_dir}/*.csv".format(queue_dir=queue_dir)):
#  os.remove("{filepath}".format(filepath=f))
