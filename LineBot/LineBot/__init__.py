import base64
import hmac
import hashlib
import locale
import logging
import os
import random
import re
import time
import urllib

import MySQLdb as mysql

from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import LineBotApiError
from linebot.models import MessageEvent, TextMessage, ImageSendMessage, StickerSendMessage, TextSendMessage, VideoSendMessage, SourceUser, SourceGroup, SourceRoom, TemplateSendMessage, ConfirmTemplate, MessageTemplateAction, ButtonsTemplate, URITemplateAction, PostbackTemplateAction, CarouselTemplate, CarouselColumn, PostbackEvent, StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage, ImageMessage, VideoMessage, AudioMessage, UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent

from constants import Const

app = Flask(__name__)
app.secret_key = os.urandom(24)

locale.setlocale(locale.LC_ALL, 'en_US.utf8')

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler("/var/log/LineBot.log")
formatter = logging.Formatter("%(asctime)s - %(message)s", '%d-%b-%Y %H:%M:%S')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

line_bot_api = LineBotApi('nfQJjb0MP5+AHAuc79f5W5unuiqf0eTsrsZmkg8eK7j3mQHauQfWVg38LnYhw/3FaPHWR3wh9qodQqi0dQUDqkdWC40JmVrpDdtk5iZg5+KGkGDV5+gu7HFq5ufYYzRORPyzKoNZ9qRPWQL1aeUycAdB04t89/1O/w1cDnyilFU=')


@app.route('/')
def hello():
    return "Hello", 200


@app.route('/', methods=['POST'])
def default():
    events = request.json

    # logger.info("request.json=%s" % (events,))

    channel_signature = request.headers['X-Line-Signature']
    hash = hmac.new("4bf2db692f5e3705b8d1bf6d82e35dc8".encode('utf-8'), request.data, hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode()

    if not hmac.compare_digest(channel_signature, signature):
        logging.error("HMAC no good!")
        return "HMAC verification mismatch", 403

    for event in events['events']:
        logger.info("event=%s" % (event,))
        reply_token = event['replyToken']
        user_id = event['source']['userId']


        if event['type'] == "follow":
            text_message(
                user_id=event['source']['userId'],
                message="Welcome to Lemonade on Line sponsored by Disney Tsum Tsum"
            )

            video_message(
                user_id=event['source']['userId'],
                thumb_url="https://i.imgur.com/VPr9NZR.jpg",
                video_url="https://prekey.co/static/stacks.mp4"
            )

        elif 'postback' in event:
            handle_postback(
                user_id=event['source']['userId'],
                payload=event['postback']['data'],
            )

        else:
            main_carousel(
                user_id=event['source']['userId']
            )

    return "OK", 200


def storefront_templates():
    logger.info("storefront_templates()")

    return [
        {
            'index'      : 0,
            'title'      : "M4A4 | Desolate Space",
            'description': "CSGO Item",
            'image_url'  : "https://i.imgur.com/qrwkaGq.jpg",
            'price'      : 9.99,
            'query_term' : "M4A4DesolateSpace"
        }, {
            'index'      : 1,
            'title'      : "Sxyhxy's Body Armor",
            'description': "H1Z1 Item",
            'image_url'  : "https://i.imgur.com/TZRtwsg.jpg",
            'price'      : 4.99,
            'query_term' : "SxyhxysBodyArmor"
        }, {
            'index'      : 2,
            'title'      : "MAC-10 | Neon Rider",
            'description': "CSGO Item",
            'image_url'  : "https://i.imgur.com/u12Z6G2.jpg",
            'price'      : 4.99,
            'query_term' : "MAC10NeonRider"
        }, {
            'index'      : 3,
            'title'      : "P2000 Imperial Dragon",
            'description': "CSGO Item",
            'image_url'  : "https://i.imgur.com/D8fJbrN.jpg",
            'price'      : 4.99,
            'query_term' : "P2000ImperialDragon"
        }, {
            'index'      : 4,
            'title'      : "Claws of the Blood Moon",
            'description': "Dota 2 Item",
            'image_url'  : "https://i.imgur.com/KAkicdD.jpg",
            'price'      : 1.99,
            'query_term' : "ClawsoftheBloodMoon"
        }, {
            'index'      : 5,
            'title'      : "M4A1-S | Hyper Beast",
            'description': "CSGO Item",
            'image_url'  : "https://i.imgur.com/QFLtVjU.jpg",
            'price'      : 1.99,
            'query_term' : "M4A1SHyperBeast"
        }
    ]


def storefront_lookup(storefront_id):
    logger.info("storefront_lookup(storefront_id=%s)" % (storefront_id,))

    storefront = None
    conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            product = None
            while product is None:
                cur.execute('SELECT `id`, `display_name`, `logo_url` FROM `storefronts` WHERE `id` = %s LIMIT 1;', (storefront_id,))
                row = cur.fetchone()
                if row is not None:
                    storefront = row

    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return storefront



def product_lookup(product_id):
    logger.info("product_lookup(product_id=%s)" % (product_id,))

    product = None
    conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            product = None
            while product is None:
                cur.execute('SELECT `id`, `display_name`, `image_url`, `price`, `prebot_url` FROM `products` WHERE `id` = %s LIMIT 1;', (product_id,))
                row = cur.fetchone()
                if row is not None:
                    product = row

    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return product


def product_search(query_term):
    logger.info("product_search(query_term=%s)" % (query_term,))

    product = None
    conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)

            product = None
            while product is None:
                cur.execute('SELECT `id`, `display_name`, `image_url`, `price`, `prebot_url` FROM `products` WHERE `name` LIKE %s AND `enabled` = 1 ORDER BY `id` LIMIT 1;', ("%{query_term}%".format(query_term=query_term),))
                row = cur.fetchone()
                if row is not None:
                    product = row

    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return product


def handle_postback(user_id, payload):
    logger.info("handle_postback(user_id=%s, payload=%s)" % (user_id, payload))

    if payload == "SHARE_APP":
        share_app(
            user_id=user_id
        )

    elif payload == "FLIP_RND_STOREFRONT":
        flip_product(
            user_id=user_id
        )

    elif re.search(r'^VIEW_CAROUSEL_PRODUCT\-(\d)$', payload) is not None:
        view_product(
            user_id=user_id,
            product_id=product_search(storefront_templates()[int(re.match(r'^VIEW_CAROUSEL_PRODUCT\-(?P<index>\d)$', payload).group('index'))]['query_term'])['id']
        )

    elif re.search(r'^VIEW_PRODUCT\-(\d+)$', payload) is not None:
        view_product(
            user_id=user_id,
            product_id=int(re.match(r'^VIEW_PRODUCT\-(?P<product_id>\d+)$', payload).group('product_id'))
        )

    elif re.search(r'^PURCHASE_PRODUCT\-(\d+)$', payload) is not None:
        purchase_product(
            user_id=user_id,
            product_id=int(re.match(r'^PURCHASE_PRODUCT\-(?P<product_id>\d+)$', payload).group('product_id')),
        )

    elif re.search(r'^PURCHASE_PRODUCT_YES\-(\d+)$', payload) is not None:
        customer_trade_url(

        )

    elif re.search(r'^PURCHASE_PRODUCT_NO\-(\d+)$', payload) is not None:
        main_carousel(
            user_id=user_id
        )

    elif re.search(r'^RESELL_CAROUSEL_PRODUCT\-(\d+)$', payload) is not None:
        resell_product(
            user_id=user_id,
            product_id=product_search(storefront_templates()[int(re.match(r'^RESELL_CAROUSEL_PRODUCT\-(?P<index>\d)$', payload).group('index'))]['query_term'])['id'],
        )

    elif re.search(r'^RESELL_PRODUCT\-(\d+)$', payload) is not None:
        resell_product(
            user_id=user_id,
            product_id=int(re.match(r'^RESELL_PRODUCT\-(?P<product_id>\d+)$', payload).group('product_id')),
        )

    elif payload == "MYSTERY_FLIP":
        product_card(
            user_id=user_id,
            title="Gamebots Mystery Flip",
            description="1 Flip High Tier Item",
            image_url="https://i.imgur.com/SngEQtI.jpg",
            buttons=[
                PostbackTemplateAction(label="Resell ({points} Pts)".format(points=locale.format('%d', Const.POINT_AMOUNT_RESELL_STOREFRONT, grouping=True)), data="RESELL_MYSTERY_FLIP"),
                PostbackTemplateAction(label="{points} Points".format(points=locale.format('%d', int(4.99 * 250000), grouping=True)), data="PURCHASE_MYSTERY_FLIP"),
                PostbackTemplateAction(label="Share", data="SHARE_STOREFRONT")
            ]
        )


def flip_product(user_id):
    logger.info("flip_product(user_id=%s)" % (user_id,))

    outcome = random.uniform(0, 1) < (1 / float(5))
    conn = mysql.connect(host=Const.MYSQL_HOST, user=Const.MYSQL_USER, passwd=Const.MYSQL_PASS, db=Const.MYSQL_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('SELECT `id`, `storefront_id` FROM `products` WHERE `tags` LIKE %s AND `enabled` = 1 ORDER BY RAND() LIMIT 1;', ("%{tag}%".format(tag="autogen-import"),))
            row = cur.fetchone()
            if row is not None:
                if outcome is True:
                    code = hashlib.md5(str(time.time()).encode()).hexdigest()[-4:].upper()
                    # cur.execute('INSERT INTO `flip_wins` (`id`, `user_id`, `storefront_id`, `product_id`, `added`) VALUES (NULL, %s, %s, %s, UTC_TIMESTAMP());', (customer.id, row['storefront_id'], row['id']))

                view_product(
                    user_id=user_id,
                    product_id=row['id'])

            else:
                text_message(
                    user_id=user_id,
                    message="No shops are available to flip right now, try again later."
                )

    except mysql.Error, e:
        logger.info("MySqlError (%d): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()



def view_product(user_id, product_id):
    logger.info("view_product(user_id=%s, product_id=%s)" % (user_id, product_id))

    product = product_lookup(product_id)
    product_card(
        user_id=user_id,
        title=product['display_name'],
        description=locale.format('%d', int(product['price'] * 250000), grouping=True),
        image_url="https://i.imgur.com/qrwkaGq.jpg",#product['image_url'],
        buttons=[
            PostbackTemplateAction(label="Resell ({points} Pts)".format(points=locale.format('%d', Const.POINT_AMOUNT_RESELL_STOREFRONT, grouping=True)), data="RESELL_PRODUCT-{product_id}".format(product_id=product_id)),
            PostbackTemplateAction(label="{points} Points".format(points=locale.format('%d', int(product['price'] * 250000), grouping=True)), data="PURCHASE_PRODUCT-{product_id}".format(product_id=product_id)),
            PostbackTemplateAction(label="Share", data="SHARE_APP")
        ]
    )


def purchase_product(user_id, product_id):
    logger.info("purchase_product(user_id=%s, product_id=%s)" % (user_id, product_id))

    product = product_lookup(product_id)

    line_bot_api.push_message(
        to=user_id,
        messages=TemplateSendMessage(
            alt_text="Purchase {product_name}?".format(product_name=product['display_name']),
            template=ConfirmTemplate(text="Are you sure you want to use {points} for {product_name}?".format(points=locale.format('%d', int(product['price'] * 250000), grouping=True), product_name=product['display_name']),
            actions=[
                PostbackTemplateAction(label="Confirm", data='PURCHASE_PRODUCT_YES'),
                PostbackTemplateAction(label="Cancel", data='PURCHASE_PRODUCT_NO')
            ])
        )
    )


def resell_product(user_id, product_id):
    logger.info("resell_product(user_id=%s, product_id=%s)" % (user_id, product_id))

    product = product_lookup(product_id)

    text_message(
        user_id=user_id,
        message="Welcome to the Lmon8 Reseller Program. Every time an item is sold you will get {points} Pts. Keep Flipping!".format(points=locale.format('%d', Const.POINT_AMOUNT_RESELL_STOREFRONT, grouping=True))
    )

    text_message(
        user_id=user_id,
        message="{product_name} created.\n{prebot_url}".format(product_name=product['display_name'], prebot_url=product['prebot_url'])
    )

    text_message(
        user_id=user_id,
        message="Share {product_name} with your Friends on Messenger".format(product_name=product['display_name'])
    )

    main_carousel(
        user_id=user_id
    )


def customer_trade_url(user_id):
    logger.info("customer_trade_url(user_id=%s)" % (user_id,))

    text_message(
        user_id=user_id,
        message="Purchase complete.\nPlease enter your Steam Trade URL."
    )

    text_message(
        user_id=user_id,
        message="Your purchase has been made. The item and points are being approved and will transfer shortly.\n\nPurchase ID: {purchase_id}".format(purchase_id=random.randint(1000, 9999))
    )


def share_app(user_id):
    logger.info("share_app(user_id=%s)" % (user_id,))

    text_message(
        user_id=user_id,
        message="To share your Lemonade on Line shop send the following QR code to 20 friends!"
    )

    image_message(
        image_url="https://i.imgur.com/9svbARK.jpg",
        user_id=user_id
    )

    main_carousel(
        user_id=user_id
    )


def main_carousel(user_id):
    logger.info("main_carousel(user_id=%s)" % (user_id,))

    profile = line_bot_api.get_profile(user_id)


    columns = [
        CarouselColumn(
            text="Win Lmon8 Points Now",
            title="Flip Shops to Win",
            thumbnail_image_url="https://i.imgur.com/Ao3eCpX.jpg",
            actions=[
                PostbackTemplateAction(label="Flip Now ({points} Pts)".format(points=locale.format('%d', Const.POINT_AMOUNT_FLIP_STOREFRONT_WIN, grouping=True)), data="FLIP_RND_STOREFRONT"),
                PostbackTemplateAction(label="Share ({points} Pts)".format(points=Const.POINT_AMOUNT_REFFERAL), data="SHARE_APP")
            ]
        ),
        CarouselColumn(
            text="Earn {points} Pts Per Invite".format(points=locale.format('%d', Const.POINT_AMOUNT_REFFERAL, grouping=True)),
            title="Refer a Friend",
            thumbnail_image_url="https://i.imgur.com/xtRQaAx.jpg",
            actions=[
                PostbackTemplateAction(label="My ID", data="REFERRAL_FAQ"),
                PostbackTemplateAction(label="Share ({points} Pts)".format(points=Const.POINT_AMOUNT_REFFERAL), data="SHARE_REFERRAL")
            ]
        ),
        CarouselColumn(
            text="1 Flip High Tier Item",
            title="Gamebots Mystery Flip",
            thumbnail_image_url="https://i.imgur.com/SngEQtI.jpg",
            actions=[
                PostbackTemplateAction(label="Resell ({points} Pts)".format(points=Const.POINT_AMOUNT_RESELL_STOREFRONT), data="RESELL_PRODUCT-5"),
                PostbackTemplateAction(label="View Shop", data="VIEW_PRODUCT-5")
            ]
        )
    ]
    storefronts = storefront_templates()
    random.shuffle(storefronts)
    for storefront in storefronts:
        if len(columns) < 5:
            columns.append(
                CarouselColumn(
                    text=storefront['description'],
                    title=storefront['title'],
                    thumbnail_image_url=storefront['image_url'],
                    actions=[
                        PostbackTemplateAction(label="Resell ({points} Pts)".format(points=Const.POINT_AMOUNT_RESELL_STOREFRONT), data="RESELL_CAROUSEL_PRODUCT-{index}".format(index=storefront['index'])),
                        PostbackTemplateAction(label="View Shop", data="VIEW_CAROUSEL_PRODUCT-{index}".format(index=storefront['index']))
                    ]
                )
            )


    try:
        line_bot_api.push_message(
            to=user_id,
            messages=TemplateSendMessage(
                alt_text="Lmon8 shops",
                template=CarouselTemplate(
                    columns=columns
                )
            )
        )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


def storefront_carousel(user_id):
    logger.info("storefront_carousel(user_id=%s)" % (user_id,))

    storefronts = storefront_templates()
    random.shuffle(storefronts)

    columns = []
    for storefront in storefronts:
        if len(columns) < 5:
            columns.append(
                CarouselColumn(
                    text=storefront['description'],
                    title=storefront['title'],
                    thumbnail_image_url=storefront['image_url'],
                    actions=[
                        # URITemplateAction(label="Go to line.me", uri="https://line.me"),
                        PostbackTemplateAction(label="Create", data="CREATE_STOREFRONT-{index}".format(index=storefront['index'])),
                        PostbackTemplateAction(label="Share Now", data="SHARE_STOREFRONT-{index}".format(index=storefront['index']))
                    ]
                )
            )

    try:
        line_bot_api.push_message(
            to=user_id,
            messages=TemplateSendMessage(
                alt_text="Disney shops",
                template=CarouselTemplate(
                    columns=columns
                )
            )
        )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


def product_card(user_id, title, description, image_url, buttons):
    logger.info("product_card(user_id=%s, title=%s, description=%s, image_url=%s, buttons=%s)" % (user_id, title, description, image_url, buttons))
    try:
        line_bot_api.push_message(
            to=user_id,
            messages=TemplateSendMessage(
                alt_text=title,
                template=ButtonsTemplate(
                    text=description,
                    title=title,
                    thumbnail_image_url=image_url,
                    actions=buttons
                )
            )
        )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


def text_message(user_id, message):
    logger.info("text_message(user_id=%s, message=%s)" % (user_id, message))

    try:
        line_bot_api.push_message(
            to=user_id,
            messages=TextSendMessage(text=message)
        )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


def sticker_message(user_id, package_id, sticker_id):
    logger.info("sticker_message(user_id=%s, package_id=%s, sticker_id=%s)" % (user_id, package_id, sticker_id))

    try:
        line_bot_api.push_message(
            to=user_id,
            messages=StickerSendMessage(
                package_id=package_id,
                sticker_id=sticker_id
            )
        )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


def image_message(user_id, image_url):
    logger.info("image_message(user_id=%s, image_url=%s)" % (user_id, image_url))

    try:
        line_bot_api.push_message(
            to=user_id,
            messages=ImageSendMessage(
                original_content_url=image_url,
                preview_image_url=image_url
            )
        )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


def video_message(user_id, thumb_url, video_url):
    logger.info("video_message(user_id=%s, thumb_url=%s, video_url=%s)" % (user_id, thumb_url, video_url))

    try:
        line_bot_api.push_message(
            to=user_id,
            messages=VideoSendMessage(
                original_content_url=video_url,
                preview_image_url=thumb_url
            )
        )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


if __name__ == "__main__":
    app.run()
