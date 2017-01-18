#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import cStringIO
import hashlib
import json
import locale
import logging
import os
import random
import re
import time

from datetime import datetime

import av
import flask
import grequests
import MySQLdb as mysql
import pycurl
import requests

from dateutil.relativedelta import relativedelta
from flask import escape, request

from models import logger
from data import Consts
from data import Customer, Product, Storefront, Subscription

api = flask.Blueprint('api', __name__, template_folder='templates')



#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#



#=- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#






def async_send_evt_tracker(urls):
    logger.info("send_evt_tracker(len(urls)=%d)" % (len(urls)))

    responses = (grequests.get(u) for u in urls)
    grequests.map(responses)



def send_tracker(category, action, label):
    logger.info("send_tracker(category={category}, action={action}, label={label})".format(category=category, action=action, label=label))

    client_id = hashlib.md5(label.encode()).hexdigest()
    src_app = "facebook"
    username = ""
    chat_id = category
    value = ""

    urls = [
        "http://beta.modd.live/api/user_tracking.php?username={username}&chat_id={chat_id}".format(username=label, chat_id=action),
        "http://beta.modd.live/api/bot_tracker.php?src=facebook&category={category}&action={action}&label={label}&value={value}&cid={cid}".format(category=category, action=category, label=action, value=value, cid=hashlib.md5(label.encode()).hexdigest()),
        "http://beta.modd.live/api/bot_tracker.php?src=facebook&category=user-message&action=user-message&label={label}&value={value}&cid={cid}".format(label=action, value=value, cid=hashlib.md5(label.encode()).hexdigest())
    ]

    responses = (grequests.get(u) for u in urls)
    grequests.map(responses)

    return True


def write_message_log(sender_id, message_id, message_txt):
    logger.info("write_message_log(sender_id={sender_id}, message_id={message_id}, message_txt={message_txt})".format(sender_id=sender_id, message_id=message_id, message_txt=message_txt))

    try:
        conn = mysql.connect(Consts.MYSQL_HOST, Consts.MYSQL_USER, Consts.MYSQL_PASS, Consts.MYSQL_NAME)
        with conn:
            cur = conn.cursor(mysql.cursors.DictCursor)
            cur.execute('INSERT IGNORE INTO `chat_logs` (`id`, `fbps_id`, `message_id`, `body`, `added`) VALUES (NULL, "{fbps_id}", "{message_id}", "{body}", UTC_TIMESTAMP())'.format(fbps_id=sender_id, message_id=message_id, body=message_txt))
            conn.commit()

    except mysql.Error, e:
        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    finally:
        if conn:
            conn.close()



def build_button(btn_type, caption="", url="", payload=""):
    logger.info("build_button(btn_type={btn_type}, caption={caption}, payload={payload})".format(btn_type=btn_type, caption=caption, payload=payload))

    if btn_type == Consts.CARD_BTN_POSTBACK:
        button = {
            'type' : Consts.CARD_BTN_POSTBACK,
            'payload' : payload,
            'title' : caption
        }

    elif btn_type == Consts.CARD_BTN_URL:
        button = {
            'type' : Consts.CARD_BTN_URL,
            'url' : url,
            'title' : caption
        }

    elif btn_type == Consts.CARD_BTN_INVITE:
        button = {
            'type' : "element_share"
        }

    elif btn_type == Consts.KWIK_BTN_TEXT:
        button = {
            'content_type' : Consts.KWIK_BTN_TEXT,
            'title' : caption,
            'payload' : payload
        }

    return button


def build_quick_reply(btn_type, caption, payload, image_url=""):
    logger.info("build_quick_reply(btn_type={btn_type}, caption={caption}, payload={payload})".format(btn_type=btn_type, caption=caption, payload=payload))

    if btn_type == Consts.KWIK_BTN_TEXT:
        button = {
            'content_type' : Consts.KWIK_BTN_TEXT,
            'title' : caption,
            'payload' : payload
        }

    elif btn_type == Consts.KWIK_BTN_IMAGE:
        button = {
            'type' : Consts.KWIK_BTN_TEXT,
            'title' : caption,
            'image_url' : image_url,
            'payload' : payload
        }

    elif btn_type == Consts.KWIK_BTN_LOCATION:
        button = {
            'type' : Consts.KWIK_BTN_LOCATION,
            'title' : caption,
            'image_url' : image_url,
            'payload' : payload
        }

    else:
        button = {
            'type' : Consts.KWIK_BTN_TEXT,
            'title' : caption,
            'payload' : payload
        }

    return button


def build_survey_message(recipient_id, question, options=None):
    logger.info("build_survey_message(recipient_id={recipient_id}, question={question}, options={options})".format(recipient_id=recipient_id, question=question, options=options))

    if options is None:
        options = ["Close"]

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type' : "survey",
                'question' : question,
                'msgid' : time.time(),
                'options' : options
            }
        }
    }

    return data


    # data =  {
    #     "type": "survey",
    #     "question": "What would you like to do?",
    #     "msgid": "3er45",
    #     "options": [
    #         "Eat",
    #         "Drink",
    #         {
    #             "type": "url",
    #             "title": "View website",
    #             "url": "www.gupshup.io"
    #         }
    #     ]
    # }


def build_card_element(index, title, subtitle, image_url, item_url, buttons=None):
    logger.info("build_card_element(index={index}, title={title}, subtitle={subtitle}, image_url={image_url}, item_url={item_url}, buttons={buttons})".format(index=index, title=title, subtitle=subtitle, image_url=image_url, item_url=item_url, buttons=buttons))

    element = {
        'title' : title,
        'subtitle' : subtitle,
        'image_url' : image_url,
        'item_url' : item_url
    }

    if buttons is not None:
        element['buttons'] = buttons

    return element


def build_content_card(recipient_id, title, subtitle, image_url, item_url, buttons=None, quick_replies=None):
    logger.info("build_content_card(recipient_id={recipient_id}, title={title}, subtitle={subtitle}, image_url={image_url}, item_url={item_url}, buttons={buttons}, quick_replies={quick_replies})".format(recipient_id=recipient_id, title=title, subtitle=subtitle, image_url=image_url, item_url=item_url, buttons=buttons, quick_replies=quick_replies))

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type' : "template",
                'payload' : {
                    'template_type' : "generic",
                    'elements' : [
                        build_card_element(
                            index = 0,
                            title = title,
                            subtitle = subtitle,
                            image_url = image_url,
                            item_url = item_url,
                            buttons = buttons
                        )
                    ]
                }
            }
        }
    }

    if buttons is not None:
        data['message']['attachment']['payload']['elements'][0]['buttons'] = buttons

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    return data


def build_carousel(recipient_id, cards, quick_replies=None):
    logger.info("build_carousel(recipient_id={recipient_id}, cards={cards}, quick_replies={quick_replies})".format(recipient_id=recipient_id, cards=cards, quick_replies=quick_replies))

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type' : "template",
                'payload' : {
                    'template_type' : "generic",
                    'elements' : cards
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    return data


def welcome_message(recipient_id, entry_type, deeplink=""):
    logger.info("welcome_message(recipient_id={recipient_id}, entry_type={entry_type}, deeplink={deeplink})".format(recipient_id=recipient_id, entry_type=entry_type, deeplink=deeplink))

    send_video(recipient_id, "http://{ip_addr}/videos/intro_all.mp4".format(ip_addr=Consts.WEB_SERVER_IP), "179590205850150")
    if entry_type == Consts.MARKETPLACE_GREETING:
        send_text(recipient_id, Consts.ORTHODOX_GREETING)
        send_admin_carousel(recipient_id)

    elif entry_type == Consts.STOREFRONT_ADMIN:
        send_text(recipient_id, Consts.ORTHODOX_GREETING)
        send_admin_carousel(recipient_id)

    elif entry_type == Consts.CUSTOMER_EMPTY:
        send_text(recipient_id, Consts.ORTHODOX_GREETING)
        send_admin_carousel(recipient_id)

    elif entry_type == Consts.CUSTOMER_REFERRAL:
        storefront = None
        product = None

        product_query = Product.query.filter(Product.name == deeplink.split("/")[-1])
        if product_query.count() > 0:
            product = product_query.order_by(Product.added.desc()).scalar()
            storefront_query = Storefront.query.filter(Storefront.id == product.storefront_id)
            if storefront_query.count() > 0:
                storefront = storefront_query.first()

        else:
            storefront_query = Storefront.query.filter(Storefront.name == deeplink.split("/")[0])
            if storefront_query.count() > 0:
                storefront = storefront_query.first()
                product_query = Product.query.filter(Product.storefront_id == storefront.id)
                if product_query.count() > 0:
                    product = product_query.order_by(Product.added.desc()).scalar()

        if storefront is not None:
            customer_query = Customer.query.filter(Customer.fb_psid == recipient_id)
            if customer_query.count() > 0:
                customer = customer_query.first()

                product_id = 0
                subscription_query = Subscription.query.filter(Subscription.storefront_id == storefront.id).filter(Subscription.customer_id == customer.id)
                if product is not None:
                    product_id = product.id
                    subscription_query = subscription_query.filter(Subscription.product_id == product.id)

                if subscription_query.count() == 0:
                    db.session.add(Subscription(storefront.id, product.id, customer.id))
                    db.session.commit()

                    try:
                        conn = mysql.connect(Consts.MYSQL_HOST, Consts.MYSQL_USER, Consts.MYSQL_PASS, Consts.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('INSERT IGNORE INTO `subscriptions` (`id`, `user_id`, `storefront_id`, `product_id`, `added`) VALUES (NULL, "{user_id}", "{storefront_id}", "{product_id}", UTC_TIMESTAMP())'.format(user_id=customer.id, storefront_id=storefront.id, product_id=product_id))
                            conn.commit()

                    except mysql.Error, e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()

                    payload = {
                        'channel' : "#pre",
                        'username' : "fbprebot",
                        'icon_url' : "https://scontent.fsnc1-4.fna.fbcdn.net/t39.2081-0/p128x128/15728018_267940103621073_6998097150915641344_n.png",
                        'text' : "*{sender_id}* just subscribed to _{product_name}_ from a shop named _{storefront_name}_.\n{video_url}".format(sender_id=recipient_id, product_name=product.display_name, storefront_name=storefront.display_name, video_url=product.video_url),
                        'attachments' : [{
                            'image_url' : product.image_url
                        }]
                    }
                    response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })



        if storefront is not None:
            send_text(recipient_id, "Welcome to {storefront_name}'s Shop Bot on Pre. You have been subscribed to {storefront_name} updates.".format(storefront_name=storefront.display_name))
            send_storefront_carousel(recipient_id, storefront.id)

        else:
            send_text(recipient_id, Consts.ORTHODOX_GREETING)
            send_admin_carousel(recipient_id)

    else:
        send_text(recipient_id, Consts.ORTHODOX_GREETING)
        send_admin_carousel(recipient_id)


def send_admin_carousel(recipient_id):
    logger.info("send_admin_carousel(recipient_id={recipient_id})".format(recipient_id=recipient_id))

    #-- look for created storefront
    storefront_query = Storefront.query.filter(Storefront.owner_id == recipient_id)
    cards = []

    if storefront_query.count() == 0:
        cards.append(
            build_card_element(
                index = 0,
                title = "Create Shop",
                subtitle = "",
                image_url = Consts.IMAGE_URL_CREATE_SHOP,
                item_url = None,
                buttons = [
                    build_button(Consts.CARD_BTN_POSTBACK, caption="Create Shop", payload=Consts.PB_PAYLOAD_CREATE_STOREFRONT)
                ]
            )
        )

    else:
        storefront = storefront_query.first()

        if storefront.display_name is None:
            storefront.display_name = "[NAME NOT SET]"

        if storefront.description is None:
            storefront.description = ""

        if storefront.logo_url is None:
            storefront.logo_url = Consts.IMAGE_URL_ADD_PRODUCT

        if storefront.prebot_url is None:
            storefront.prebot_url = "http://prebot.me"


        product_query = Product.query.filter(Product.storefront_id == storefront.id)
        if product_query.count() == 0:
            cards.append(
                build_card_element(
                    index = 1,
                    title = "Add Item",
                    subtitle = "",
                    image_url = Consts.IMAGE_URL_ADD_PRODUCT,
                    item_url = None,
                    buttons = [
                        build_button(Consts.CARD_BTN_POSTBACK, caption="Add Item", payload=Consts.PB_PAYLOAD_ADD_PRODUCT)
                    ]
                )
            )

        else:
            product = product_query.order_by(Product.added.desc()).scalar()

            if product.prebot_url is None:
                product.prebot_url = "http://prebot.me"

            if product.display_name is None:
                product.display_name = "[NAME NOT SET]"

            if product.video_url is None:
                product.image_url = Consts.IMAGE_URL_ADD_PRODUCT
                product.video_url = None

            subscriber_query = Subscription.query.filter(Subscription.product_id == product.id).filter(Subscription.enabled == True)
            if subscriber_query.count() == 1:
                cards.append(
                    build_card_element(
                        index = 1,
                        title = "Message Customers",
                        subtitle =  "Notify your 1 subscriber",
                        image_url = Consts.IMAGE_URL_NOTIFY_SUBSCRIBERS,
                        item_url = None,
                        buttons = [
                            build_button(Consts.CARD_BTN_POSTBACK, caption="Message Customers", payload=Consts.PB_PAYLOAD_NOTIFY_SUBSCRIBERS)
                        ]
                    )
                )

            elif subscriber_query.count() > 1:
                cards.append(
                    build_card_element(
                        index = 1,
                        title = "Message Customers",
                        subtitle =  "Notify your {total} subscribers.".format(total=subscriber_query.count()),
                        image_url = Consts.IMAGE_URL_NOTIFY_SUBSCRIBERS,
                        item_url = None,
                        buttons = [
                            build_button(Consts.CARD_BTN_POSTBACK, caption="Message Customers", payload=Consts.PB_PAYLOAD_NOTIFY_SUBSCRIBERS)
                        ]
                    )
                )

            cards.append(
                build_card_element(
                    index = 1,
                    title = product.display_name,
                    subtitle = product.description,
                    image_url = product.image_url,
                    item_url = product.video_url,
                    buttons = [
                        build_button(Consts.CARD_BTN_POSTBACK, caption="Replace Item", payload=Consts.PB_PAYLOAD_DELETE_PRODUCT)
                    ]
                )
            )

        cards.append(
            build_card_element(
                index = 2,
                title = "Share Shop",
                subtitle = "",
                image_url = Consts.IMAGE_URL_SHARE_STOREFRONT,
                item_url = "http://prebot.me/share",
                buttons = [
                    build_button(Consts.CARD_BTN_POSTBACK, caption="Share Shop", payload=Consts.PB_PAYLOAD_SHARE_STOREFRONT)
                ]
            )
        )

    cards.append(
        build_card_element(
            index = 3,
            title = "View Shops",
            subtitle = "",
            image_url = Consts.IMAGE_URL_MARKETPLACE,
            item_url = "http://prebot.me/shops",
            buttons = [
                build_button(Consts.CARD_BTN_URL, caption="View Shops", url="http://prebot.me/shops")
            ]
        )
    )

    cards.append(
        build_card_element(
            index = 3,
            title = "Support",
            subtitle = "",
            image_url = Consts.IMAGE_URL_SUPPORT,
            item_url = "http://prebot.me/support",
            buttons = [
                build_button(Consts.CARD_BTN_URL, caption="Get Support", url="http://prebot.me/support")
            ]
        )
    )

    if storefront_query.count() > 0:
        storefront = storefront_query.first()
        cards.append(
            build_card_element(
                index = 0,
                title = storefront.display_name,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.prebot_url,
                buttons = [
                    build_button(Consts.CARD_BTN_POSTBACK, caption="Remove Shop", payload=Consts.PB_PAYLOAD_DELETE_STOREFRONT)
                ]
            )
        )

    data = build_carousel(
        recipient_id = recipient_id,
        cards = cards
    )

    send_message(json.dumps(data))


def send_storefront_carousel(recipient_id, storefront_id, product_name=""):
    logger.info("send_storefront_carousel(recipient_id={recipient_id}, storefront_id={storefront_id})".format(recipient_id=recipient_id, storefront_id=storefront_id))

    query = Storefront.query.filter(Storefront.id == storefront_id)
    if query.count() > 0:
        storefront = query.first()

        try:
            conn = mysql.connect(Consts.MYSQL_HOST, Consts.MYSQL_USER, Consts.MYSQL_PASS, Consts.MYSQL_NAME)
            with conn:
                cur = conn.cursor(mysql.cursors.DictCursor)
                cur.execute('UPDATE `storefronts` SET `views` = `views` + 1 WHERE `id` = {storefront_id} LIMIT 1;'.format(storefront_id=storefront.id))
                conn.commit()

        except mysql.Error, e:
            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

        finally:
            if conn:
                conn.close()

        query = Product.query.filter(Product.storefront_id == storefront.id)
        if query.count() > 0:
            product = query.order_by(Product.added.desc()).scalar()

            data = build_carousel(
                recipient_id = recipient_id,
                cards = [
                    build_card_element(
                        index = 0,
                        title = product.display_name,
                        subtitle = product.description,
                        image_url = product.image_url,
                        item_url = product.prebot_url,
                        buttons = [
                            build_button(Consts.CARD_BTN_URL, caption="Tap to Reserve", url="http://prebot.me/reserve/{product_id}".format(product_id=product.id)),
                            build_button(Consts.CARD_BTN_INVITE)
                        ]
                    ),
                    build_card_element(
                        index = 1,
                        title = storefront.display_name,
                        subtitle = storefront.description,
                        image_url = storefront.logo_url,
                        item_url = storefront.prebot_url,
                        buttons = [
                            build_button(Consts.CARD_BTN_INVITE)
                        ]
                    ),
                    build_card_element(
                        index = 3,
                        title = "View Shops",
                        subtitle = "",
                        image_url = Consts.IMAGE_URL_MARKETPLACE,
                        item_url = "http://prebot.me/shops",
                        buttons = [
                            build_button(Consts.CARD_BTN_URL, caption="View Shops", url="http://prebot.me/shops")
                        ]
                    ),
                    build_card_element(
                        index = 2,
                        title = "Support",
                        subtitle = "",
                        image_url = Consts.IMAGE_URL_SUPPORT,
                        item_url = "http://prebot.me/support",
                        buttons = [
                            build_button(Consts.CARD_BTN_URL, caption="Get Support", url="http://prebot.me/support")
                        ]
                    )
                ]
            )

            send_message(json.dumps(data))


def send_storefront_card(recipient_id, storefront_id, card_type=Consts.CARD_TYPE_STOREFRONT):
    logger.info("send_storefront_card(recipient_id={recipient_id}, storefront_id={storefront_id}, card_type={card_type})".format(recipient_id=recipient_id, storefront_id=storefront_id, card_type=card_type))

    query = Storefront.query.filter(Storefront.id == storefront_id)
    if query.count() > 0:
        storefront = query.first()

        if card_type == Consts.CARD_TYPE_STOREFRONT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = storefront.display_name,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.prebot_url,
                buttons = [
                    build_button(Consts.CARD_BTN_INVITE)
                ]
            )

        elif card_type == Consts.CARD_TYPE_PREVIEW_STOREFRONT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = storefront.display_name,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.prebot_url,
                quick_replies = [
                    build_quick_reply(Consts.KWIK_BTN_TEXT, "Submit", Consts.PB_PAYLOAD_SUBMIT_STOREFRONT),
                    build_quick_reply(Consts.KWIK_BTN_TEXT, "Re-Do", Consts.PB_PAYLOAD_REDO_STOREFRONT),
                    build_quick_reply(Consts.KWIK_BTN_TEXT, "Cancel", Consts.PB_PAYLOAD_CANCEL_STOREFRONT)
                ]
            )

        elif card_type == Consts.CARD_TYPE_SHARE_STOREFRONT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = storefront.display_name,
                subtitle = "",
                image_url = storefront.logo_url,
                item_url = storefront.prebot_url,
                buttons = [
                    build_button(Consts.CARD_BTN_INVITE)
                ]
            )

        else:
            data = build_content_card(
                recipient_id = recipient_id,
                title = storefront.display_name,
                subtitle = storefront.description,
                image_url = storefront.logo_url,
                item_url = storefront.prebot_url,
                buttons = [
                    build_button(Consts.CARD_BTN_INVITE)
                ]
            )

        send_message(json.dumps(data))


def send_product_card(recipient_id, product_id, card_type=Consts.CARD_TYPE_PRODUCT):
    logger.info("send_product_card(recipient_id={recipient_id}, product_id={product_id}, card_type={card_type})".format(recipient_id=recipient_id, product_id=product_id, card_type=card_type))

    query = Product.query.filter(Product.id == product_id)
    if query.count() > 0:
        product = query.order_by(Product.added.desc()).scalar()

        if product.image_url is None:
            product.image_url = Consts.IMAGE_URL_ADD_PRODUCT

        if card_type == Consts.CARD_TYPE_PRODUCT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
                subtitle = product.description,
                image_url = product.image_url,
                item_url = product.video_url,
                buttons = [
                    build_button(Consts.CARD_BTN_URL, caption="Tap to Reserve", url="http://prebot.me/reserve/{product_id}".format(product_id=product_id))
                ]
            )

        elif card_type == Consts.CARD_TYPE_PREVIEW_PRODUCT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
                subtitle = product.description,
                image_url = product.image_url,
                item_url = product.video_url,
                quick_replies = [
                    build_quick_reply(Consts.KWIK_BTN_TEXT, "Submit", Consts.PB_PAYLOAD_SUBMIT_PRODUCT),
                    build_quick_reply(Consts.KWIK_BTN_TEXT, "Re-Do", Consts.PB_PAYLOAD_REDO_PRODUCT),
                    build_quick_reply(Consts.KWIK_BTN_TEXT, "Cancel", Consts.PB_PAYLOAD_CANCEL_PRODUCT)
                ]
            )

        elif card_type == Consts.CARD_TYPE_SHARE_PRODUCT:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
                subtitle = product.description,
                image_url = product.image_url,
                item_url = product.video_url,
                buttons = [
                    build_button(Consts.CARD_BTN_INVITE)
                ]
            )

        else:
            data = build_content_card(
                recipient_id = recipient_id,
                title = product.display_name,
                subtitle = product.description,
                image_url = product.image_url,
                item_url = product.video_url,
                buttons = [
                    build_button(Consts.CARD_BTN_URL, caption="Tap to Reserve", url="http://prebot.me/reserve/{product_id}".format(product_id=product_id))
                ]
            )

        send_message(json.dumps(data))



@api.route('/', methods=['POST'])
def webook():

    if 'is_echo' in request.data:
        return "OK", 200

    if 'delivery' in request.data or 'read' in request.data or 'optin' in request.data:
        return "OK", 200

    data = request.get_json()

    logger.info("\n\n[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    logger.info("[=-=-=-=-=-=-=-[POST DATA]-=-=-=-=-=-=-=-=]")
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    logger.info(data)
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")

    if data['object'] == "page":
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                sender_id = messaging_event['sender']['id']
                recipient_id = messaging_event['recipient']['id']  # the recipient's ID, which should be your page's facebook ID
                timestamp = messaging_event['timestamp']

                message_id = None
                message_text = None

                if sender_id == "177712676037903":
                    logger.info("-=- MESSAGE-ECHO -=-")
                    return "OK", 200

                if 'delivery' in messaging_event:  # delivery confirmation
                    logger.info("-=- DELIVERY-CONFIRM -=-")
                    return "OK", 200

                if 'read' in messaging_event:  # read confirmation
                    logger.info("-=- READ-CONFIRM -=- %s" % (recipient_id))
                    send_tracker("read-receipt", sender_id, "")
                    return "OK", 200

                if 'optin' in messaging_event:  # optin confirmation
                    logger.info("-=- OPT-IN -=-")
                    return "OK", 200


                #-- drop sqlite data
                #drop_sqlite()



                #-- look for created storefront
                storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 4)
                logger.info("STOREFRONTS -->%s" % (Storefront.query.filter(Storefront.owner_id == sender_id).all()))

                if storefront_query.count() > 0:
                    logger.info("PRODUCTS -->%s" % (Product.query.filter(Product.storefront_id == storefront_query.first().id).all()))
                    logger.info("SUBSCRIPTIONS -->%s" % (Subscription.query.filter(Subscription.storefront_id == storefront_query.first().id).all()))

                #-- entered via url referral
                referral = ""
                if 'referral' in messaging_event:
                    referral = messaging_event['referral']['ref']
                    welcome_message(sender_id, Consts.CUSTOMER_REFERRAL, referral[1:])
                    return "OK", 200


                #-- check sqlite for user
                users_query = Customer.query.filter(Customer.fb_psid == sender_id)
                logger.info("USERS -->%s" % (Customer.query.filter(Customer.fb_psid == sender_id).all()))
                if users_query.count() == 0:
                    db.session.add(Customer(fb_psid=sender_id, fb_name="", referrer=referral))
                    db.session.commit()

                    try:
                        conn = mysql.connect(Consts.MYSQL_HOST, Consts.MYSQL_USER, Consts.MYSQL_PASS, Consts.MYSQL_NAME)
                        with conn:
                            cur = conn.cursor(mysql.cursors.DictCursor)
                            cur.execute('INSERT IGNORE INTO `users` (`id`, `fb_psid`, `referrer`, `added`) VALUES (NULL, "{fbps_id}", "{referrer}", UTC_TIMESTAMP())'.format(fbps_id=sender_id, referrer=referral))
                            conn.commit()

                    except mysql.Error, e:
                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                    finally:
                        if conn:
                            conn.close()


                #-- postback response w/ payload
                if 'postback' in messaging_event:
                    payload = messaging_event['postback']['payload']
                    logger.info("-=- POSTBACK RESPONSE -=- (%s)" % (payload))

                    if payload == Consts.PB_PAYLOAD_GREETING:
                        logger.info("----------=BOT GREETING @({timestamp})=----------".format(timestamp=time.strftime("%Y-%m-%d %H:%M:%S")))
                        send_tracker("signup-fb-pre", sender_id, "")
                        welcome_message(sender_id, Consts.MARKETPLACE_GREETING)

                    elif payload == Consts.PB_PAYLOAD_CREATE_STOREFRONT:
                        send_tracker("button-create-shop", sender_id, "")

                        for storefront in Storefront.query.filter(Storefront.owner_id == sender_id):
                            storefront.enabled = False
                            for product in Product.query.filter(Product.storefront_id == storefront.id):
                                product.enabled = False

                        db.session.add(Storefront(sender_id))
                        db.session.commit()

                        send_text(sender_id, "Give your Pre Shop Bot a name.")


                    elif payload == Consts.PB_PAYLOAD_DELETE_STOREFRONT:
                        send_tracker("button-delete-shop", sender_id, "")

                        for storefront in Storefront.query.filter(Storefront.owner_id == sender_id):
                            send_text(sender_id, "{storefront_name} has been removed.".format(storefront_name=storefront.display_name))
                            storefront.enabled = False
                            for product in Product.query.filter(Product.storefront_id == storefront.id):
                                product.enabled = False

                        db.session.commit()

                        try:
                            conn = mysql.connect(Consts.MYSQL_HOST, Consts.MYSQL_USER, Consts.MYSQL_PASS, Consts.MYSQL_NAME)
                            with conn:
                                cur = conn.cursor(mysql.cursors.DictCursor)
                                cur.execute('UPDATE `storefronts` SET `enabled` = 0 WHERE `id` = {storefront_id};'.format(storefront_id=storefront.id))
                                cur.execute('UPDATE `products` SET `enabled` = 0 WHERE `storefront_id` = {storefront_id};'.format(storefront_id=storefront.id))
                                cur.execute('UPDATE `subscriptions` SET `enabled` = 0 WHERE `storefront_id` = {storefront_id};'.format(storefront_id=storefront.id))
                                conn.commit()

                        except mysql.Error, e:
                            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                        finally:
                            if conn:
                                conn.close()


                        send_admin_carousel(sender_id)


                    elif payload == Consts.PB_PAYLOAD_ADD_PRODUCT:
                        send_tracker("button-add-item", sender_id, "")

                        # storefront = storefront_query.first()
                        # for product in Product.query.filter(Product.storefront_id == storefront.id):
                        #     Product.query.filter(Product.storefront_id == storefront.id).delete()

                        db.session.add(Product(storefront_query.first().id))
                        db.session.commit()

                        send_text(sender_id, "Give your pre-sale product or item a name.")


                    elif payload == Consts.PB_PAYLOAD_DELETE_PRODUCT:
                        send_tracker("button-delete-item", sender_id, "")

                        storefront = storefront_query.first()

                        product_ids = []
                        for product in Product.query.filter(Product.storefront_id == storefront.id):
                            product.enabled = False
                            product_ids.append(product.id)
                            send_text(sender_id, "{product_name} has been removed.".format(product_name=product.display_name))
                            for subscription in Subscription.query.filter(Subscription.product_id == product.id):
                                subscription.enabled = False

                        db.session.commit()

                        try:
                            conn = mysql.connect(Consts.MYSQL_HOST, Consts.MYSQL_USER, Consts.MYSQL_PASS, Consts.MYSQL_NAME)
                            with conn:
                                cur = conn.cursor(mysql.cursors.DictCursor)
                                cur.execute('UPDATE `products` SET `enabled` = 0 WHERE `storefront_id` = {storefront_id};'.format(storefront_id=storefront.id))
                                if len(product_ids) > 0:
                                    print("UPDATING SUBSCRIPTIONS -->\n%s" % ('UPDATE `subscriptions` SET `enabled` = 0 WHERE `added` = "0000-00-00 00:00:00" {product_ids};'.format(product_ids=" OR `product_id` = ".join(product_ids))))
                                    cur.execute('UPDATE `subscriptions` SET `enabled` = 0 WHERE `added` = "0000-00-00 00:00:00" {product_ids};'.format(product_ids=" OR `product_id` = ".join(product_ids)))
                                conn.commit()

                        except mysql.Error, e:
                            logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                        finally:
                            if conn:
                                conn.close()


                        send_admin_carousel(sender_id)


                    elif payload == Consts.PB_PAYLOAD_SHARE_STOREFRONT:
                        send_tracker("button-share", sender_id, "")
                        send_storefront_card(sender_id, storefront_query.first().id, Consts.CARD_TYPE_SHARE_STOREFRONT)
                        send_admin_carousel(sender_id)


                    elif payload == Consts.PB_PAYLOAD_SUPPORT:
                        send_tracker("button-support", sender_id, "")
                        send_text(sender_id, "Support for Prebot:\nprebot.me/support")


                    elif payload == Consts.PB_PAYLOAD_RESERVE_PRODUCT:
                        send_tracker("button-reserve", sender_id, "")


                    else:
                        send_tracker("unknown-button", sender_id, "")
                        send_text(sender_id, "Button not recognized!")

                    return "OK", 200


                #-- actual message
                if 'message' in messaging_event:#.get('message'):
                    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECEIVED ->{message}".format(message=messaging_event['sender']))
                    message = messaging_event['message']
                    message_id = message['mid']
                    message_text = ""

                    #-- insert to log
                    write_message_log(sender_id, message_id, message)

                    if 'attachments' in message:
                        for attachment in message['attachments']:

                            #------- IMAGE MESSAGE
                            if attachment['type'] == "image":
                                logger.info("IMAGE: %s" % (attachment['payload']['url']))
                                query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 2)

                                if query.count() > 0:
                                    storefront = query.first()
                                    storefront.creation_state = 3
                                    storefront.logo_url = attachment['payload']['url']
                                    db.session.commit()

                                    send_text(sender_id, "Here's what your shop will look like:")
                                    send_storefront_card(sender_id, storefront.id, Consts.CARD_TYPE_PREVIEW_STOREFRONT)

                            #------- VIDEO MESSAGE
                            elif attachment['type'] == "video":
                                logger.info("VIDEO: %s" % (attachment['payload']['url']))
                                query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 1)

                                if query.count() > 0:
                                    file_path = os.path.dirname(os.path.realpath(__file__))
                                    timestamp = int(time.time())

                                    with open("{file_path}/videos/{timestamp}.mp4".format(file_path=file_path, timestamp=timestamp), 'wb') as handle:
                                        response = requests.get(attachment['payload']['url'], stream=True)

                                        if not response.ok:
                                            logger.info("DOWNLOAD FAILED!!! %s" % (response.text))

                                        for block in response.iter_content(1024):
                                            handle.write(block)


                                    container = av.open("{file_path}/videos/{timestamp}.mp4".format(file_path=file_path, timestamp=timestamp))
                                    video = next(s for s in container.streams if s.type == b'video')
                                    for packet in container.demux(video):
                                        for frame in packet.decode():
                                            if frame.index == 20:
                                                frame.to_image().save("/var/www/html/thumbs/{timestamp}.jpg".format(file_path=file_path, timestamp=timestamp))
                                                break

                                    os.remove("{file_path}/videos/{timestamp}.mp4".format(file_path=file_path, timestamp=timestamp))
                                    product = query.order_by(Product.added.desc()).scalar()
                                    product.creation_state = 2
                                    product.image_url = "http://{ip_addr}/thumbs/{timestamp}.jpg".format(ip_addr=Consts.WEB_SERVER_IP, timestamp=timestamp)
                                    product.video_url = attachment['payload']['url']
                                    db.session.commit()

                                    send_text(
                                        recipient_id = sender_id,
                                        message_text = "Select the date range your product will be exclusively available.",
                                        quick_replies = [
                                            build_quick_reply(Consts.KWIK_BTN_TEXT, "Right Now", Consts.PB_PAYLOAD_PRODUCT_RELEASE_NOW),
                                            build_quick_reply(Consts.KWIK_BTN_TEXT, "Next Month", Consts.PB_PAYLOAD_PRODUCT_RELEASE_30_DAYS),
                                            build_quick_reply(Consts.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=2)).strftime('%B %Y'), Consts.PB_PAYLOAD_PRODUCT_RELEASE_60_DAYS),
                                            build_quick_reply(Consts.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=3)).strftime('%B %Y'), Consts.PB_PAYLOAD_PRODUCT_RELEASE_90_DAYS),
                                            build_quick_reply(Consts.KWIK_BTN_TEXT, (datetime.now() + relativedelta(months=4)).strftime('%B %Y'), Consts.PB_PAYLOAD_PRODUCT_RELEASE_120_DAYS)
                                        ]
                                    )

                        return "OK", 200

                    else:
                        if 'quick_reply' in message:
                            quick_reply = message['quick_reply']['payload'].encode('utf-8')
                            logger.info("QR --> {quick_replies}".format(quick_replies=message['quick_reply']['payload'].encode('utf-8')))

                            if quick_reply == Consts.PB_PAYLOAD_SUBMIT_STOREFRONT:
                                send_tracker("button-submit-store", sender_id, "")

                                storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 3)
                                if storefront_query.count() > 0:
                                    storefront = storefront_query.first();
                                    storefront.creation_state = 4
                                    storefront.added = datetime.utcnow()
                                    db.session.commit()

                                    try:
                                        conn = mysql.connect(Consts.MYSQL_HOST, Consts.MYSQL_USER, Consts.MYSQL_PASS, Consts.MYSQL_NAME)
                                        with conn:
                                            cur = conn.cursor(mysql.cursors.DictCursor)
                                            cur.execute('INSERT IGNORE INTO `storefronts` (`id`, `owner_id`, `name`, `display_name`, `description`, `logo_url`, `prebot_url`, `added`) VALUES (NULL, {owner_id}, "{name}", "{display_name}", "{description}", "{logo_url}", "{prebot_url}", UTC_TIMESTAMP())'.format(owner_id=users_query.first().id, name=storefront.name, display_name=storefront.display_name, description=storefront.description, logo_url=storefront.logo_url, prebot_url=storefront.prebot_url))
                                            conn.commit()

                                    except mysql.Error, e:
                                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                                    finally:
                                        if conn:
                                            conn.close()


                                    send_text(sender_id, "{storefront_name} has been successful created..\n{storefront_url}".format(storefront_name=storefront.display_name, storefront_url=re.sub(r'https?:\/\/', '', storefront.prebot_url)))
                                    send_admin_carousel(sender_id)

                                    payload = {
                                        'channel' : "#pre",
                                        'username' : "fbprebot",
                                        'icon_url' : "https://scontent.fsnc1-4.fna.fbcdn.net/t39.2081-0/p128x128/15728018_267940103621073_6998097150915641344_n.png",
                                        'text' : "*{sender_id}* just created a shop named _{storefront_name}_.".format(sender_id=sender_id, storefront_name=storefront.display_name),
                                        'attachments' : [{
                                            'image_url' : storefront.logo_url
                                        }]
                                    }
                                    response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })


                            elif quick_reply == Consts.PB_PAYLOAD_REDO_STOREFRONT:
                                send_tracker("button-redo-store", sender_id, "")

                                storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 3)
                                if storefront_query.count() > 0:
                                    Storefront.query.filter(Storefront.owner_id == sender_id).delete()
                                    db.session.commit()

                                db.session.add(Storefront(sender_id))
                                db.session.commit()

                                send_text(sender_id, "Give your Pre Shop Bot a name.")

                            elif quick_reply == Consts.PB_PAYLOAD_CANCEL_STOREFRONT:
                                send_tracker("button-cancel-store", sender_id, "")

                                send_text(sender_id, "Canceling your {storefront_name} shop creation...".format(storefront_name=storefront.display_name))
                                storefront_query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state == 3)
                                if storefront_query.count() > 0:
                                    Storefront.query.filter(Storefront.owner_id == sender_id).delete()
                                    db.session.commit()

                                send_admin_carousel(sender_id)

                            elif re.search('PRODUCT_RELEASE_(\d+)_DAYS', quick_reply) is not None:
                                match = re.match(r'PRODUCT_RELEASE_(\d+)_DAYS', quick_reply)
                                send_tracker("button-product-release-{days}-days-store".format(days=match.group(1)), sender_id, "")

                                product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 2)
                                if product_query.count() > 0:
                                    product = product_query.order_by(Product.added.desc()).scalar()
                                    product.release_date = (datetime.utcnow() + relativedelta(months=int(int(match.group(1)) / 30))).replace(hour=0, minute=0, second=0, microsecond=0)
                                    product.description = "Pre-release ends {release_date}".format(release_date=product.release_date.strftime('%a, %b %-d'))
                                    product.creation_state = 3
                                    db.session.commit()

                                    send_text(sender_id, "Here's what your product will look like:")
                                    send_product_card(sender_id, product.id, Consts.CARD_TYPE_PREVIEW_PRODUCT)

                            elif quick_reply == Consts.PB_PAYLOAD_SUBMIT_PRODUCT:
                                send_tracker("button-submit-product", sender_id, "")

                                product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state == 3)
                                if product_query.count() > 0:
                                    product = product_query.order_by(Product.added.desc()).scalar()
                                    product.creation_state = 4
                                    product.added = datetime.utcnow()
                                    db.session.commit()

                                    try:
                                        conn = mysql.connect(Consts.MYSQL_HOST, Consts.MYSQL_USER, Consts.MYSQL_PASS, Consts.MYSQL_NAME)
                                        with conn:
                                            cur = conn.cursor(mysql.cursors.DictCursor)
                                            cur.execute('INSERT IGNORE INTO `products` (`id`, `storefront_id`, `name`, `display_name`, `description`, `image_url`, `video_url`, `attachment_id`, `price`, `prebot_url`, `release_date`, `added`) VALUES (NULL, {storefront_id}, "{name}", "{display_name}", "{description}", "{image_url}", "{video_url}", "{attachment_id}", {price}, "{prebot_url}", "{release_date}", UTC_TIMESTAMP())'.format(storefront_id=product.storefront_id, name=product.name, display_name=product.display_name, description=product.description, image_url=product.image_url, video_url=product.video_url, attachment_id=product.attachment_id, price=product.price, prebot_url=product.prebot_url, release_date=product.release_date))
                                            conn.commit()

                                    except mysql.Error, e:
                                        logger.info("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

                                    finally:
                                        if conn:
                                            conn.close()


                                    send_text(sender_id, "Success! You have added {product_name}.\n{product_url}".format(product_name=product.display_name, product_url=re.sub(r'https?:\/\/', '', product.prebot_url)))
                                    send_product_card(sender_id, product.id, Consts.CARD_TYPE_SHARE_PRODUCT)

                                    payload = {
                                        'channel' : "#pre",
                                        'username' : "fbprebot",
                                        'icon_url' : "https://scontent.fsnc1-4.fna.fbcdn.net/t39.2081-0/p128x128/15728018_267940103621073_6998097150915641344_n.png",
                                        'text' : "*{sender_id}* just created a product named _{product_name}_ for the shop _{storefront_name}_.\n<{video_url}>".format(sender_id=sender_id, product_name=product.display_name, storefront_name=storefront_query.first().display_name, video_url=product.video_url),
                                        'attachments' : [{
                                            'image_url' : product.image_url
                                        }]
                                    }
                                    response = requests.post("https://hooks.slack.com/services/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", data={ 'payload' : json.dumps(payload) })

                                send_admin_carousel(sender_id)

                            elif quick_reply == Consts.PB_PAYLOAD_REDO_PRODUCT:
                                send_tracker("button-redo-product", sender_id, "")

                                product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id)
                                if product_query.count() > 0:
                                    product = product_query.order_by(Product.added.desc()).scalar()
                                    Product.query.filter(Product.storefront_id == storefront_query.first().id).delete()

                                db.session.add(Product(storefront_query.first().id))
                                db.session.commit()

                                send_text(sender_id, "Give your product a name.")

                            elif quick_reply == Consts.PB_PAYLOAD_CANCEL_PRODUCT:
                                send_tracker("button-undo-product", sender_id, "")

                                product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id)
                                if product_query.count() > 0:
                                    product = product_query.order_by(Product.added.desc()).scalar()
                                    send_text(sender_id, "Canceling your {product_name} product creation...".format(product_name=product.display_name))

                                    Product.query.filter(Product.storefront_id == storefront_query.first().id).delete()
                                    db.session.commit()

                                send_admin_carousel(sender_id)



                        #-- text entry
                        else:
                            message_text = ""
                            if 'text' in message:
                                message_text = message['text']  # the message's text


                                #-- force referral
                                if message_text.startswith("/"):
                                    welcome_message(sender_id, Consts.CUSTOMER_REFERRAL, message_text[1:])
                                    return "OK", 200


                                #-- return home
                                if message_text.lower() in Consts.RESERVED_MENU_REPLIES:
                                    if storefront_query.count() > 0:
                                        product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4)
                                        if product_query.count() > 0:
                                            Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4).delete()

                                    Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state < 4).delete()
                                    db.session.commit()

                                    send_admin_carousel(sender_id)
                                    return "OK", 200

                                #-- quit message
                                if message_text.lower() in Consts.RESERVED_STOP_REPLIES:
                                    if storefront_query.count() > 0:
                                        product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4)
                                        if product_query.count() > 0:
                                            Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4).delete()

                                    Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state < 4).delete()
                                    db.session.commit()

                                    send_text(sender_id, Consts.GOODBYE_MESSAGE)
                                    return "OK", 200

                                #-- has active storefront
                                if storefront_query.count() > 0:
                                    #-- look for in-progress product creation
                                    product_query = Product.query.filter(Product.storefront_id == storefront_query.first().id).filter(Product.creation_state < 4)
                                    if product_query.count() > 0:
                                        product = product_query.order_by(Product.added.desc()).scalar()

                                        #-- name submitted
                                        if product.creation_state == 0:
                                            product.creation_state = 1
                                            product.display_name = message_text
                                            product.name = message_text.replace(" ", "_")
                                            product.prebot_url = "http://prebot.me/{storefront_slug}/{product_slug}".format(storefront_slug=storefront_query.first().name, product_slug=product.name)
                                            db.session.commit()

                                            send_text(sender_id, "Upload a product video under 30 seconds.")

                                        return "OK", 200

                                    else:
                                        welcome_message(sender_id, Consts.CUSTOMER_REFERRAL, message_text)

                                else:
                                    #-- look for in-progress storefront creation
                                    query = Storefront.query.filter(Storefront.owner_id == sender_id).filter(Storefront.creation_state < 4)
                                    if query.count() > 0:
                                        storefront = query.first()

                                        #-- name submitted
                                        if storefront.creation_state == 0:
                                            storefront.creation_state = 1
                                            storefront.display_name = message_text
                                            storefront.name = message_text.replace(" ", "_")
                                            storefront.prebot_url = "http://prebot.me/{storefront_slug}".format(storefront_slug=escape(message_text.replace(" ", "_")))
                                            db.session.commit()

                                            send_text(sender_id, "Give {storefront_name} a description.".format(storefront_name=storefront.display_name))

                                        #-- description entered
                                        elif storefront.creation_state == 1:
                                            storefront.creation_state = 2
                                            storefront.description = message_text
                                            db.session.commit()

                                            send_text(sender_id, "Upload an avatar image for {storefront_name}".format(storefront_name=storefront.display_name))

                                    else:
                                        welcome_message(sender_id, Consts.CUSTOMER_REFERRAL, message_text)

                else:
                    send_text(sender_id, Consts.UNKNOWN_MESSAGE)

    return "OK", 200



#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#
#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#



@api.route('/', methods=['GET'])
def verify():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= GET --   ({hub_mode})->{request}".format(hub_mode=request.args.get('hub.mode'), request=request.args))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == Consts.VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args['hub.challenge'], 200

    return "OK", 200

#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#
#-- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#

def send_typing_indicator(recipient_id, is_typing):

    if is_typing:
        sender_action = "typing_on"

    else:
        sender_action = "typing_off"

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'sender_action' : sender_action
    }

    send_message(json.dumps(data))


def send_text(recipient_id, message_text, quick_replies=None):
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'text' : message_text
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_image(recipient_id, url, quick_replies=None):
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message' : {
            'attachment' : {
                'type' : "image",
                'payload' : {
                    'url' : url
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_video(recipient_id, url, attachment_id=None, quick_replies=None):
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            "id" : recipient_id
        },
        'message' : {
            'attachment' : {
                'type' : "video",
                'payload' : {
                    'url' : url,
                    'is_reusable' : True
                }
            }
        }
    }

    if attachment_id is None:
        data['message']['attachment']['payload'] = {
            'url' : url,
            'is_reusable' : True
        }

    else:
        data['message']['attachment']['payload'] = { 'attachment_id' : attachment_id }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_message(payload):
    logger.info("\nsend_message(payload={payload})".format(payload=payload))

    timestamp = int(time.time() * 1000)
    buf = cStringIO.StringIO()

    c = pycurl.Curl()
    c.setopt(c.HTTPHEADER, ["Content-Type: application/json"])
    c.setopt(c.URL, "https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=Consts.ACCESS_TOKEN))
    c.setopt(c.POST, 1)
    c.setopt(c.POSTFIELDS, payload)
    c.setopt(c.CONNECTTIMEOUT, 300)
    c.setopt(c.TIMEOUT, 60)
    c.setopt(c.FAILONERROR, True)

    try:
        c.perform()
        logger.info("SEND MESSAGE response code: {code}".format(code=c.getinfo(c.RESPONSE_CODE)))
        c.close()

    except pycurl.error, error:
        errno, errstr = error
        logger.info("SEND MESSAGE Error: -({errno})- {errstr}".format(errno=errno, errstr=errstr))

    finally:
        #logger.info("SEND MESSAGE body: {body}".format(body=buf.getvalue()))
        buf.close()

    return True

