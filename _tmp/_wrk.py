#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import time
import csv
import json
import random
import sqlite3
import datetime, time

import urllib2
import requests
import netifaces as ni
import MySQLdb as mdb

import tornado.escape
import tornado.ioloop
import tornado.web

import modd


from datetime import date
from urllib2 import quote



conn = sqlite3.connect("%s/data/sqlite3/topics.db" % (os.getcwd()))
c = conn.cursor()
#c.execute('''CREATE TABLE faqs (id INTEGER PRIMARY KEY, title VARCHAR(255), content TEXT, added DATE, updated DATE)''')

c.execute("INSERT INTO faqs(id, title, content, added, updated) VALUES (NULL, '_{TITLE}_', '_{CONTENT}_', '%s', '%s')" % (datetime.datetime.now(), datetime.datetime.now()))
conn.commit()
conn.close()
