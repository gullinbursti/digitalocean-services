import base64
import json
import logging
import os
import hmac
import hashlib
import time

from datetime import datetime

import requests

from flask import Flask, request
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage, SourceUser, SourceGroup, SourceRoom, TemplateSendMessage, ConfirmTemplate, MessageTemplateAction, ButtonsTemplate, URITemplateAction, PostbackTemplateAction, CarouselTemplate, CarouselColumn, PostbackEvent, StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage, ImageMessage, VideoMessage, AudioMessage, UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent
from linebot.exceptions import LineBotApiError


app = Flask(__name__)
app.secret_key = os.urandom(24)

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler("/var/log/LineBot.log")
formatter = logging.Formatter('%(asctime)s - %(message)s', '%d-%b-%Y %H:%M:%S')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

line_bot_api = LineBotApi('nfQJjb0MP5+AHAuc79f5W5unuiqf0eTsrsZmkg8eK7j3mQHauQfWVg38LnYhw/3FaPHWR3wh9qodQqi0dQUDqkdWC40JmVrpDdtk5iZg5+KGkGDV5+gu7HFq5ufYYzRORPyzKoNZ9qRPWQL1aeUycAdB04t89/1O/w1cDnyilFU=')


@app.route('/')
def hello():
    return 'Hello'


channel_id = 'nfQJjb0MP5+AHAuc79f5W5unuiqf0eTsrsZmkg8eK7j3mQHauQfWVg38LnYhw/3FaPHWR3wh9qodQqi0dQUDqkdWC40JmVrpDdtk5iZg5+KGkGDV5+gu7HFq5ufYYzRORPyzKoNZ9qRPWQL1aeUycAdB04t89/1O/w1cDnyilFU='
channel_secret = '4bf2db692f5e3705b8d1bf6d82e35dc8'
mid = '1511403276'

CHANNEL = '1511403276'
EVENT_TYPE = '138311608800106203'


@app.route('/', methods=['POST'])
def default():
    events = request.json

    #logger.info("request.json=%s" % (events,))

    channel_signature = request.headers['X-Line-Signature']
    hash = hmac.new(channel_secret.encode('utf-8'), request.data, hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode()

    if not hmac.compare_digest(channel_signature, signature):
        logging.error("HMAC no good!")
        return "HMAC verification mismatch", 403

    for event in events['events']:
        logger.info("event=%s" % (event,))

        try:
            #line_bot_api.reply_message(event['replyToken'], TextSendMessage(text="Server time is: %s" % (datetime.now().strftime('%H:%M:%S'),)))
            #line_bot_api.reply_message(event['replyToken'], ImageSendMessage(original_content_url="http://i.imgur.com/RZQiEtb.png", preview_image_url="http://i.imgur.com/RZQiEtbb.jpg"))
            # line_bot_api.reply_message(
            #     reply_token=event['replyToken'],
            #     messages=TemplateSendMessage(
            #         alt_text='Confirm alt text',
            #         template=ConfirmTemplate(
            #             text='Do it?',
            #             actions=[
            #                 MessageTemplateAction(
            #                     label='Yes',
            #                     text='Yes!'
            #                 ),
            #                 MessageTemplateAction(
            #                     label='No',
            #                     text='No!'
            #                 ),
            #             ]
            #         )
            #     )
            # )

            line_bot_api.reply_message(
                reply_token=event['replyToken'],
                messages=TemplateSendMessage(
                    alt_text='Buttons alt text',
                    template=CarouselTemplate(
                        columns=[
                            CarouselColumn(
                                text='Description I',
                                title='Shop I',
                                # thumbnail_image_url="http://i.imgur.com/RZQiEtb.png",
                                actions=[
                                    # URITemplateAction(label='Go to line.me', uri='https://line.me'),
                                    PostbackTemplateAction(label='Share', data='SHARE_STOREFRONT'),
                                    PostbackTemplateAction(label='View', data='VIEW_STOREFRONT'),
                                    PostbackTemplateAction(label='Create', data='CREATE_STOREFRONT'),
                                ]
                            ),
                            CarouselColumn(
                                text='Description II',
                                title='Shop II',
                                # thumbnail_image_url="http://i.imgur.com/RZQiEtb.png",
                                actions=[
                                    # URITemplateAction(label='Go to line.me', uri='https://line.me'),
                                    PostbackTemplateAction(label='Share', data='SHARE_STOREFRONT'),
                                    PostbackTemplateAction(label='View', data='VIEW_STOREFRONT'),
                                    PostbackTemplateAction(label='Create', data='CREATE_STOREFRONT'),
                                ]
                            ),
                            CarouselColumn(
                                text='Description III',
                                title='Shop III',
                                # thumbnail_image_url="http://i.imgur.com/RZQiEtb.png",
                                actions=[
                                    # URITemplateAction(label='Go to line.me', uri='https://line.me'),
                                    PostbackTemplateAction(label='Share', data='SHARE_STOREFRONT'),
                                    PostbackTemplateAction(label='View', data='VIEW_STOREFRONT'),
                                    PostbackTemplateAction(label='Create', data='CREATE_STOREFRONT'),
                                ]
                            ),
                            CarouselColumn(
                                text='Description IV',
                                title='Shop IV',
                                # thumbnail_image_url="http://i.imgur.com/RZQiEtb.png",
                                actions=[
                                    # URITemplateAction(label='Go to line.me', uri='https://line.me'),
                                    PostbackTemplateAction(label='Share', data='SHARE_STOREFRONT'),
                                    PostbackTemplateAction(label='View', data='VIEW_STOREFRONT'),
                                    PostbackTemplateAction(label='Create', data='CREATE_STOREFRONT'),
                                ]
                            ),
                        ]
                    )
                )
             )


        except LineBotApiError as e:
            logger.info("LineBotApiError:%s" % (e,))

        headers = {
            'Authorization'               : "Bearer {access_token}".format(access_token=channel_id),
            'Content-Type'                : 'application/json; charset=UTF-8',
            'X-Line-ChannelID'            : channel_id,
            'X-Line-ChannelSecret'        : channel_secret,
            'X-Line-Trusted-User-With-ACL': mid
        }


        payload = {

            'replyToken' : event['replyToken'],
            'messages': [{
            "type"    : "template",
            "altText" : "this is a buttons template",
            "template": {
                "type"             : "buttons",
                "thumbnailImageUrl": "http://i.imgur.com/RZQiEtb.png",
                "title"            : "Menu",
                "text"             : "Please select",
                "actions"          : [
                    {
                        "type" : "postback",
                        "label": "Buy",
                        "data" : "action=buy&itemid=123"
                    },
                    {
                        "type" : "postback",
                        "label": "Add to cart",
                        "data" : "action=add&itemid=123"
                    }
                ]
            }}]
        }

        # payload = {
        #     'messages': int(time.time()),
        #     'replyToken': event['replyToken'],
        #     "type"    : "template",
        #     "altText" : "this is a carousel template",
        #     "template": {
        #         "type"   : "carousel",
        #         "columns": [
        #             {
        #                 "thumbnailImageUrl": "http://i.imgur.com/RZQiEtb.png",
        #                 "title"            : "this is menu",
        #                 "text"             : "description",
        #                 "actions"          : [
        #                     {
        #                         "type" : "postback",
        #                         "label": "Buy",
        #                         "data" : "action=buy&itemid=111"
        #                     },
        #                     {
        #                         "type" : "postback",
        #                         "label": "Add to cart",
        #                         "data" : "action=add&itemid=111"
        #                     },
        #                     {
        #                         "type" : "uri",
        #                         "label": "View detail",
        #                         "uri"  : "http://example.com/page/111"
        #                     }
        #                 ]
        #             },
        #             {
        #                 "thumbnailImageUrl": "http://i.imgur.com/RZQiEtb.png",
        #                 "title"            : "this is menu",
        #                 "text"             : "description",
        #                 "actions"          : [
        #                     {
        #                         "type" : "postback",
        #                         "label": "Buy",
        #                         "data" : "action=buy&itemid=222"
        #                     },
        #                     {
        #                         "type" : "postback",
        #                         "label": "Add to cart",
        #                         "data" : "action=add&itemid=222"
        #                     },
        #                     {
        #                         "type" : "uri",
        #                         "label": "View detail",
        #                         "uri"  : "http://example.com/page/222"
        #                     }
        #                 ]
        #             }
        #         ]
        #     }
        # }

        #response = requests.post("https://api.line.me/v2/bot/message/reply", data=json.dumps(payload), headers=headers)
        #logger.info("RESPONSE:%s" % (response.json(),))


    #
    # #proxies = {'https': os.environ['FIXIE_URL']}
    #
    # for event in events:
    #     payload = {
    #         'to'       : [result['content']['from']],
    #         'toChannel': CHANNEL,
    #         'eventType': EVENT_TYPE,
    #         'content'  : result['content']
    #     }
    #
    #     r = requests.post("https://api.line.me/v2/bot/message/reply", data=json.dumps(payload), headers=headers)
    #     logging.debug(r.status_code)
    #     logging.debug(r.text)
    #     r.raise_for_status()

    return "OK", 200


if __name__ == '__main__':
    app.run()
