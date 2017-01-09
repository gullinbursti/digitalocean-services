#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import locale
import logging
import random

from flask_sqlalchemy import SQLAlchemy
from gevent import monkey

from data import Customer, Product, Storefront, Subscription

db = SQLAlchemy()

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler("/var/log/FacebookBot.log")
frmtr = logging.Formatter('%(asctime)s.%(msecs)03d %(module)s.%(funcName)s:%(lineno)d %(levelno)s %(message)s', '%H:%M:%S')
frmtr.formatTime()
hdlr.setFormatter()
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

monkey.patch_all()
locale.setlocale(locale.LC_ALL, 'en_US.utf8')


class LangUtils(object):

    def __init__(self):
        random.seed()

    @staticmethod
    def bool_int(val):
        return val * 1

    @staticmethod
    def int_bool(val):
        return val == 1

    @staticmethod
    def coin_flip(weighted=0.0):
        return random.uniform(0.0, 1.0)

    @staticmethod
    def cmwc_random(seed=None, a=3636507990, b=2**32, logb=32, r=1359):
        seeder = random.Random(seed)
    Q = [seeder.randrange(b) for i in range(r)]
    c = seeder.randrange(b)
    f = bits = 0
    for i in itertools.cycle(range(r)):
        t = a * Q[i] + c
        c = t & (b - 1)
        x = Q[i] = b - 1 - (t >> logb)
        f = (f << logb) | x;  bits += logb
        if bits >= 53:
            yield (f & (2 ** 53 - 1)) * (2 ** -53)
            f >>= 53;  bits -= 53



def drop_sqlite(flag=15):
    logger.info("drop_sql(flag={flag)".format(flag=flag))

    if flag & 1:
        try:
            total = db.session.query(Product).delete()
            db.session.commit()
        except:
            db.session.rollback()

    if flag & 2:
        try:
            total = db.session.query(Storefront).delete()
            db.session.commit()
        except:
            db.session.rollback()

    if flag & 4:
        try:
            total = db.session.query(Customer).delete()
            db.session.commit()
        except:
            db.session.rollback()

    if flag & 8:
        try:
            total = db.session.query(Subscription).delete()
            db.session.commit()
        except:
            db.session.rollback()
