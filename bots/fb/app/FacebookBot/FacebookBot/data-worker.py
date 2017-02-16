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
from sqlalchemy import create_engine, TypeDecorator, Column, Boolean, Float, Integer, String, Unicode, UnicodeText
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


from constants import Const

engine = create_engine("sqlite:///data/sqlite3/prebotfb.db".format(file_path=os.path.dirname(os.path.realpath(__file__))), echo=False)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


class CoerceUTF8(TypeDecorator):
    """Safely coerce Python bytestrings to Unicode
    before passing off to the database."""

    impl = Unicode

    def process_bind_param(self, value, dialect):
        if isinstance(value, str):
            value = value.decode('utf-8')
        return value


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    fb_psid = Column(String(255))
    fb_name = Column(String(255))
    email = Column(String(255))
    referrer = Column(String(255))
    paypal_email = Column(String(255))
    bitcoin_addr = Column(String(255))
    stripe_id = Column(String(255))
    card_id = Column(String(255))
    bitcoin_id = Column(String(255))
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
        return "<Customer id=%s, fb_psid=%s, fb_name=%s, email=%s, bitcoin_addr=%s, referrer=%s, paypal_email=%s, storefront_id=%s, product_id=%s, purchase_id=%s, added=%s>" % (self.id, self.fb_psid, self.fb_name, self.email, self.bitcoin_addr, self.referrer, self.paypal_email, self.storefront_id, self.product_id, self.purchase_id, self.added)


class FBUser(Base):
    __tablename__ = "fb_users"

    id = Column(Integer, primary_key=True)
    fb_psid = Column(String(255))
    first_name = Column(CoerceUTF8)
    last_name = Column(CoerceUTF8)
    profile_pic_url = Column(String(255))
    locale = Column(String(255))
    timezone = Column(Integer)
    gender = Column(String(255))
    payments_enabled = Column(Boolean)
    added = Column(Integer)

    def __init__(self, fb_psid, graph):
        print("graph=%s" % graph)
        self.fb_psid = fb_psid
        self.first_name = graph.get('first_name').encode('utf-8') or None
        self.last_name = graph.get('last_name').encode('utf-8') or None
        self.profile_pic_url = graph.get('profile_pic') or None
        self.locale = graph.get('locale') or None
        self.timezone = graph.get('timezone') or None
        self.gender = graph.get('gender') or None
        self.payments_enabled = graph.get('is_payment_enabled') or False
        self.added = int(time.time())

    @property
    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    @property
    def local_dt(self):
        return datetime.utcfromtimestamp(time.time()).replace(tzinfo=pytz.utc).astimezone(tzoffset(None, self.timezone * 100))

    @property
    def profile_image(self):
        return Image.open(requests.get(self.profile_pic_url, stream=True).raw)

    def __repr__(self):
        return "<FBUser id=%s, fb_psid=%s, first_name=%s, last_name=%s, profile_pic_url=%s, locale=%s, timezone=%s, gender=%s, payments_enabled=%s, added=%s, [full_name=%s, local_dt=%s, profile_image=%s]>" % (self.id, self.fb_psid, self.first_name, self.last_name, self.profile_pic_url, self.locale, self.timezone or 666, self.gender, self.payments_enabled, self.added, self.full_name, self.local_dt, self.profile_image)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    fb_psid = Column(String(255))
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
    views = Column(String(255))
    avg_rating = Column(Float)
    release_date = Column(Integer)
    added = Column(Integer)

    def __init__(self, fb_psid, storefront_id):
        self.fb_psid = fb_psid
        self.storefront_id = storefront_id
        self.creation_state = 0
        self.price = 1.99
        self.views = 0
        self.avg_rating = 0.0
        self.added = int(time.time())

    def __repr__(self):
        return "<Product id=%s, fb_psid=%s, storefront_id=%s, creation_state=%s, name=%s, display_name=%s, image_url=%s, video_url=%s, prebot_url=%s, release_date=%s, views=%s, avg_rating=%.2f, added=%s>" % (self.id, self.fb_psid, self.storefront_id, self.creation_state, self.name, self.display_name, self.image_url, self.video_url, self.prebot_url, self.release_date, self.views, self.avg_rating, self.added)


class Storefront(Base):
    __tablename__ = "storefronts"

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
    views = Column(Integer)
    added = Column(Integer)

    def __init__(self, owner_id, type=1):
        self.owner_id = owner_id
        self.creation_state = 0
        self.type = type
        self.giveaway = 0
        self.views = 0
        self.added = int(time.time())

    def __repr__(self):
        return "<Storefront id=%s, owner_id=%s, creation_state=%s, display_name=%s, logo_url=%s, video_url=%s, prebot_url=%s, giveaway=%s, added=%s>" % (self.id, self.owner_id, self.creation_state, self.display_name, self.logo_url, self.video_url, self.prebot_url, self.giveaway, self.added)



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
            scale_factor = max((src_image.size[0] / float(self.canvas_size[0]), src_image.size[1] / float(self.canvas_size[1])))
            scale_size = ((
                int(round(src_image.size[0] / float(scale_factor))),
                int(round(src_image.size[1] / float(scale_factor)))
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

            # print("[::|::|::|::] CROP ->org=%s, scale_factor=%f, scale_size=%s, padding=%s, area=%s" % (src_image.size, scale_factor, scale_size, padding, area))

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
            logger.info("DOWNLOAD FAILED!!! %s" % (response.text))
        del response



def add_commerce(fb_psid, storefront_name, storefront_description, storefront_logo_url, product_name, product_image, product_video, product_price):
    user_id = add_user(fb_psid)
    storefront_id = add_storefront(fb_psid, storefront_name, storefront_description, storefront_logo_url)
    product_id = add_product(fb_psid, storefront_id, product_name, product_image, product_price)
    return (user_id, storefront_id, product_id)


def name_fill():
    with open("{basepath}/data/csv/kik_names.csv".format(basepath=os.path.dirname(os.path.realpath(__file__))), 'rb') as f:
        for row in csv.reader(f, delimiter=",", quotechar="\""):
            kik_names.append(row[0])

def item_fill():
    with open("{basepath}/data/csv/csgo_items.csv".format(basepath=os.path.dirname(os.path.realpath(__file__))), 'rb') as f:
        for row in csv.DictReader(f, delimiter=",", quotechar="\"", fieldnames=["name", "img_url"]):
            csgo_items.append(row)


def add_user(fb_psid):
    print("add_user(fb_psid={fb_psid})".format(fb_psid=fb_psid))

    try:
        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            #-- check against mysql
            cur.execute('SELECT `id` FROM `users` WHERE `fb_psid` = "{fb_psid}" LIMIT 1;'.format(fb_psid=fb_psid))
            row = cur.fetchone()

            #-- go ahead n' add 'em
            if row is None:
                cur.execute('INSERT INTO `users` (`id`, `fb_psid`, `referrer`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());', (fb_psid, "/"))
                conn.commit()
                cur.execute('SELECT `id`, `added` FROM `users` WHERE `id` = @@IDENTITY LIMIT 1;')
                row = cur.fetchone()

                #-- now add on sqlite w/ the new guy
                customer = session.query(Customer).filter(Customer.fb_psid == fb_psid).first()
                if customer is None:
                    customer = Customer(id=row['id'], fb_psid=fb_psid, referrer="/")
                    session.add(customer)

                else:
                    customer.id = row['id']

            else:
                customer = session.query(Customer).filter(Customer.fb_psid == fb_psid).first()
                if customer is None:
                    customer = Customer(id=row['id'], fb_psid=fb_psid, referrer="/")
                    session.add(customer)

                else:
                    customer.id = row['id']
            session.commit()

    except mysql.Error, e:
        print("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()

    return customer.id



def add_storefront(fb_psid, name, description, logo_url):
    print("add_storefront(fb_psid={fb_psid}, name={name}, description={description}, logo_url={logo_url})".format(fb_psid=fb_psid, name=name, description=description, logo_url=logo_url))

    timestamp = ("%.03f" % (time.time())).replace(".", "_")
    image_file = "/var/www/html/thumbs/{timestamp}.jpg".format(timestamp=timestamp)

    copy_thread = threading.Thread(
        target=copy_remote_asset,
        name="image_copy",
        kwargs={
            'src_url'    : logo_url,
            'local_file' : image_file
        }
    )
    copy_thread.start()
    copy_thread.join()

    image_sizer_sq = ImageSizer(image_file)
    image_sizer_sq.start()

    image_sizer_ls = ImageSizer(in_file=image_file, out_file=None, canvas_size=(400, 300))
    image_sizer_ls.start()

    image_sizer_pt = ImageSizer(in_file=image_file, out_file=None, canvas_size=(480, 640))
    image_sizer_pt.start()

    image_sizer_ws = ImageSizer(in_file=image_file, canvas_size=(1280, 720))
    image_sizer_ws.start()

    customer = session.query(Customer).filter(Customer.fb_psid == fb_psid).first()

    storefront_tmp = Storefront(fb_psid)
    storefront_tmp.creation_state = 4
    storefront_tmp.display_name = name
    storefront_tmp.name = re.sub(r'[\,\'\"\`\~\ \:\;\^\%\#\&\*\@\!\/\?\=\+\-\|\(\)\[\]\{\}\\]', "", name.encode('ascii', 'xmlcharrefreplace'))
    storefront_tmp.prebot_url = "http://prebot.me/{storefront_name}".format(storefront_name=storefront_tmp.name)
    storefront_tmp.logo_url = "http://prebot.me/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
    storefront_tmp.description = description

    storefront = session.query(Storefront).filter(Storefront.owner_id == fb_psid).filter(Storefront.display_name == storefront_tmp.display_name).first()
    if storefront is None:
        storefront = storefront_tmp
        session.add(storefront)

    try:
        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            #-- check against mysql
            cur.execute('SELECT `id` FROM `storefronts` WHERE `owner_id` = {owner_id} AND `display_name` = "{display_name}" LIMIT 1;'.format(owner_id=customer.id, display_name=storefront.display_name))
            row = cur.fetchone()

            #-- not there, so create it
            if row is None:
                cur.execute('INSERT INTO `storefronts` (`id`, `owner_id`, `name`, `display_name`, `description`, `logo_url`, `prebot_url`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP())', (customer.id, storefront.name, storefront.display_name, storefront.description, storefront.logo_url, storefront.prebot_url))
                conn.commit()
                cur.execute('SELECT `id`, `added` FROM `storefronts` WHERE `id` = @@IDENTITY LIMIT 1;')
                row = cur.fetchone()
                storefront.id = row['id']

            #-- update w/ existing id
            else:
                storefront.id = row['id']
            session.commit()

    except mysql.Error, e:
        print("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()

    return storefront.id


def add_product(fb_psid, storefront_id, name, image_url, price=1.99):
    print("add_product(fb_psid={fb_psid}, storefront_id={storefront_id}, name={name}, image_url={image_url}, price={price})".format(fb_psid=fb_psid, storefront_id=storefront_id, name=name, image_url=image_url, price=price))

    timestamp = ("%.03f" % (time.time())).replace(".", "_")
    image_file = "/var/www/html/thumbs/{timestamp}.jpg".format(timestamp=timestamp)

    copy_thread = threading.Thread(
        target=copy_remote_asset,
        name="image_copy",
        kwargs={
            'src_url'    : image_url,
            'local_file' : image_file
        }
    )
    copy_thread.start()
    copy_thread.join()

    image_sizer_sq = ImageSizer(in_file=image_file, out_file=None)
    image_sizer_sq.start()

    image_sizer_ls = ImageSizer(in_file=image_file, out_file=None, canvas_size=(400, 300))
    image_sizer_ls.start()

    image_sizer_pt = ImageSizer(in_file=image_file, out_file=None, canvas_size=(480, 640))
    image_sizer_pt.start()

    image_sizer_ws = ImageSizer(in_file=image_file, canvas_size=(1280, 720))
    image_sizer_ws.start()

    customer = session.query(Customer).filter(Customer.fb_psid == fb_psid).first()
    storefront = session.query(Storefront).filter(Storefront.id == storefront_id).first()

    product_tmp = Product(fb_psid, storefront.id)
    product_tmp.creation_state = 5
    product_tmp.display_name = name
    product_tmp.name = re.sub(r'[\,\'\"\`\~\ \:\;\^\%\#\&\*\@\!\/\?\=\+\-\|\(\)\[\]\{\}\\]', "", name.encode('ascii', 'xmlcharrefreplace'))
    product_tmp.prebot_url = "http://prebot.me/{product_name}".format(product_name=product_tmp.name)
    product_tmp.release_date = calendar.timegm((datetime.utcnow() + relativedelta(months=random.randint(2, 4))).replace(hour=0, minute=0, second=0, microsecond=0).utctimetuple())
    product_tmp.description = "For sale starting on {release_date}".format(release_date=datetime.utcfromtimestamp(int(product_tmp.release_date)).strftime('%a, %b %-d'))
    product_tmp.image_url = "http://prebot.me/thumbs/{timestamp}.jpg".format(timestamp=timestamp)
    product_tmp.price = price

    product = session.query(Product).filter(Product.storefront_id == product_tmp.storefront_id).filter(Product.display_name == product_tmp.display_name).first()
    if product is None:
        product = product_tmp
        session.add(product)

    try:
        conn = mysql.connect(Const.MYSQL_HOST, Const.MYSQL_USER, Const.MYSQL_PASS, Const.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            #-- check against mysql
            cur.execute('SELECT `id` FROM `products` WHERE `display_name` = "{display_name}" AND `storefront_id` IN (SELECT `id` FROM `storefronts` WHERE `id` = "{storefront_id}") LIMIT 1;'.format(display_name=storefront.display_name, storefront_id=storefront.id))
            row = cur.fetchone()

            #-- add to mysql
            if row is None:
                cur.execute('INSERT INTO `products` (`id`, `storefront_id`, `name`, `display_name`, `description`, `image_url`, `price`, `prebot_url`, `release_date`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, FROM_UNIXTIME(%s), UTC_TIMESTAMP())', (product.storefront_id, product.name, product.display_name, product.description, product.image_url, product.price, product.prebot_url, product.release_date))
                conn.commit()
                cur.execute('SELECT `id`, `added` FROM `products` WHERE `id` = @@IDENTITY LIMIT 1;')
                row = cur.fetchone()
                product.id = row['id']

            #-- update w/ existing id
            else:
                product.id = row['id']
            session.commit()

    except mysql.Error, e:
        print("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()

    return product.id



def generate_fb_psid():
    psid = "99"
    for i in range(1, 15):
        psid = "{psid}{rand}".format(psid=psid, rand=random.randint(0, 9))

    return "{psid}".format(psid=psid)


def fb_graph_user(recipient_id):
    print("fb_graph_user(recipient_id=%s)" % (recipient_id))

    params = {
        'fields'       : "first_name,last_name,profile_pic,locale,timezone,gender,is_payment_enabled",
        'access_token' : Const.ACCESS_TOKEN
    }
    response = requests.get("https://graph.facebook.com/v2.6/{recipient_id}".format(recipient_id=recipient_id), params=params)
    return None if 'error' in response.json() else response.json()


def graph_updater():
    for customer in session.query(Customer).filter(Customer.id < 193):
        graph = fb_graph_user(customer.fb_psid)
        if graph is not None:
            fb_user = FBUser(customer.fb_psid, graph)
            session.add(fb_user)

            try:
                conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
                with conn:
                    cur = conn.cursor(mysql.cursors.DictCursor)
                    cur.execute('SELECT `id` FROM `fb_users` WHERE `fb_psid` = %s LIMIT 1;' % (customer.fb_psid,))
                    row = cur.fetchone()

                    if row is None:
                        cur.execute('INSERT INTO `fb_users` (`id`, `user_id`, `fb_psid`, `first_name`, `last_name`, `profile_pic_url`, `locale`, `timezone`, `gender`, `payments_enabled`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, customer.fb_psid or "", fb_user.first_name.decode('utf-8') or "", fb_user.last_name.decode('utf-8') or "", fb_user.profile_pic_url or "", fb_user.locale or "", fb_user.timezone or 666, fb_user.gender or "", int(fb_user.payments_enabled)))
                        conn.commit()
                        cur.execute('SELECT @@IDENTITY AS `id` FROM `fb_users`;')
                        fb_user.id = cur.fetchone()['id']

                    else:
                        fb_user.id = row['id']

                    session.commit()

            except mysql.Error, e:
                print("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

            finally:
                if conn:
                    conn.close()


def product_fb_psid():
    for product in session.query(Product).filter(Product.id > 9866):
        storefront = session.query(Storefront).filter(Storefront.id == product.storefront_id).first()
        if storefront is not None:
            product.fb_psid = storefront.owner_id
            session.commit()

        print(product)


def products_changer():
    storefront_query = session.query(Storefront.id).filter(Storefront.display_name.like('% e-Shop')).subquery('storefront_query')
    for product in session.query(Product).filter(Product.storefront_id.in_(storefront_query)):
        owner_name = product.display_name.replace(" Snaps", "")
        product.display_name = "%s Money Guide" % (owner_name)
        product.name = "%sMoneyGuide" % (owner_name)
        product.prebot_url = product.prebot_url.replace("Snaps", "MoneyGuide")
        session.commit()

        print(product)



kik_names = []
csgo_items = []

name_fill()
item_fill()

print("Creating {name_total} users...".format(name_total=len(kik_names)))

results = []
for kik_name in kik_names:
    cnt = len(results)

    csgo_item = random.choice(csgo_items)
    entry = {
        'user_id'      : 0,
        'fb_psid'      : generate_fb_psid(),
        'kik_name'     : kik_name,
        'storefronts'  : [],
        'products'     : [],
        'item_name'    : csgo_item['name'],
        'item_img_url' : csgo_item['img_url'],
        'timestamp'    : datetime.now().strftime('%Y-%m-%d %H:%M:%s')
    }
    results.append(entry)

    print("Importing ({cnt} / {tot}) --> \"{kik_name}\" as [{fb_psid}]".format(cnt=len(results), tot=len(kik_names), kik_name=entry['kik_name'], fb_psid=entry['fb_psid']))

    customer_id, storefront_id, product_id = add_commerce(
        fb_psid = entry['fb_psid'],
        storefront_name = "{kik_name} Shop".format(kik_name=entry['kik_name']),
        storefront_description = "Buy {kik_name} snapchat pics here!".format(kik_name=entry['kik_name']),
        storefront_logo_url = "http://prebot.me/thumbs/snapchat.png",
        product_name = "{kik_name} Snaps".format(kik_name=entry['kik_name']),
        product_image = "http://prebot.me/thumbs/{card}.jpg".format(card=random.randint(1, 100)),
        product_video = None,
        product_price = round(random.uniform(0.50, 4.99), 2)
    )
    entry['user_id'] = user_id
    entry['storefronts'].append(storefront_id)
    entry['products'].append(product_id)

    customer_id, storefront_id, product_id = add_commerce(
        fb_psid = entry['fb_psid'],
        storefront_name = "{kik_name} e-Shop".format(kik_name=entry['kik_name']),
        storefront_description = "Buy stuff from {kik_name} here!".format(kik_name=entry['kik_name']),
        storefront_logo_url = "https://i.imgur.com/dafKv0U.png",
        product_name = "{kik_name} Money Guide".format(kik_name=entry['kik_name']),
        product_image = "https://i.imgur.com/dafKv0U.png",
        product_video = None,
        product_price = round(random.uniform(0.50, 4.99), 2)
    )
    entry['storefronts'].append(storefront_id)
    entry['products'].append(product_id)

    customer_id, storefront_id, product_id = add_commerce(
        fb_psid = entry['fb_psid'],
        storefront_name = "{kik_name} CS:GO".format(kik_name=entry['kik_name']),
        storefront_description = "Buy CS:GO skins from {kik_name}".format(kik_name=entry['kik_name']),
        storefront_logo_url = entry['item_img_url'],
        product_name = "{item_name}".format(item_name=entry['item_name']),
        product_image = entry['item_img_url'],
        product_video = None,
        product_price = round(random.uniform(0.50, 4.99), 2)
    )



    with open("/var/www/FacebookBot/FacebookBot/log/{file_name}.csv".format(file_name=(os.path.basename(os.path.realpath(__file__))).rsplit(".", 1)[0]), 'a') as f:
        row = []
        for key in entry:
            row.append(entry[key])
        csv.writer(f).writerow(row)

        # writer.writerow([value for key, value in entry.items() if key != 'csgo_item' for v in value])
        # csv.writer(f).writerow(['{0},{1}'.format(key, value) for key, value in entry.items()])

    time.sleep(random.uniform(1, 2))

quit()



add_commerce(generate_fb_psid(), "Bracelets by Anne", "Custom made jewelry just for you", "https://i.imgur.com/prD7TK3.jpg", "BraceletAnne", "https://i.imgur.com/prD7TK3.jpg", None, 3.99)
add_commerce(generate_fb_psid(), "CS:GO Skins Cheap", "Discounted CS:GO items", "https://i.imgur.com/lIP7k1z.jpg", "BraceletAnne", "https://i.imgur.com/lIP7k1z.jpg", None, 4.99)
add_commerce(generate_fb_psid(), "Steam Keys", "Game keys from Steam", "https://i.imgur.com/Z1o0icQ.jpg", "RocketLeague 00", "https://i.imgur.com/Z1o0icQ.jpg", None, 5.99)
add_commerce(generate_fb_psid(), "Knick Knacks", "Little things", "https://i.imgur.com/lnGGJfI.jpg", "Tiny Sword Stand", "https://i.imgur.com/lnGGJfI.jpg", None, 1.99)
quit()



#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#

