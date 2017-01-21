from named_constants import Constants

class Const(Constants):
    VERIFY_TOKEN = "AC7F552BD16A775B653F6EF6CD3902E6"
    ACCESS_TOKEN = "EAADzAMIzYPEBAJGk5P18ibMeEBhhdvUzZBsMoItnuB19PEzUGnNZALX5MN1rK0HKEfSG4YsmyVM2NmeK3m9wcmDvmwoB97aqfn1U0KOdvNtv6ZCgPLvqPFr2YbnlinuUUSrPtnphqafj6ad73wIPVBCOhCaiLGfvEZCUr7CxcAZDZD"

    WEB_SERVER_IP = "192.241.212.32"

    MYSQL_HOST = '138.197.216.56'
    MYSQL_NAME = 'prebot_marketplace'
    MYSQL_USER = 'pre_usr'
    MYSQL_PASS = 'f4zeHUga.age'

    STRIPE_DEV_API_KEY = "sk_test_3QTHaM9IjN2g3AI91Gqqaoxo"
    STRIPE_LIVE_API_KEY = "sk_live_XhtvWeK1aZ1ggqLrJ4Z0SOZZ"

    ORTHODOX_GREETING = "Welcome to Pre. The fastest way to sell in chat."
    GOODBYE_MESSAGE = "Ok, Thanks. Goodbye!"
    UNKNOWN_MESSAGE = "I'm sorry, I cannot understand that type of message."

    IMAGE_URL_CREATE_STOREFRONT = "https://i.imgur.com/Mr5nLPv.png"
    IMAGE_URL_REMOVE_STOREFRONT = "https://i.imgur.com/za3e16d.png"
    IMAGE_URL_ADD_PRODUCT = "https://i.imgur.com/nItiQnP.png"
    IMAGE_URL_SHARE_STOREFRONT = "https://i.imgur.com/UWPgP6N.png"
    IMAGE_URL_MARKETPLACE = "https://i.imgur.com/v2yFGAJ.png"
    IMAGE_URL_NOTIFY_SUBSCRIBERS = "https://i.imgur.com/zFlsVGN.png"
    IMAGE_URL_SUPPORT = "https://i.imgur.com/tQ9mBeG.png"

    MARKETPLACE_GREETING = 'MARKETPLACE_GREETING'
    STOREFRONT_ADMIN = 'STOREFRONT_ADMIN'
    CUSTOMER_EMPTY = 'CUSTOMER_EMPTY'
    CUSTOMER_REFERRAL = 'CUSTOMER_REFERRAL'
    CUSTOMER_STOREFRONT = 'CUSTOMER_STOREFRONT'
    CUSTOMER_PRODUCT = 'CUSTOMER_PRODUCT'

    CARD_TYPE_STOREFRONT = 'CARD_STOREFRONT'
    CARD_TYPE_STOREFRONT_PREVIEW = 'CARD_STOREFRONT_PREVIEW'
    CARD_TYPE_STOREFRONT_SHARE = 'CARD_STOREFRONT_SHARE'
    CARD_TYPE_PRODUCT = 'CARD_PRODUCT'
    CARD_TYPE_PRODUCT_PREVIEW = 'CARD_PRODUCT_PREVIEW'
    CARD_TYPE_PRODUCT_SHARE = 'CARD_PRODUCT_SHARE'
    CARD_TYPE_PRODUCT_PURCHASE = 'CARD_PRODUCT_PURCHASE'
    CARD_TYPE_PRODUCT_CHECKOUT = 'CARD_PRODUCT_CHECKOUT'
    CARD_TYPE_PRODUCT_RECEIPT = 'CARD_PRODUCT_RECEIPT'
    CARD_TYPE_SUPPORT = 'CARD_SUPPORT'
    CARD_TYPE_NOTIFY_SUBSCRIBERS = 'CARD_NOTIFY_SUBSCRIBERS'


    CARD_BTN_POSTBACK = 'postback'
    CARD_BTN_URL = 'web_url'
    CARD_BTN_INVITE = 'element_share'
    KWIK_BTN_TEXT = 'text'
    KWIK_BTN_LOCATION = 'location'

    PB_PAYLOAD_ORTHODOX = 'ORTHODOX_PAYLOAD'
    PB_PAYLOAD_GREETING = 'WELCOME_MESSAGE'

    PB_PAYLOAD_PAYMENT_YES = 'PAYMENT_YES'
    PB_PAYLOAD_PAYMENT_NO = 'PAYMENT_NO'
    PB_PAYLOAD_PAYMENT_CANCEL = 'PAYMENT_CANCEL'

    PB_PAYLOAD_CREATE_STOREFRONT = 'CREATE_STOREFRONT'
    PB_PAYLOAD_DELETE_STOREFRONT = 'DELETE_STOREFRONT'
    PB_PAYLOAD_SUBMIT_STOREFRONT = 'SUBMIT_STOREFRONT'
    PB_PAYLOAD_REDO_STOREFRONT = 'REDO_STOREFRONT'
    PB_PAYLOAD_CANCEL_STOREFRONT = 'CANCEL_STOREFRONT'

    PB_PAYLOAD_ADD_PRODUCT = 'ADD_PRODUCT'
    PB_PAYLOAD_DELETE_PRODUCT = 'DELETE_PRODUCT'
    PB_PAYLOAD_SUBMIT_PRODUCT = 'SUBMIT_PRODUCT'
    PB_PAYLOAD_REDO_PRODUCT = 'REDO_PRODUCT'
    PB_PAYLOAD_CANCEL_PRODUCT = 'CANCEL_PRODUCT'

    PB_PAYLOAD_PRODUCT_RELEASE_NOW = 'PRODUCT_RELEASE_0_DAYS'
    PB_PAYLOAD_PRODUCT_RELEASE_30_DAYS = 'PRODUCT_RELEASE_30_DAYS'
    PB_PAYLOAD_PRODUCT_RELEASE_60_DAYS = 'PRODUCT_RELEASE_60_DAYS'
    PB_PAYLOAD_PRODUCT_RELEASE_90_DAYS = 'PRODUCT_RELEASE_90_DAYS'
    PB_PAYLOAD_PRODUCT_RELEASE_120_DAYS = 'PRODUCT_RELEASE_120_DAYS'

    PB_PAYLOAD_RESERVE_PRODUCT = 'RESERVE_PRODUCT'
    PB_PAYLOAD_CHECKOUT_PRODUCT = 'CHECKOUT_PRODUCT'
    PB_PAYLOAD_PURCHASE_PRODUCT = 'PURCHASE_PRODUCT'
    PB_PAYLOAD_SHARE_STOREFRONT = 'SHARE_STOREFRONT'
    PB_PAYLOAD_SHARE_PRODUCT = 'SHARE_PRODUCT'
    PB_PAYLOAD_VIEW_MARKETPLACE = 'VIEW_MARKETPLACE'
    PB_PAYLOAD_PRODUCT_VIDEO = 'PRODUCT_VIDEO'
    PB_PAYLOAD_SUPPORT = 'SUPPORT'
    PB_PAYLOAD_CUSTOMERS = 'CUSTOMERS'
    PB_PAYLOAD_NOTIFY_STOREFRONT_OWNER = 'NOTIFY_STOREFRONT_OWNER'
    PB_PAYLOAD_NOTIFY_SUBSCRIBERS = 'NOTIFY_SUBSCRIBERS'

    PB_PAYLOAD_STRIPE_PAYMENT = 'STRIPE_PAYMENT'

    RESERVED_ADMIN_REPLIES = "admin"
    RESERVED_SHOP_REPLIES = "main|main menu|menu"
    RESERVED_SUPPORT_REPLIES = "help|support"
    RESERVED_STOP_REPLIES = "cancel|end|quit|stop"
