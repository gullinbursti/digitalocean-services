#!/usr/bin/python

import sys
import logging

handler = logging.StreamHandler(sys.stdout)

sys.path.insert(0, "/var/www/FacebookBot/")
sys.path.insert(0, "/var/www/FacebookBot/FacebookBot/")

from lemonadefb import app as application
application.secret_key = 'TEMBA_HIS_ARMS_WIDE'
