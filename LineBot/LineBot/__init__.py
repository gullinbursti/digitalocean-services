import base64
import hmac
import hashlib
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
    return 'Hello'


@app.route('/', methods=['POST'])
def default():
    events = request.json

    #logger.info("request.json=%s" % (events,))

    channel_signature = request.headers['X-Line-Signature']
    hash = hmac.new("4bf2db692f5e3705b8d1bf6d82e35dc8".encode('utf-8'), request.data, hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode()

    if not hmac.compare_digest(channel_signature, signature):
        logging.error("HMAC no good!")
        return "HMAC verification mismatch", 403

    for event in events['events']:
        logger.info("event=%s" % (event,))

        if event['type'] == "follow":
            text_message(
                reply_token=event['replyToken'],
                message="Welcome to Lemonade on Line sponsored by Disney Tsum Tsum"
            )

            video_message(
                reply_token=event['replyToken'],
                thumb_url="https://i.imgur.com/VPr9NZR.jpg",
                video_url="https://prekey.co/static/stacks.mp4",
                user_id=event['source']['userId']
            )

            threading.Timer(900, mystery_flip, [event['replyToken'], event['source']['userId']]).start()

        elif 'postback' in event:
            handle_postback(
                reply_token=event['replyToken'],
                payload=event['postback']['data'],
                user_id=event['source']['userId']
            )

        else:
            main_carousel(
                reply_token=event['replyToken'],
                user_id=event['source']['userId']
            )


    return "OK", 200


def storefront_templates():
    logger.info("storefront_templates()")

    return [
        {
            'index'      : 0,
            'title'      : "Tsum Tsum Rubies 20x Extra",
            'description': "Get 20 extra for buying now",
            'image_url'  : "https://i.imgur.com/7162dOV.jpg",
            'price'      : 1.99
        }, {
            'index'      : 2,
            'title'      : "Tsum Tsum Rubies 80x",
            'description': "Disney Company (Japan) Ltd.",
            'image_url'  : "https://i.imgur.com/nz9qCZc.jpg",
            'price'      : 9.99
        }, {
            'index'      : 2,
            'title'      : "Moana Sticker Pack",
            'description': "Disney Company (Japan) Ltd.",
            'image_url'  : "https://i.imgur.com/pjxRWSh.png",
            'price'      : 4.99
        }, {
            'index'      : 3,
            'title'      : "Extra Level Disney Crossy Road",
            'description': "Disney Company (Japan) Ltd.",
            'image_url'  : "https://i.imgur.com/oaMjnNH.png",
            'price'      : 4.99
        }, {
            'index'      : 4,
            'title'      : "Unlock Tsum Tsum Ironman",
            'description': "Disney Company (Japan) Ltd.",
            'image_url'  : "https://i.imgur.com/S1CTt2H.png",
            'price'      : 4.99
        }, {
            'index'      : 5,
            'title'      : "Mini: Happy Days Stickers",
            'description': "Disney Company (Japan) Ltd.",
            'image_url'  : "https://i.imgur.com/Zz4rJ8L.png",
            'price'      : 1.99
        }, {
            'index'      : 6,
            'title'      : "Tsum Tsum Stickers (10)",
            'description': "Disney Company (Japan) Ltd.",
            'image_url'  : "https://i.imgur.com/A9rS87L.png",
            'price'      : 1.99
        }
    ]


def mystery_flip(reply_token, user_id=None):
    logger.info("mystery_flip(reply_token=%s, user_id=%s)" % (reply_token, user_id))

    outcome = random.uniform(0, 100) < 50

    video_message(
        reply_token=reply_token,
        thumb_url="https://i.imgur.com/VPr9NZR.jpg",
        video_url="https://prekey.co/static/stacks.mp4",
        user_id=user_id
    )

    sticker_message(
        reply_token=reply_token,
        package_id=2 if outcome is True else 1,
        sticker_id=22 if outcome is True else 6
    )

    mystery_card(
        reply_token=reply_token,
        user_id=user_id
    )


def handle_postback(reply_token, payload, user_id=None):
    logger.info("handle_postback(reply_token=%s, payload=%s, user_id=%s)" % (reply_token, payload, user_id))

    if payload == "SHARE_STOREFRONT":
        share_storefront(
            reply_token=reply_token,
            user_id=user_id
        )

    elif re.search(r'^SHARE_STOREFRONT\-(\d)$', payload) is not None:
        share_storefront(
            reply_token=reply_token,
            index=int(re.match(r'^SHARE_STOREFRONT\-(?P<index>\d)$', payload).group('index')),
            user_id=user_id
        )

    elif re.search(r'^VIEW_STOREFRONT\-(\d)$', payload) is not None:
        view_storefront(
            reply_token=reply_token,
            index=int(re.match(r'^VIEW_STOREFRONT\-(?P<index>\d)$', payload).group('index'))
        )

    elif re.search(r'^CREATE_STOREFRONT\-(\d)$', payload) is not None:
       create_storefront(
           reply_token=reply_token,
           index=int(re.match(r'^CREATE_STOREFRONT\-(?P<index>\d)$', payload).group('index')),
           user_id=user_id
        )

    elif payload == "CREATE_STOREFRONT":
        storefront_carousel(
            reply_token=reply_token,
            user_id=user_id
        )

    elif payload == "FLIP_STOREFRONT":
        flip_storefront(
            reply_token=reply_token,
            user_id=user_id
        )

    elif re.search(r'^PURCHASE_STOREFRONT\-(\d)$', payload) is not None:
        purchase_storefront(
            reply_token=reply_token,
            index=0,
            user_id=user_id
        )

    elif re.search(r'^REDEEM_STOREFRONT\-(\d)$', payload) is not None:
        text_message(
            reply_token=reply_token,
            message="You do not have enough points to redeem this item. Keep flipping to win!"
        )

    elif payload == "STOREFRONT_SALES":
        text_message(
            reply_token=reply_token,
            message="You have no sales yet! Keep trying"
        )

    elif payload == "STOREFRONT_POINTS":
        text_message(
            reply_token=reply_token,
            message="You have 100 points."
        )

    elif payload == "MYSTERY_FLIP":
        mystery_flip(
            reply_token=reply_token,
            user_id=user_id
        )


def create_storefront(reply_token, index, user_id=None):
    logger.info("create_storefront(reply_token=%s, index=%s, user_id=%s)" % (reply_token, index, user_id))

    storefront = storefront_templates()[index]

    text_message(
        reply_token=reply_token,
        message="You have created a {storefront_name} shop! Share the shop now with your friends on Line.".format(storefront_name=storefront['title']),
        user_id=user_id
    )

    view_storefront(
        reply_token=reply_token,
        index=index,
        user_id=user_id
    )


def flip_storefront(reply_token, user_id=None):
    logger.info("view_storefront(reply_token=%s, user_id=%s)" % (reply_token, user_id))

    outcome = random.uniform(0, 100) <= 50

    sticker_message(
        reply_token=reply_token,
        package_id=2 if outcome is True else 1,
        sticker_id=22 if outcome is True else 6
    )

    time.sleep(1.125)

    flip_card(
        reply_token=reply_token,
        outcome=outcome,
        user_id=user_id
    )


def view_storefront(reply_token, index, user_id=None):
    logger.info("view_storefront(reply_token=%s, index=%s, user_id=%s)" % (reply_token, index, user_id))

    storefront = storefront_templates()[index]
    shop_card(
        reply_token=reply_token,
        title="{storefront_name} - {price:.2f}".format(storefront_name=storefront['title'], price=storefront['price']),
        description=storefront['description'],
        image_url=storefront['image_url'],
        buttons=[
            PostbackTemplateAction(label="Buy Now", data="PURCHASE_STOREFRONT-{index}".format(index=index)),
            PostbackTemplateAction(label="Share with Friends", data="SHARE_STOREFRONT-{index}".format(index=index))
        ],
        user_id=user_id
    )


def purchase_storefront(reply_token, index, user_id=None):
    logger.info("purchase_storefront(reply_token=%s, index=%s, user_id=%s)" % (reply_token, index, user_id))

    storefront = storefront_templates()[index]
    text_message(
        reply_token=reply_token,
        message="Authorizing Line Pay payment..."
    )

    time.sleep(2.125)
    text_message(
        reply_token=reply_token,
        message="Payment approved! Please check Tsum Tsum now for your items to transfer.",
        user_id=user_id
    )

    main_carousel(
        reply_token=reply_token,
        user_id=user_id
    )


def share_storefront(reply_token, index=None, user_id=None):
    logger.info("share_storefront(reply_token=%s, index=%s, user_id=%s)" % (reply_token, index, user_id))

    storefront = storefront_templates()[index or random.randint(0, 6)]

    text_message(
        reply_token=reply_token,
        message="To share your Lemonade on Line {storefront_name} shop send the following QR code to 20 friends!".format(storefront_name=storefront['title'])
    )
    image_message(
        reply_token=reply_token,
        image_url="https://i.imgur.com/9svbARK.jpg",
        user_id=user_id
    )

    main_carousel(
        reply_token=reply_token,
        user_id=user_id
    )


def main_carousel(reply_token, user_id=None):
    logger.info("main_carousel(reply_token=%s, user_id=%s)" % (reply_token, user_id))

    profile = line_bot_api.get_profile(user_id)
    columns = [
        CarouselColumn(
            text="Play Now to Win",
            title="Flip to Win Disney Points!",
            thumbnail_image_url="https://i.imgur.com/T8Y7G9S.jpg",
            actions=[
                # URITemplateAction(label="Go to line.me", uri="https://line.me"),
                PostbackTemplateAction(label="Play Now", data="FLIP_STOREFRONT"),
                PostbackTemplateAction(label="Share Now", data="SHARE_STOREFRONT")
            ]
        ),
        CarouselColumn(
            text="Create a Shop for 1,000 pts",
            title="{display_name} - 100pts".format(display_name=profile.display_name),
            thumbnail_image_url="https://i.imgur.com/Qu829we.jpg",
            actions=[
                PostbackTemplateAction(label="Create Shop", data="CREATE_STOREFRONT"),
                PostbackTemplateAction(label="My Points", data="STOREFRONT_POINTS"),
            ]
        )
    ]

    try:
        if user_id is None:
            line_bot_api.reply_message(
                reply_token=reply_token,
                messages=TemplateSendMessage(
                    alt_text="Lmon8 shops",
                    template=CarouselTemplate(
                        columns=columns
                    )
                )
            )

        else:
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


def storefront_carousel(reply_token, user_id=None):
    logger.info("storefront_carousel(reply_token=%s, user_id=%s)" % (reply_token, user_id))

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
        if user_id is None:
            line_bot_api.reply_message(
                reply_token=reply_token,
                messages=TemplateSendMessage(
                    alt_text="Disney shops",
                    template=CarouselTemplate(
                        columns=columns
                    )
                )
            )

        else:
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


def flip_card(reply_token, outcome, user_id=None):
    logger.info("flip_card(reply_token=%s, outcome=%s, user_id=%s)" % (reply_token, outcome, user_id))

    index = random.randint(0, 6)
    storefront = storefront_templates()[index]

    try:
        if user_id is None:
            line_bot_api.reply_message(
                reply_token=reply_token,
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

        else:
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


def mystery_card(reply_token, user_id=None):
    logger.info("mystery_card(reply_token=%s, user_id=%s)" % (reply_token, user_id))

    try:
        if user_id is None:
            line_bot_api.reply_message(
                reply_token=reply_token,
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

        else:
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


def shop_card(reply_token, title, description, image_url, buttons, user_id=None):
    logger.info("shop_card(reply_token=%s, title=%s, description=%s, image_url=%s, buttons=%s, user_id=%s)" % (reply_token, title, description, image_url, buttons, user_id))
    try:
        if user_id is None:
            line_bot_api.reply_message(
                reply_token=reply_token,
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

        else:
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




def text_message(reply_token, message, user_id=None):
    logger.info("text_message(reply_token=%s, message=%s, user_id=%s)" % (reply_token, message, user_id))

    try:
        if user_id is None:
            line_bot_api.reply_message(
                reply_token=reply_token,
                messages=TextSendMessage(text=message)
            )

        else:
            line_bot_api.push_message(
                to=user_id,
                messages=TextSendMessage(text=message)
            )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


def sticker_message(reply_token, package_id, sticker_id, user_id=None):
    logger.info("sticker_message(reply_token=%s, package_id=%s, sticker_id=%s, user_id=%s)" % (reply_token, package_id, sticker_id, user_id))

    try:
        if user_id is None:
            line_bot_api.reply_message(
                reply_token=reply_token,
                messages=StickerSendMessage(
                    package_id=package_id,
                    sticker_id=sticker_id
                )
            )

        else:
            line_bot_api.push_message(
                to=user_id,
                messages=StickerSendMessage(
                    package_id=package_id,
                    sticker_id=sticker_id
                )
            )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


def image_message(reply_token, image_url, user_id=None):
    logger.info("image_message(reply_token=%s, image_url=%s, user_id=%s)" % (reply_token, image_url, user_id))

    try:
        if user_id is None:
            line_bot_api.reply_message(
                reply_token=reply_token,
                messages=ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            )

        else:
            line_bot_api.push_message(
                to=user_id,
                messages=ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                )
            )

    except LineBotApiError as e:
        logger.info("LineBotApiError:%s" % (e,))


def video_message(reply_token, thumb_url, video_url, user_id=None):
    logger.info("video_message(reply_token=%s, thumb_url=%s, video_url=%s, user_id=%s)" % (reply_token, thumb_url, video_url, user_id))

    try:
        if user_id is None:
            line_bot_api.reply_message(
                reply_token=reply_token,
                messages=VideoSendMessage(
                    original_content_url=video_url,
                    preview_image_url=thumb_url
                )
            )

        else:
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
