from named_constants import Constants

class Const(Constants):

    DB_HOST = 'external-db.s4086.gridserver.com'
    DB_NAME = 'db4086_modd'
    DB_USER = 'db4086_modd_usr'
    DB_PASS = 'f4zeHUga.age'

    VERIFY_TOKEN = "d41d8cd98f00b204e9800998ecf8427e"
    ACCESS_TOKEN = "EAAXFDiMELKsBAESoNb9hvGcOarJZCSuHJOQCjC835GS1QwwlOn8D255xPF86We1Wxg4DtxQqr91aHFYjFoOybUOVBTdtDalFKNLcjA2EXTEIGHXEMRbsA4vghEWKiIpB6nbzsX6G5rYBZCHuBc1UlsUnOqwZAS2jY56xppiIgZDZD"

    ADMIN_FB_PSID = "1298454546880273"#894483894011953

    # FLIP_CLAIM_URL = "www.gamebots.chat/giveaway.html"
    FLIP_CLAIM_URL = "taps.io/gamebotsc"
    FLIP_WIN_TEXT = "WINNER!\nYou won {item_name}.\n\nEnter your Steam Trade URL now."

    TRADE_URL_PURCHASE = "TRADE_URL_PURCHASE"
    TRADE_URL_FLIP_ITEM = "TRADE_URL_FLIP_ITEM"

    FLIP_COIN_START_GIF_URL = "http://i.imgur.com/C6Pgtf4.gif"
    FLIP_COIN_WIN_GIF_URL = "http://i.imgur.com/9fmZntz.gif"
    FLIP_COIN_LOSE_GIF_URL = "http://i.imgur.com/7YNujdq.gif"
    SHARE_IMAGE_URL = "https://pbs.twimg.com/profile_images/840610720563642368/p5TfHdUP_400x400.jpg"

    GA_TRACKING_ID = "UA-79705534-3"
    GA_TRACKING_URL = "http://www.google-analytics.com/collect"

    SESSION_STATE_UNKNOWN                 = -1
    SESSION_STATE_NEW_USER                = 0
    SESSION_STATE_HOME                    = 1
    SESSION_STATE_FLIPPING                = 2
    SESSION_STATE_FLIP_TRADE_URL          = 3
    SESSION_STATE_FLIP_LMON8_URL          = 4

    SESSION_STATE_DAILY_ITEM              = 10
    SESSION_STATE_CHECKOUT_ITEM           = 11
    SESSION_STATE_PURCHASE_ITEM           = 12
    SESSION_STATE_PURCHASED_ITEM          = 13
    SESSION_STATE_PURCHASED_TRADE_URL     = 14

    PAYLOAD_TYPE_QUICK_REPLY = "PAYLOAD_TYPE_QUICK_REPLY"
    PAYLOAD_TYPE_POSTBACK = "PAYLOAD_TYPE_POSTBACK"
    PAYLOAD_TYPE_ATTACHMENT = "PAYLOAD_TYPE_ATTACHMENT"
    PAYLOAD_TYPE_OTHER = "PAYLOAD_TYPE_OTHER"


    PAYLOAD_ATTACHMENT_TEXT = "PAYLOAD_ATTACHMENT-text"
    PAYLOAD_ATTACHMENT_IMAGE = "PAYLOAD_ATTACHMENT-image"
    PAYLOAD_ATTACHMENT_VIDEO = "PAYLOAD_ATTACHMENT-video"
    PAYLOAD_ATTACHMENT_URL = "PAYLOAD_ATTACHMENT-url"
    PAYLOAD_ATTACHMENT_FALLBACK = "PAYLOAD_ATTACHMENT-fallback"
    PAYLOAD_ATTACHMENT_OTHER = "PAYLOAD_ATTACHMENT-OTHER"

    APPNEXT_REPLIES = "f1xgb"
    MAIN_MENU_REPLIES = "menu|main menu|menu|mainmenu|home"
    UPLOAD_REPLIES = "giveaway|mod|upload"
    OPT_OUT_REPLIES = "optout|quit|end|stop|exit"
