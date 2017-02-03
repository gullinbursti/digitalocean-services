#!/usr/bin/env python
# -*- coding: utf-8 -*-


import calendar
import csv
import MySQLdb as mysql
import os
import random
import re
import requests
import threading
import time

from datetime import datetime

from dateutil.relativedelta import relativedelta
from PIL import Image
from sqlalchemy import create_engine, Column, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from constants import Const

engine = create_engine('sqlite:///prebotfb.db', echo=True)

Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#

class Customer(Base):
    __tablename__ = "customer"

    id = Column(Integer, primary_key=True)
    fb_psid = Column(String(255))
    fb_name = Column(String(255))
    email = Column(String(255))
    referrer = Column(String(255))
    stripe_id = Column(String(255))
    card_id = Column(String(255))
    storefront_id = Column(Integer)
    product_id = Column(Integer)
    purchase_id = Column(Integer)
    added = Column(Integer)

    def __init__(self, id, fb_psid, referrer="/"):
        self.id = id
        self.fb_psid = fb_psid
        self.referrer = referrer
        self.added = int(time.time())

    def __repr__(self):
        return "<Customer fb_psid=%s, fb_name=%s, referrer=%s>" % (self.fb_psid, self.fb_name, self.referrer)


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True)
    storefront_id = Column(Integer)
    creation_state = Column(Integer)
    name = Column(String(255))
    display_name = Column(String(255))
    description = Column(String(255))
    image_url = Column(String(255))
    video_url = Column(String(255))
    broadcast_message = Column(String(255))
    attachment_id = Column(String(255))
    price = Column(Float)
    prebot_url = Column(String(255))
    release_date = Column(Integer)
    added = Column(Integer)

    def __init__(self, storefront_id):
        self.storefront_id = storefront_id
        self.creation_state = 0
        self.price = 1.99
        self.added = int(time.time())

    def __repr__(self):
        return "<Product storefront_id=%d, creation_state=%d, display_name=%s, release_date=%s>" % (self.storefront_id, self.creation_state, self.display_name, self.release_date)


class Storefront(Base):
    __tablename__ = "storefront"

    id = Column(Integer, primary_key=True)
    owner_id = Column(String(255))
    creation_state = Column(Integer)
    type = Column(Integer)
    name = Column(String(255))
    display_name = Column(String(255))
    description = Column(String(255))
    logo_url = Column(String(255))
    video_url = Column(String(255))
    prebot_url = Column(String(255))
    giveaway = Column(Integer)
    added = Column(Integer)

    def __init__(self, owner_id, type=1):
        self.owner_id = owner_id
        self.creation_state = 0
        self.type = type
        self.giveaway = 0
        self.added = int(time.time())

    def __repr__(self):
        return "<Storefront owner_id=%s, creation_state=%d, display_name=%s, giveaway=%d>" % (self.owner_id, self.creation_state, self.display_name, self.giveaway)


class ImageCopier(threading.Thread):
    def __init__(self, src_url, out_file=None):
        threading.Thread.__init__(self)
        self.src_url = src_url
        self.out_file = out_file

    def run(self):
        os.chdir(os.path.dirname(self.out_file))


class ImageSizer(threading.Thread):
    def __init__(self, in_file, out_file=None, canvas_size=(256, 256)):
        if out_file is None:
            out_file = in_file

        threading.Thread.__init__(self)
        self.in_file = in_file
        self.out_file = out_file
        self.canvas_size = canvas_size

    def run(self):
        os.chdir(os.path.dirname(self.in_file))
        with Image.open(self.in_file.split("/")[-1]) as src_image:
            ratio = src_image.size[0] / float(src_image.size[1])
            scale_factor = self.canvas_size[0] / float(src_image.size[0])

            scale_size = ((
                int(src_image.size[0] * float(scale_factor)),
                int((src_image.size[0] * scale_factor) / float(ratio))
            ))

            padding = (
                int((self.canvas_size[0] - scale_size[0]) * 0.5),
                int((self.canvas_size[1] - scale_size[1]) * 0.5)
            )

            area = (
                -padding[0],
                -padding[1],
                self.canvas_size[0] - padding[0],
                self.canvas_size[1] - padding[1]
            )

            print("::::::::::] CROP ->scale_factor=%f, scale_size=%s, padding=%s, area=%s" % (scale_factor, scale_size, padding, area))

            out_image = src_image.resize(scale_size, Image.BILINEAR).crop(area)
            os.chdir(os.path.dirname(self.out_file))
            out_image.save("{out_file}".format(out_file=("-{sq}.".format(sq=self.canvas_size[0])).join(self.out_file.split("/")[-1].split("."))))


def copy_remote_asset(src_url, local_file):
    print("copy_remote_asset(src_url={src_url}, local_file={local_file})".format(src_url=src_url, local_file=local_file))

    with open(local_file, 'wb') as handle:
        response = requests.get(src_url, stream=True)
        if response.status_code == 200:
            for block in response.iter_content(1024):
                handle.write(block)
        else:
            print("DOWNLOAD FAILED!!! %s" % (response.text))
        del response


def add_user(recipient_id):
    print("add_user(recipient_id={recipient_id})".format(recipient_id=recipient_id))

    try:
        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            #-- check db for existing user
            cur.execute('SELECT `id` FROM `users` WHERE `fb_psid` = "{fb_psid}" LIMIT 1;'.format(fb_psid=recipient_id))
            row = cur.fetchone()

            #-- go ahead n' add 'em
            if row is None:
                cur.execute('INSERT IGNORE INTO `users` (`id`, `fb_psid`, `referrer`, `added`) VALUES (NULL, "{fb_psid}", "{referrer}", UTC_TIMESTAMP());'.format(fb_psid=recipient_id, referrer="/"))
                conn.commit()

                #-- now update sqlite w/ the new guy
                users_query = session.query(Customer).filter(Customer.fb_psid == recipient_id)
                if users_query.count() == 0:
                    session.add(Customer(id=cur.lastrowid, fb_psid=recipient_id, referrer="/"))

                else:
                    customer = users_query.first()
                    customer.id = row['id']

                session.commit()


    except mysql.Error, e:
        print("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()



def add_storefront(recipient_id, name, description, logo_url):
    print("add_storefront(recipient_id={recipient_id}, name={name}, description={description}, logo_url={logo_url})".format(recipient_id=recipient_id, name=name, description=description, logo_url=logo_url))

    customer = session.query(Customer).filter(Customer.fb_psid == recipient_id).first()

    storefront = Storefront(recipient_id)
    storefront.creation_state = 4
    storefront.display_name = name
    storefront.name = re.sub(r'[\,\'\"\ \:\;\^\%\#\&\*\@\!\/\?\=\+\|\(\)\\]', "", name)
    storefront.prebot_url = "http://prebot.me/{storefront_name}".format(storefront_name=storefront.name)
    storefront.logo_url = logo_url
    storefront.description = description

    try:
        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('INSERT IGNORE INTO `storefronts` (`id`, `owner_id`, `name`, `display_name`, `description`, `logo_url`, `prebot_url`, `added`) VALUES (NULL, {owner_id}, "{name}", "{display_name}", "{description}", "{logo_url}", "{prebot_url}", UTC_TIMESTAMP())'.format(owner_id=customer.id, name=storefront.name, display_name=storefront.display_name, description=storefront.description, logo_url=storefront.logo_url, prebot_url=storefront.prebot_url))
            conn.commit()
            storefront.id = cur.lastrowid
            session.add(storefront)
            session.commit()

    except mysql.Error, e:
        print("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()



def add_product(recipient_id, name, image_url, price=1.99):
    print("add_product(recipient_id={recipient_id}, name={name}, image_url={image_url}, price={price})".format(recipient_id=recipient_id, name=name, image_url=image_url, price=price))

    customer = session.query(Customer).filter(Customer.fb_psid == recipient_id).first()
    storefront = session.query(Storefront).filter(Storefront.owner_id == recipient_id).order_by(Storefront.added.desc()).first()

    product = Product(storefront.id)
    product.creation_state = 5
    product.display_name = name
    product.name = re.sub(r'[\,\'\"\ \:\;\^\%\#\&\*\@\!\/\?\=\+\|\(\)\\]', "", name)
    product.prebot_url = "http://prebot.me/{product_name}".format(product_name=product.name)
    product.price = price
    product.release_date = calendar.timegm((datetime.utcnow() + relativedelta(months=random.randint(2, 4))).replace(hour=0, minute=0, second=0, microsecond=0).utctimetuple())
    product.description = "Pre-release ends {release_date}".format(release_date=datetime.utcfromtimestamp(int(product.release_date)).strftime('%a, %b %-d'))
    product.image_url = image_url
    product.video_url = ""
    product.attachment_id = ""

    try:
        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('INSERT IGNORE INTO `products` (`id`, `storefront_id`, `name`, `display_name`, `description`, `image_url`, `video_url`, `attachment_id`, `price`, `prebot_url`, `release_date`, `added`) VALUES (NULL, {storefront_id}, "{name}", "{display_name}", "{description}", "{image_url}", "{video_url}", "{attachment_id}", {price}, "{prebot_url}", FROM_UNIXTIME({release_date}), UTC_TIMESTAMP())'.format(storefront_id=product.storefront_id, name=product.name, display_name=product.display_name, description=product.description, image_url=product.image_url, video_url=product.video_url, attachment_id=product.attachment_id, price=product.price, prebot_url=product.prebot_url, release_date=product.release_date))
            conn.commit()
            product.id = cur.lastrowid
            session.add(product)
            session.commit()

    except mysql.Error, e:
        print("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()



def generate_fb_pid():
    psid = "9"
    for i in range(1, 16):
        psid = "{psid}{rand}".format(psid=psid, rand=random.randint(0, 9))

    return psid



with open("items.txt") as f:
    items = f.readlines()
items = [x.strip() for x in items]


with open("senders.txt") as f:
    names = f.readlines()
names = [x.strip() for x in names]


for name in names:
    print(name)

    fb_psid = generate_fb_pid()
    item = random.choice(items)


    add_user(fb_psid)
    add_storefront(fb_psid, "{name} Shop".format(name=name), "Buy {name} snapchat pics here!".format(name=name), "http://prebot.me/thumbs/snapchat.png")
    add_product(fb_psid, "{name} Snaps".format(name=name), "http://prebot.me/thumbs/{card}.jpg".format(card=random.randint(1, 100)), round(random.uniform(0.50, 4.99), 2))

    add_storefront(fb_psid, "{name} CS:GO".format(name=name), "Buy CS:GO skins from {name}".format(name=name), item.split(",")[-1])
    add_product(fb_psid, "{item_name}".format(item_name=item.split(",")[0]), item.split(",")[-1], round(random.uniform(0.50, 4.99), 2))

    add_storefront(fb_psid, "{name} e-Shop".format(name=name), "Buy stuff from {name} here!".format(name=name), "https://i.imgur.com/dafKv0U.png")
    add_product(fb_psid, "{name} Snaps".format(name=name), "https://i.imgur.com/dafKv0U.png", round(random.uniform(0.50, 4.99), 2))


    with open("/var/www/FacebookBot/FacebookBot/log/import.csv", 'a') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%s'), fb_psid, name])


    time.sleep(random.uniform(60, 90))




#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#

