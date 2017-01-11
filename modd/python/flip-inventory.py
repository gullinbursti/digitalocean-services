#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import json
from urllib import quote

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
        key = "%s_%s" % (asset['classid'].encode('utf-8'), asset['instanceid'].encode('utf-8'))
        inventory[key] = {
            'key'       : key,
            'name'      : asset['name'].encode('utf-8'),
            'image_url' : "http://steamcommunity-a.akamaihd.net/economy/image/%s" % (asset['icon_url_large']).encode('utf-8'),
            'quantity'  : 0
        }

    for asset in response.json()['assets']:
        key = "%s_%s" % (asset['classid'].encode('utf-8'), asset['instanceid'].encode('utf-8'))
        inventory[key]['quantity'] += 1

    return inventory


def update_db(inventory):
    #print("update_db(inventory={inventory})".format(inventory=inventory))

    for key, value in inventory.iteritems():
        print("%s (%d)" % (value['name'], value['quantity']))


    try:
        conn = mdb.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME);
        with conn:
            cur = conn.cursor()

            for key, value in inventory.iteritems():
                # print("Name: %s" % (val[name].encode('utf-8')))
                cur.execute('SET NAMES utf8;')
                cur.execute('SET CHARACTER SET utf8;');
                cur.execute('SELECT `id` FROM `flip_inventory` WHERE `steam_id` = "{steam_id}" LIMIT 1;'.format(steam_id=key))
                row = cur.fetchone()

                if row is None:
                    cur.execute('INSERT IGNORE INTO `flip_inventory` (`id`, `name`, `image_url`, `steam_id`, `quantity`, `added`) VALUES (NULL, "{name}", "{image_url}", "{steam_id}", {quantity}, NOW());'.format(name=value['name'], image_url=value['image_url'], steam_id=key, quantity=value['quantity']))

                else:
                    cur.execute('UPDATE `flip_inventory` SET `quantity` = {quantity} WHERE `id` = {asset_id} LIMIT 1;'.format(quantity=value['quantity'], asset_id=row[0]))
            conn.commit()

    except mdb.Error, e:
        print("MySqlError ({errno}): {errstr}".format(errno=e.args[0], errstr=e.args[1]))

    else:
        if conn:
            conn.close()


update_db(fetch())
