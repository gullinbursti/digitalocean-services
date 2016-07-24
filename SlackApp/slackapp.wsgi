#!/usr/bin/python

import sys
import logging

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, "/var/www/SlackApp/")

from SlackApp import app as application
application.secret_key = 'SHAKA_WHEN_THE_WALLS_FELL'
