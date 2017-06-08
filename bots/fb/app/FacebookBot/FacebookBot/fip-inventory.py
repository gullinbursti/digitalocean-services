#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import json
import random
import re
import time

from urllib import quote

import MySQLdb as mdb
import requests

from bs4 import BeautifulSoup


DB_HOST = "external-db.s4086.gridserver.com"
DB_NAME = "db4086_modd"
DB_USER = "db4086_modd_usr"
DB_PASS = "f4zeHUga.age"


def fetch(profile_id=76561198277603515):
    # print("fetch(profile_id={profile_id})".format(profile_id=profile_id))

    # -- existing inventory
    prev_inv = {}
    conn = mdb.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME)
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `market_id`, `max_buy`, `min_sell` FROM `flip_inventory` GROUP BY `name`;')

            for i in xrange(0, cur.rowcount):
                row = cur.fetchone()
                prev_inv[row['name']] = row

    except mdb.Error, e:
        print("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    else:
        if conn:
            conn.close()

    # -- current inventory
    response = requests.get("http://steamcommunity.com/inventory/76561198277603515/570/2", data=json.dumps({'l': "english"}))
    desc_obj = response.json()['descriptions']
    print("TOTAL: %d" % (len(response.json()['assets'])))

    # -- build asset info
    inventory = {}
    for asset in response.json()['descriptions']:
        print("Asset (%03d/%03d) - %s" % ((len(inventory) + 1), len(desc_obj), asset['market_name'].encode('utf-8')))
        market_id = "0"
        max_buy = 0.00
        min_sell = 0.00

        # -- check against existing inventory
        if asset['market_name'] not in prev_inv:
            # -- check if its already been recorded
            if asset['market_name'].encode('utf-8') not in [value['name'] for key, value in inventory.items()]:
                delay = random.gauss(45, 5)
                print("ADDING NEW ITEM AFTER {delay:.2f}s -- {market_name}".format(delay=delay, market_name=asset['market_name'].encode('utf-8')))
                time.sleep(delay)
                # -- get max buy / min sell price
                r = requests.get("http://steamcommunity.com/market/listings/730/%s" % (quote(asset['market_name'].encode('utf-8'))))

                # -- skip if error
                soup = BeautifulSoup(r.text, 'html.parser')
                if soup.h2 is not None and re.search(r'^Error$', soup.h2.string) is not None:
                    print("Error getting %s - %s" % (r.request.url, soup.h3.string))
                    continue

                # -- check for id
                if re.search(r'Market_LoadOrderSpread\(\ (\d+)\ \)\;\t', r.text) is not None:
                    market_id = int(re.findall(r'Market_LoadOrderSpread\(\ (\d+)\ \)\;\t', r.text)[0])
                    params = {
                        'query'      : "",
                        'start'      : 0,
                        'count'      : 10,
                        'country'    : "US",
                        'language'   : "english",
                        'currency'   : 1,
                        'item_nameid': market_id
                    }
                    r = requests.get("http://steamcommunity.com/market/itemordershistogram", params=params)
                    max_buy = int(r.json()['highest_buy_order'] or 0.00) * 0.01
                    min_sell = int(r.json()['lowest_sell_order'] or 0.00) * 0.01

            # -- copy prev
            else:
                min_sell = [value['min_sell'] for key, value in inventory.items() if value['name'] == asset['market_name'].encode('utf-8')][0]
                max_buy = [value['max_buy'] for key, value in inventory.items() if value['name'] == asset['market_name'].encode('utf-8')][0]

        else:
            market_id = prev_inv[asset['market_name']]['market_id']
            max_buy = prev_inv[asset['market_name']]['max_buy']
            min_sell = prev_inv[asset['market_name']]['min_sell']

        # -- build asset obj
        key = "%s_%s" % (asset['classid'], asset['instanceid'])
        inventory[key] = {
            'app_id'     : asset['appid'],
            'class_id'   : asset['classid'].encode('utf-8'),
            'instance_id': asset['instanceid'].encode('utf-8'),
            'asset_id'   : "",
            'market_id'  : market_id,
            'name'       : asset['market_name'].encode('utf-8'),
            'description': "" if len(asset['descriptions']) < 3 else asset['descriptions'][2]['value'].encode('utf-8'),
            'icon_url'   : "http://steamcommunity-a.akamaihd.net/economy/image/%s" % (asset['icon_url'].encode('utf-8')),
            'image_url'  : "" if 'icon_url_large' not in asset else "http://steamcommunity-a.akamaihd.net/economy/image/%s" % (asset['icon_url_large'].encode('utf-8')),
            'quantity'   : 0,
            'max_buy'    : max_buy,
            'min_sell'   : min_sell,
            'tradable'   : asset['tradable']
        }

    # -- loop thru them
    for asset in response.json()['assets']:
        key = "%s_%s" % (asset['classid'], asset['instanceid'])
        if key in inventory:
            # -- assign asset id
            inventory[key]['asset_id'] = asset['assetid'].encode('utf-8')

            # -- inc the quantity
            inventory[key]['quantity'] += 1

    return inventory


def update_db(inventory):
    # print("update_db(inventory={inventory})".format(inventory=inventory))

    # -- output current item quantities
    for key, value in inventory.iteritems():
        print("%s (%d)" % (value['name'], value['quantity']))

    conn = mdb.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME);
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('UPDATE `flip_inventory` SET `quantity` = 0 WHERE `quantity` > 0;')
            conn.commit()

            # -- loop thru
            for key, value in inventory.iteritems():
                cur.execute('SET NAMES utf8;')
                cur.execute('SET CHARACTER SET utf8;')
                cur.execute('SELECT `asset_id` FROM `flip_inventory` WHERE `asset_id` = %s LIMIT 1;', (value['asset_id'],))
                row = cur.fetchone()

                if row is None and value['quantity'] > 0:
                    cur.execute('INSERT INTO `flip_inventory` (`id`, `name`, `game_name`, `description`, `asset_id`, `app_id`, `class_id`, `instance_id`, `market_id`, `icon_url`, `image_url`, `quantity`, `max_buy`, `min_sell`, `tradable`, `updated`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(), UTC_TIMESTAMP());', (value['name'], "Dota 2", value['description'], value['asset_id'], value['app_id'], value['class_id'], value['instance_id'], value['market_id'], value['icon_url'], value['image_url'], value['quantity'], value['max_buy'], value['min_sell'], value['tradable']))

                else:
                    cur.execute('UPDATE `flip_inventory` SET `quantity` = %s, `max_buy` = %s, `min_sell` = %s, `tradable` = %s, `updated` = UTC_TIMESTAMP() WHERE `asset_id` = %s LIMIT 1;', (value['quantity'], value['max_buy'], value['min_sell'], value['tradable'], value['asset_id']))
                conn.commit()

                # -- update types for certain criteria
                cur.execute('UPDATE `flip_inventory` SET `type` = 3, `tradable` = 1 WHERE `min_sell` >= 3 AND `min_sell` <= 10 AND `type` = 1;')
                # if value['name'] in giveaway_items:
                #    cur.execute('UPDATE `flip_inventory` SET `type` = 2, `tradable` = 0 WHERE `name` = %s LIMIT 1;', (value['name']))
                cur.execute('UPDATE `flip_inventory` SET `type` = 10, `tradable` = 0 WHERE `min_sell` >= 16.00 AND `type` = 1;')
                conn.commit()

                # -- redo the condensed table
                cur.execute('DROP TABLE IF EXISTS `flip_items`;')
                cur.execute('CREATE TABLE `flip_items` (`id` INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY) AS SELECT `type` AS `type_id`, `name` AS `asset_name`, `description`, `game_name`, `image_url`, `icon_url`, SUM(`quantity`) AS `quantity`, `min_sell` AS `price`, `enabled`, UTC_TIMESTAMP() AS `updated`, UTC_TIMESTAMP() AS `added` FROM `flip_inventory` WHERE `quantity` > 0 GROUP BY `name` ORDER BY `added`;')
                conn.commit()

    except mdb.Error, e:
        print("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    else:
        if conn:
            conn.close()


# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


# -- get latest inventory
update_db(fetch())

