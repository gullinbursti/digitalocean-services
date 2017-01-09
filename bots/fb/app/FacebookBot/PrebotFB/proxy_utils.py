#!/usr/bin/env python
# -*- coding: UTF-8 -*-


from models import logger
from data import Customer, MessageStatus, Product, Storefront, Subscription


def product_for_id(product_id, creation_state=4, enabled=True):
    logger.info("product_for_id(product_id={product_id}, creation_state={creation_state}, enabled={enabled})".format(product_id=product_id))
    return [Product.query.filter(Product.id == product_id).first()]


def products_for_storefront(storefront_id, creation_state=4, enabled=True):
    logger.info("products_for_storefront(storefront_id={storefront_id}, creation_state={creation_state}, enabled={enabled})".format(storefront_id=storefront_id, creation_state=creation_state, enabled=enabled))

    # products = {
    #     'query' : Product.query.filter(Product.storefront_id == storefront_id).filter(Product.creation_state == creation_state).filter(Product.enabled == enabled),
    #     'results' : [],
    #     'params' : {
    #         'storefront_id' : storefront_id,
    #         'creation_state' : creation_state,
    #         'enabled' : enabled
    #     }
    # }
    products = []
    for product in Product.query.filter(Product.storefront_id == storefront_id).filter(Product.creation_state == creation_state).filter(Product.enabled == enabled):
        products.append(product)
        #products['results'].append(product)


    logger.info(":::: PRODUCTS for (%s) -->\n%s" % (Storefront.query.filter(Storefront.id == storefront_id).order_by(Storefront.added.desc()).first().display_name, "\n".join(products)))
    return products


def products_for_user(recipient_id, creation_state=4, enabled=True):
    logger.info("products_for_user(recipient_id={recipient_id}, creation_state={creation_state}, enabled={enabled})".format(recipient_id=recipient_id))

    # products = {
    #     'query' : Product.query.filter(Product.fb_psid == recipient_id).filter(Product.creation_state == creation_state).filter(Product.enabled == enabled),
    #     'results' : [],
    #     'params' : {
    #         'recipient_id' : recipient_id,
    #         'creation_state' : creation_state,
    #         'enabled' : enabled
    #     }
    # }
    products = []
    for product in Product.query.filter(Product.fb_psid == recipient_id).filter(Product.creation_state == creation_state).filter(Product.enabled == enabled):
        products.append(product)
        # products['results'].append(product)

    logger.info(":::: PRODUCTS for (%s) --> (creation_state=%d, enabled=%s):\n%s" % (recipient_id, creation_state, enabled, "\n".join(products)))
    return products


def storefront_for_id(storefront_id, creation_state=4, enabled=True):
    logger.info("storefront_for_id(storefront_id={storefront_id}, creation_state={creation_state}, enabled={enabled})".format(storefront_id=storefront_id))
    return [Storefront.query.filter(Storefront.id == storefront_id).first()]


def storefronts_for_user(recipient_id, creation_state=4, enabled=True):
    logger.info("storefronts_for_user(recipient_id={recipient_id}, creation_state={creation_state}, enabled={enabled})".format(recipient_id=recipient_id))

    # storefronts = {
    #     'query' : Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == creation_state).filter(enabled == enabled).order_by(Storefront.added.desc()),
    #     'results' : [],
    #     'params' : {
    #         'recipient_id' : recipient_id,
    #         'creation_state' : creation_state,
    #         'enabled' : enabled
    #     }
    # }
    storefronts = []
    for storefront in Storefront.query.filter(Storefront.fb_psid == recipient_id).filter(Storefront.creation_state == creation_state).filter(Storefront.enabled == enabled).order_by(Storefront.added.desc()):
        storefronts.append(storefront)
        # storefronts['results'].append(storefront)

    logger.info(":::: STOREFRONTS for (%s) --> (creation_state=%d, enabled=%s):\n%s" % (recipient_id, creation_state, enabled, "\n".join(storefronts)))
    return storefronts

def subscription_for_id(subscription_id, enabled=True):
    logger.info("subscription_for_id(subscription_id={subscription_id}, enabled={enabled})".format(subscription_id=subscription_id))
    return [Subscription.query.filter(Subscription.id == subscription_id).first()]


def subscriptions_for_product(product_id, enabled=True):
    logger.info("subscriptions_for_product(product_id={product_id}, enabled={enabled})".format(product_id=product_id, enabled=enabled))

    # subscriptions = {
    #     'query' : Subscription.query.filter(Subscription.product_id == product_id).filter(Product.enabled == enabled),
    #     'results' : [],
    #     'params' : {
    #         'product_id' : product_id,
    #         'enabled' : enabled
    #     }
    # }
    subscriptions = []
    for subscription in Subscription.query.filter(Subscription.product_id == product_id).filter(Subscription.enabled == enabled):
        subscriptions.append(subscription)
        # subscriptions['results'].append(subscription)

    logger.info(":::: SUBSCRIPTIONS for (%s) -->\n%s" % (product_id, "\n".join(subscriptions)))
    return subscriptions


def subscriptions_for_storefront(storefront_id, enabled=True):
    logger.info("subscriptions_for_storefront(storefront_id={storefront_id}, enabled={enabled})".format(storefront_id=storefront_id, enabled=enabled))

    # subscriptions = {
    #     'query' : Subscription.query.filter(Subscription.storefront_id == storefront_id).filter(Product.enabled == enabled),
    #     'results' : [],
    #     'params' : {
    #         'storefront_id' : storefront_id,
    #         'enabled' : enabled
    #     }
    # }
    subscriptions = []
    for subscription in Subscription.query.filter(Subscription.storefront_id == storefront_id).filter(Subscription.enabled == enabled):
        subscriptions.append(subscription)
        # subscriptions['results'].append(subscription)

    logger.info(":::: SUBSCRIPTIONS for (%s) -->\n%s" % (Storefront.query.filter(Storefront.id == storefront_id).order_by(Storefront.added.desc()).first().display_name, "\n".join(subscriptions)))
    return subscriptions


def subscriptions_for_user(recipient_id, enabled=True):
    logger.info("subscriptions_for_user(recipient_id={recipient_id}, enabled={enabled})".format(recipient_id=recipient_id, enabled=enabled))

    # subscriptions = {
    #     'query' : Subscription.query.filter(Subscription.storefront_id == storefront_id).filter(Product.enabled == enabled),
    #     'results' : [],
    #     'params' : {
    #         'storefront_id' : storefront_id,
    #         'enabled' : enabled
    #     }
    # }
    subscriptions = []
    for subscription in Subscription.query.filter(Subscription.fb_psid == recipient_id).filter(Subscription.enabled == enabled):
        subscriptions.append(subscription)
        # subscriptions['results'].append(subscription)

    logger.info(":::: SUBSCRIPTIONS for (%s) -->\n%s" % (recipient_id, "\n".join(subscriptions)))
    return subscriptions