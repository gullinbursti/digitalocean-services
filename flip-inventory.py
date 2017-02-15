# -*- coding: UTF-8 -*-

import json

import MySQLdb as mdb
import requests


DB_HOST = "external-db.s4086.gridserver.com"
DB_NAME = "db4086_modd"
DB_USER = "db4086_modd_usr"
DB_PASS = "f4zeHUga.age"


def fetch(profile_id=76561198277603515):
    #print("fetch(profile_id={profile_id})".format(profile_id=profile_id))

    response = requests.get("http://steamcommunity.com/inventory/76561198277603515/730/2", data=json.dumps({ 'l' : "english" }))
    print("TOTAL: %d" % (len(response.json()['assets'])))

    inventory = {}
    for asset in response.json()['descriptions']:
        #if asset['tradable'] == "1":
            key = "%s_%s" % (asset['classid'], asset['instanceid'])
            inventory[key] = {
                'app_id'      : asset['appid'],
                'class_id'    : asset['classid'],
                'instance_id' : asset['instanceid'],
                'name'        : asset['market_name'].encode('utf-8'),
                'description' : asset['descriptions'][2]['value'].encode('utf-8'),
                'icon_url'    : "http://steamcommunity-a.akamaihd.net/economy/image/%s" % (asset['icon_url']),
                'image_url'   : "http://steamcommunity-a.akamaihd.net/economy/image/%s" % (asset['icon_url_large']),
                'quantity'    : 0
            }

    for asset in response.json()['assets']:
        key = "%s_%s" % (asset['classid'], asset['instanceid'])
        if key in inventory:
            if 'asset_id' not in inventory[key]:
              inventory[key]['asset_id'] = asset['assetid']
            inventory[key]['quantity'] += 1

    return inventory


def update_db(inventory):
    #print("update_db(inventory={inventory})".format(inventory=inventory))

    for key, value in inventory.iteritems():
        print("%s (%d)" % (value['name'], value['quantity']))

    try:
        conn = mdb.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME);
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)

            for key, value in inventory.iteritems():
                # print("Name: %s" % (val[name].encode('utf-8')))

                cur.execute('SET NAMES utf8;')
                cur.execute('SET CHARACTER SET utf8;');
                cur.execute('SELECT `asset_id` FROM `flip_inventory` WHERE `asset_id` = "{asset_id}" LIMIT 1;'.format(asset_id=value['asset_id']))
                row = cur.fetchone()

                if row is None:
                    if value['quantity'] > 0:
                        cur.execute('INSERT IGNORE INTO `flip_inventory` (`id`, `name`, `description`, `asset_id`, `app_id`, `class_id`, `instance_id`, `icon_url`, `image_url`, `quantity`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW());', (value['name'], value['description'], value['asset_id'], value['app_id'], value['class_id'], value['instance_id'], value['icon_url'], value['image_url'], value['quantity']))
                        conn.commit()

                else:
                    cur.execute('UPDATE `flip_inventory` SET `quantity` = {quantity} WHERE `asset_id` = {asset_id} LIMIT 1;'.format(quantity=value['quantity'], asset_id=value['asset_id']))
                cur.execute('UPDATE `flip_inventory` SET `type` = 2 WHERE `name` LIKE "AK%Frontside%";')

            conn.commit()

    except mdb.Error, e:
        print("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    else:
        if conn:
            conn.close()


update_db(fetch())