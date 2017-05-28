import base64
import hmac
import hashlib
import locale
import logging
import os
import random
import re
import threading
import time
import urllib

from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import LineBotApiError
from linebot.models import MessageEvent, TextMessage, ImageSendMessage, StickerSendMessage, TextSendMessage, VideoSendMessage, SourceUser, SourceGroup, SourceRoom, TemplateSendMessage, ConfirmTemplate, MessageTemplateAction, ButtonsTemplate, URITemplateAction, PostbackTemplateAction, CarouselTemplate, CarouselColumn, PostbackEvent, StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage, ImageMessage, VideoMessage, AudioMessage, UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent

from constants import Const

app = Flask(__name__)
app.secret_key = os.urandom(24)

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
            'index'      : 1,
            'title'      : "M4A4 | Desolate Space",
            'description': "CSGO Item",
            'image_url'  : "https://i.imgur.com/qrwkaGq.jpg",
            'price'      : 9.99
        }, {
            'index'      : 2,
            'title'      : "Sxyhxy's Body Armor",
            'description': "H1Z1 Item",
            'image_url'  : "https://i.imgur.com/TZRtwsg.jpg",
            'price'      : 4.99
        }, {
            'index'      : 3,
            'title'      : "MAC-10 | Neon Rider",
            'description': "CSGO Item",
            'image_url'  : "https://i.imgur.com/u12Z6G2.jpg",
            'price'      : 4.99
        }, {
            'index'      : 4,
            'title'      : "P2000 Imperial Dragon",
            'description': "CSGO Item",
            'image_url'  : "https://i.imgur.com/D8fJbrN.jpg",
            'price'      : 4.99
        }, {
            'index'      : 5,
            'title'      : "Claws of the Blood Moon",
            'description': "Dota 2 Item",
            'image_url'  : "https://i.imgur.com/KAkicdD.jpg",
            'price'      : 1.99
        }, {
            'index'      : 6,
            'title'      : "M4A1-S | Hyper Beast",
            'description': "CSGO Item",
            'image_url'  : "https://i.imgur.com/QFLtVjU.jpg",
            'price'      : 1.99
        }
    ]


def handle_postback(user_id, payload):
    logger.info("handle_postback(user_id=%s, payload=%s)" % (payload, user_id))

    if payload == "SHARE_STOREFRONT":
        share_storefront(
            user_id=user_id
        )

    elif re.search(r'^SHARE_STOREFRONT\-(\d)$', payload) is not None:
        share_storefront(
            user_id=user_id,
            index=int(re.match(r'^SHARE_STOREFRONT\-(?P<index>\d)$', payload).group('index'))
        )

    elif re.search(r'^VIEW_STOREFRONT\-(\d)$', payload) is not None:
        view_storefront(
            user_id=user_id,
            index=int(re.match(r'^VIEW_STOREFRONT\-(?P<index>\d)$', payload).group('index'))
        )

    elif re.search(r'^CREATE_STOREFRONT\-(\d)$', payload) is not None:
        create_storefront(
            user_id=user_id,
            index=int(re.match(r'^CREATE_STOREFRONT\-(?P<index>\d)$', payload).group('index'))
        )

    elif payload == "CREATE_STOREFRONT":
        storefront_carousel(
            user_id=user_id
        )

    elif payload == "FLIP_STOREFRONT":
        flip_storefront(
            user_id=user_id
        )

    elif re.search(r'^PURCHASE_STOREFRONT\-(\d)$', payload) is not None:
        purchase_storefront(
            user_id=user_id,
            index=0,
        )

    elif re.search(r'^REDEEM_STOREFRONT\-(\d)$', payload) is not None:
        text_message(
            user_id=user_id,
            message="You do not have enough points to redeem this item. Keep flipping to win!"
        )

    elif payload == "STOREFRONT_SALES":
        text_message(
            user_id=user_id,
            message="You have no sales yet! Keep trying"
        )

    elif payload == "STOREFRONT_POINTS":
        text_message(
            user_id=user_id,
            message="You have 100 points."
        )

    elif payload == "MYSTERY_FLIP":
        pass


def create_storefront(user_id, index):
    logger.info("create_storefront(user_id=%s, index=%s)" % (user_id, index))

    storefront = storefront_templates()[index]

    text_message(
        user_id=user_id,
        message="You have created a {storefront_name} shop! Share the shop now with your friends on Line.".format(storefront_name=storefront['title'])
    )

    view_storefront(
        user_id=user_id,
        index=index
    )


def flip_storefront(user_id):
    logger.info("view_storefront(user_id=%s)" % (user_id,))

    outcome = random.uniform(0, 100) <= 50

    sticker_message(
        user_id=user_id,
        package_id=2 if outcome is True else 1,
        sticker_id=22 if outcome is True else 6
    )

    time.sleep(1.125)

    flip_card(
        user_id=user_id,
        outcome=outcome
    )


def view_storefront(user_id, index):
    logger.info("view_storefront(user_id=%s, index=%s)" % (user_id, index))

    storefront = storefront_templates()[index]
    shop_card(
        user_id=user_id,
        title="{storefront_name} - {price:.2f}".format(storefront_name=storefront['title'], price=storefront['price']),
        description=storefront['description'],
        image_url=storefront['image_url'],
        buttons=[
            PostbackTemplateAction(label="Buy Now", data="PURCHASE_STOREFRONT-{index}".format(index=index)),
            PostbackTemplateAction(label="Share with Friends", data="SHARE_STOREFRONT-{index}".format(index=index))
        ]
    )


def purchase_storefront(user_id, index):
    logger.info("purchase_storefront(user_id=%s, index=%s)" % (user_id, index))

    storefront = storefront_templates()[index]
    text_message(
        user_id=user_id,
        message="Authorizing Line Pay payment..."
    )

    time.sleep(2.125)
    text_message(
        user_id=user_id,
        message="Payment approved! Please check Tsum Tsum now for your items to transfer."
    )

    main_carousel(
        user_id=user_id
    )


def share_storefront(user_id, index=None):
    logger.info("share_storefront(user_id=%s, index=%s)" % (user_id, index))

    storefront = storefront_templates()[index or random.randint(0, 6)]

    text_message(
        message="To share your Lemonade on Line {storefront_name} shop send the following QR code to 20 friends!".format(storefront_name=storefront['title'])
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
                PostbackTemplateAction(label="Flip Now ({points} Pts)".format(points=Const.POINT_AMOUNT_FLIP_STOREFRONT_WIN), data="FLIP_RND_STOREFRONT"),
                PostbackTemplateAction(label="Flip Now ({points} Pts)".format(points=Const.POINT_AMOUNT_FLIP_STOREFRONT_WIN), data="FLIP_RND_STOREFRONT")
            ]
        ),
        CarouselColumn(
            text="Earn {points} Pts Per Invite".format(points=locale.format('%d', Const.POINT_AMOUNT_REFFERAL, grouping=True)),
            title="Refer a Friend",
            thumbnail_image_url="https://i.imgur.com/xtRQaAx.jpg",
            actions=[
                PostbackTemplateAction(label="My ID", data="REFERRAL_FAQ"),
                PostbackTemplateAction(label="Share ({points} Pts)".format(points=Const.POINT_AMOUNT_REFFERAL), data="SHARE_APP")
            ]
        ),
        CarouselColumn(
            text="1 Flip High Tier Item",
            title="Gamebots Mystery Flip",
            thumbnail_image_url="https://i.imgur.com/SngEQtI.jpg",
            actions=[
                PostbackTemplateAction(label="Resell ({points} Pts)".format(points=Const.POINT_AMOUNT_RESELL_STOREFRONT), data="RESELL_STOREFRONT-0"),
                PostbackTemplateAction(label="View Shop", data="VIEW_STOREFRONT-0")
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
                        PostbackTemplateAction(label="Resell ({points} Pts)".format(points=Const.POINT_AMOUNT_RESELL_STOREFRONT), data="RESELL_STOREFRONT-{index}".format(index=storefront['index'])),
                        PostbackTemplateAction(label="View Shop", data="VIEW_STOREFRONT-{index}".format(index=storefront['index']))
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


def flip_card(user_id, outcome):
    logger.info("flip_card(user_id=%s, outcome=%s)" % (user_id, outcome))

    index = random.randint(0, 6)
    storefront = storefront_templates()[index]

    try:
        line_bot_api.push_message(
            to=user_id,
            messages=TemplateSendMessage(
                alt_text="Flip",
                template=ButtonsTemplate(
                    text=storefront['description'],
                    title="{storefront_name} - {price:.2f}".format(storefront_name=storefront['title'], price=storefront['price']),
                    thumbnail_image_url=storefront['image_url'],
                    actions=[
                        PostbackTemplateAction(label="Buy Now", data="PURCHASE_STOREFRONT-{index}".format(index=index)),
                        PostbackTemplateAction(label="Play Again", data="FLIP_STOREFRONT")
                    ]
                )
            )
        )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


def mystery_card(user_id):
    logger.info("mystery_card(user_id=%s)" % (user_id,))

    try:
        line_bot_api.push_message(
            to=user_id,
            messages=TemplateSendMessage(
                alt_text="Mystery Flip",
                template=ButtonsTemplate(
                    text="Flip for mystery item",
                    title="Mystery Flip",
                    thumbnail_image_url="https://i.imgur.com/X0KIBYl.jpg",
                    actions=[
                        PostbackTemplateAction(label="Mystery Flip", data="MYSTERY_FLIP"),
                    ]
                )
            )
        )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


def shop_card(user_id, title, description, image_url, buttons):
    logger.info("shop_card(user_id=%s, title=%s, description=%s, image_url=%s, buttons=%s)" % (user_id, title, description, image_url, buttons))
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
