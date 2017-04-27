#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import csv
import locale
import time

from datetime import datetime


import tornado.escape
import tornado.httpclient
import tornado.ioloop
import tornado.web

from kik.error import KikError
from kik import KikApi, Configuration
from kik.messages import messages_from_json, StartChattingMessage, TextMessage, FriendPickerMessage, LinkMessage, PictureMessage, StickerMessage, ScanDataMessage, VideoMessage, DeliveryReceiptMessage, ReadReceiptMessage, UnknownMessage


import modd
import const as Const


Const.NOTIFY_TOKEN = "fc687eb48dac3e322f89234fde5d2d4e"


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#



#--:-- Message UI / Message Part Factories --:--#
#-=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- -=:=- #


def default_text_reply(message, delay=0, type_time=500):
    print("default_text_reply(message=%s)" % (message))

    try:
        kik.send_messages([
            TextMessage(
                to = message.from_user,
                chat_id = message.chat_id,
                body = "Lemonade on Kik is launching soon. You will be notified here once the bot goes live.\n\nm.me/lmon8\ntwitter.com/lmon8de",
                type_time = type_time,
                delay = delay
            )
        ])
    except KikError as err:
        print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))


# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


def write_log(message, body=None):
    log_csv = "/opt/kik_bot/var/log/lmon8.pre.%s.csv" % (datetime.now().strftime('%Y-%m-%d'))
    with open(log_csv, 'a') as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message.chat_id, message.from_user, message.body if body is None else body])


# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


class Lmon8(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    def post(self):
        print("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

        #-- missing header
        if not kik.verify_signature(self.request.headers.get('X-Kik-Signature'), self.request.body):
            print("self.request.headers.get('X-Kik-Signature')=%s" % (self.request.headers.get('X-Kik-Signature')))
            print("403 Forbidden")
            self.set_status(403)
            return


        #-- parse
        data_json = tornado.escape.json_decode(self.request.body)
        messages = messages_from_json(data_json["messages"])
        print(":::::::: MESSAGES :::::::::\n%s" % (data_json["messages"]))

        #-- each message
        for message in messages:

            # -=-=-=-=-=-=-=-=- UNSUPPORTED TYPE -=-=-=-=-=-=-=-=-
            if isinstance(message, FriendPickerMessage) or isinstance(message, LinkMessage) or isinstance(message, PictureMessage) or isinstance(message, VideoMessage) or isinstance(message, ScanDataMessage) or isinstance(message, StickerMessage) or isinstance(message, UnknownMessage):
                print("=-= IGNORING MESSAGE =-=\n%s " % (message))
                default_text_reply(message=message)

                self.set_status(200)
                return


            # -=-=-=-=-=-=-=-=- DELIVERY RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
            elif isinstance(message, DeliveryReceiptMessage):
                print ("-= DeliveryReceiptMessage =-= ")


            # -=-=-=-=-=-=-=-=- READ RECEIPT MESSAGE -=-=-=-=-=-=-=-=-
            elif isinstance(message, ReadReceiptMessage):
                print ("-= ReadReceiptMessage =-= ")


            # -=-=-=-=-=-=-=-=- START CHATTING -=-=-=-=-=-=-=-=-
            elif isinstance(message, StartChattingMessage):
                print("-= StartChattingMessage =-= ")

                write_log(message, "__START_CHATTING__")
                default_text_reply(message)


            # -=-=-=-=-=-=-=-=- TEXT MESSAGE -=-=-=-=-=-=-=-=-
            elif isinstance(message, TextMessage):
                print("=-= TextMessage =-= ")

                write_log(message)
                default_text_reply(message)


            self.set_status(200)
            return



# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #



class UserNotify(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    def post(self):
        print("-=-=-=-=-=-=-=-=-=-= PRODUCT NOTIFY =-=-=-=-=-=-=-=-=-=-=")
        print("from_user:{from_user}".format(from_user=self.get_argument('from_user', "")))
        print("chat_id:{chat_id}".format(chat_id=self.get_argument('chat_id', "")))
        print("item_id:{item_id}".format(item_id=self.get_argument('item_id', "")))
        print("item_url:{item_url}".format(item_url=self.get_argument('item_url', "")))
        print("img_url:{img_url}".format(img_url=self.get_argument('img_url', "")))
        print("body_txt:{body_txt}".format(body_txt=self.get_argument('body_txt', "")))
        print("attrib_txt:{attrib_txt}".format(attrib_txt=self.get_argument('attrib_txt', "")))
        print("-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-==-=-=-=-=-=-=-=-=-=-=")

        if self.get_argument('token', "") == Const.NOTIFY_TOKEN:
            from_user = self.get_argument('from_user', "")
            chat_id = self.get_argument('chat_id', "")
            item_id = self.get_argument('item_id', "")
            item_url = self.get_argument('item_url', "")
            img_url = self.get_argument('img_url', "")
            body_txt = self.get_argument('body_txt', "")
            attrib_txt = self.get_argument('attrib_txt', "")

            modd.utils.send_evt_tracker(category="broadcast", action=chat_id, label=from_user)

            try:
                kik.send_messages([
                    TextMessage(
                        to = from_user,
                        chat_id = chat_id,
                        body = body_txt
                    )
                ])


            except KikError as err:
                print("::::::[kik.send_messages] kik.KikError - {message}".format(message=err))

            self.set_status(200)

        else:
            self.set_status(403)

        return

# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #


#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#
#=- -=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=--=#=- -=#


Const.KIK_API_CONFIG = {
    'USERNAME' : "lmon8.mall",
    'API_KEY'  : "ecc182af-b642-4a0b-a464-9b15792c2db7",
    'WEBHOOK'  : {
        'HOST' : "http://159.203.250.4",
        'PORT' : 8081,
        'PATH' : "lmon8"
    },

    'FEATURES' : {
        'receiveDeliveryReceipts' : False,
        'receiveReadReceipts'     : False
    }
}


# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #
# -[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]- #




#-=:=- Start + Config Kik -=:=-#
#-=:=--=:=--=:=--=:=--=:=--=:=--=:=--=:=--=:=--=:=-#
locale.setlocale(locale.LC_ALL, 'en_US.utf8')

Const.KIK_CONFIGURATION = Configuration(
    webhook = "%s:%d/%s" % (Const.KIK_API_CONFIG['WEBHOOK']['HOST'], Const.KIK_API_CONFIG['WEBHOOK']['PORT'], Const.KIK_API_CONFIG['WEBHOOK']['PATH']),
    features = Const.KIK_API_CONFIG['FEATURES']
)

kik = KikApi(
    Const.KIK_API_CONFIG['USERNAME'],
    Const.KIK_API_CONFIG['API_KEY']
)

kik.set_configuration(Const.KIK_CONFIGURATION)


#-- output what the hell kik is doing
print("\n\n\n# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #")
print("# -= Firing up KikBot: =- #")
print("# -= =-=-=-=-=-=-=-=-= =- #")
print("USERNAME : %s\nAPI_KEY  : %s\nHOST     : %s\nPORT     : %d\nPATH     : %s\nCONFIG   : %s" % (
    Const.KIK_API_CONFIG['USERNAME'],
    Const.KIK_API_CONFIG['API_KEY'],
    Const.KIK_API_CONFIG['WEBHOOK']['HOST'],
    Const.KIK_API_CONFIG['WEBHOOK']['PORT'],
    Const.KIK_API_CONFIG['WEBHOOK']['PATH'],
    kik.get_configuration().to_json()))
print("# -=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- #\n\n\n")



#-- url webhooks
application = tornado.web.Application([
    (r"/lmon8", Lmon8),
    (r"/user-notify", UserNotify),
])


#-- server starting
if __name__ == "__main__":
    application.listen(int(Const.KIK_API_CONFIG['WEBHOOK']['PORT']))
    tornado.ioloop.IOLoop.instance().start()
    print("tornado start" % (int(time.time())))
