#!/usr/bin/env python
# -*- coding: UTF-8 -*-


from proxy_utils import product_for_id, products_for_storefront, storefront_for_id, storefronts_for_user, subscription_for_id, subscriptions_for_product, subscriptions_for_storefront
from models import logger


def disable_subscriptions(subscription_id=-1, product_id=-1, storefront_id=-1):
    logger.info("disable_subscriptions(subscription_id={subscription_id}, product_id={product_id}, storefront_id={storefront_id})".format(subscription_id=subscription_id, product_id=product_id, storefront_id=storefront_id))

    subscriptions = []
    if storefront_id != -1:
        storefront = storefront_for_id(storefront_id)

        for subscription in subscriptions_for_storefront(storefront.id)['results']:
            subscriptions.append(subscription)

    if product_id != -1:
        for subscription in subscriptions_for_product(product_id):
            subscriptions.append(subscription)

    if subscription_id != -1:
        subscriptions.append(subscription_for_id(subscription_id))

    logger.info(":::: DISABLING SUBSCRIPTIONS:\n%s" % ("\n".join(subscriptions)))


def disable_products(product_id=-1, storefront_id=-1):
    logger.info("disable_products(product_id={product_id}, storefront_id={storefront_id})".format(product_id=product_id, storefront_id=storefront_id))

    products = []
    if storefront_id != -1:
        for product in products_for_storefront(storefront_id):
            disable_subscriptions(product_id=product_id)
            products.append(product)

    if product_id != -1:
        disable_subscriptions(product_id=product_id)
        products.append(product_for_id(product_id))

    logger.info(":::: DISABLING PRODUCTS:\n%s" % ("\n".join(products)))


def disable_storefronts(storefront_id=-1):
    logger.info("disable_storefronts(storefront_id={storefront_id})".format(storefront_id=storefront_id))

    storefronts = []
    if storefront_id != -1:
        for storefront in storefront_for_id(storefront_id):
            disable_products(storefront_id=storefront.id)
            disable_subscriptions(storefront_id=storefront_id)
            storefronts.append(storefront)

    logger.info(":::: DISABLING STOREFRONTS:\n%s" % ("\n".join(storefronts)))

