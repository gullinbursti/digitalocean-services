#!/usr/bin/python

import sys
import logging


logging.basicConfig(stream=sys.stderr)
# logging.basicConfig(
#     stream=sys.stderr,
#     filename='/var/log/FacebookBot.log',
#     level=logging.INFO,
#     format='%(asctime)s - %(funcName)s: %(message)s',
#     datefmt="%d-%b-%Y %H:%M:%S"
# )



sys.path.insert(0, "/var/www/LineBot/")
sys.path.insert(0, "/var/www/LineBot/LineBot/")

from LineBot import app as application
application.secret_key = 'TEMBA_HIS_ARMS_WIDE'