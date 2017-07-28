#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import csv
import hashlib
import json
import locale
import logging
import os
import random
import re
import statistics
import sqlite3
import sys
import time

from itertools import cycle
from StringIO import StringIO
from urllib import urlencode

import MySQLdb as mdb
import pycurl
import requests
import urllib

from flask import Flask, request
from flask_cors import CORS, cross_origin

from constants import Const

reload(sys)
sys.setdefaultencoding('utf8')
locale.setlocale(locale.LC_ALL, 'en_US.utf8')

app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})

logger = logging.getLogger(__name__)
hdlr = logging.FileHandler('/var/log/FacebookBot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#


def bot_page_id(bot_type=Const.BOT_TYPE_GAMEBOTS):
    logger.info("bot_page_id(bot_type=%s)" % (bot_type,))

    if bot_type == Const.BOT_TYPE_CSGOSNAKE:
        return "150502195500410"

    elif bot_type == Const.BOT_TYPE_CSGOINACTIVE:
        return "1137364719696429"

    elif bot_type == Const.BOT_TYPE_AEROFAM420:
        return "151435755413505"

    elif bot_type == Const.BOT_TYPE_CSGOBEAST:
        return "105840016730443"

    elif bot_type == Const.BOT_TYPE_CSGOHAMZA:
        return "1377356212343407"

    elif bot_type == Const.BOT_TYPE_SPIN2WIN:
        return "487601868247073"

    elif bot_type == Const.BOT_TYPE_UNICORN:
        return "2118706424822220"

    elif bot_type == Const.BOT_TYPE_VASCO:
        return "120289931921105"

    elif bot_type == Const.BOT_TYPE_CSGOCASESONLY:
        return "1909048222640463"

    elif bot_type == Const.BOT_TYPE_LORDHELIX:
        return "846114605565458"

    elif bot_type == Const.BOT_TYPE_OZZNY09:
        return "1294517167327887"

    elif bot_type == Const.BOT_TYPE_FOSSYGFX:
        return "572994059757540"

    elif bot_type == Const.BOT_TYPE_REALCSGOFIRE:
        return "713601498840690"

    elif bot_type == Const.BOT_TYPE_JERRYXTC:
        return "1708313786130929"

    elif bot_type == Const.BOT_TYPE_TELLFULGAMES:
        return "1758274057804792"

    elif bot_type == Const.BOT_TYPE_LITSKINS:
        return "450482558669695"

    elif bot_type == Const.BOT_TYPE_SUFFERCSGO:
        return "146890799220773"

    elif bot_type == Const.BOT_TYPE_BOTWREK:
        return "660584334132524"

    elif bot_type == Const.BOT_TYPE_MAINGAME:
        return "325498671237787"

    elif bot_type == Const.BOT_TYPE_JAN:
        return "787325224762591"

    elif bot_type == Const.BOT_TYPE_ITSNANCY:
        return "331592810621913"

    elif bot_type == Const.BOT_TYPE_CSGOHOPE:
        return "772647349584673"



def bot_type_token(bot_type=Const.BOT_TYPE_GAMEBOTS):
    logger.info("bot_type_token(bot_type=%s)" % (bot_type,))

    if bot_type == Const.BOT_TYPE_GAMEBOTS:
        return Const.GAMEBOTS_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_GAMEBAE:
        return Const.GAMEBAE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_H1Z1:
        return Const.H1Z1_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_DOTA2:
        return Const.DOTA2_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOSPICE:
        return Const.CSGOSPICE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOBUNNY:
        return Const.CSGOBUNNY_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOBURRITO:
        return Const.CSGOBURRITO_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOPIZZA:
        return Const.CSGOPIZZA_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOSUSHI:
        return Const.CSGOSUSHI_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOSTONER:
        return Const.CSGOSTONER_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOBLAZE:
        return Const.CSGOBLAZE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_TAC0:
        return Const.TAC0_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_BSP:
        return Const.BSP_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_PAYDAY2:
        return Const.PAYDAY2_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_BALLISTICOVERKILL:
        return Const.BALLISTICOVERKILL_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_KILLINGFLOOR2:
        return Const.KILLINGFLOOR2_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_TF2:
        return Const.TF2_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_DOI:
        return Const.DOI_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CCZAR:
        return Const.CCZAR_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOHOMIE:
        return Const.CSGOHOMIE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOFNATIC:
        return Const.CSGOFNATIC_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOSK:
        return Const.CSGOSK_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOFAZE:
        return Const.CSGOFAZE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_SKINHUB:
        return Const.SKINHUB_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOJUICE:
        return Const.CSGOJUICE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOFADED:
        return Const.CSGOFADED_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOBOOM:
        return Const.CSGOBOOM_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOSMOKE:
        return Const.CSGOSMOKE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOFAST:
        return Const.CSGOFAST_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOFLASHY:
        return Const.CSGOFLASHY_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGONASTY:
        return Const.CSGONASTY_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOLOLZ:
        return Const.CSGOLOLZ_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOBEEF:
        return Const.CSGOBEEF_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOWILD:
        return Const.CSGOWILD_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOMASSIVE:
        return Const.CSGOMASSIVE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOCHAMP:
        return Const.CSGOCHAMP_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOCARTEL:
        return Const.CSGOCARTEL_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOMAFIA:
        return Const.CSGOMAFIA_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOMICKEY:
        return Const.CSGOMICKEY_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOBIGGIE:
        return Const.CSGOBIGGIE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGONUKE:
        return Const.CSGONUKE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOKANYE:
        return Const.CSGOKANYE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOPIE:
        return Const.CSGOPIE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOWHIP:
        return Const.CSGOWHIP_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOCRAY:
        return Const.CSGOCRAY_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOWU:
        return Const.CSGOWU_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOKNIFE:
        return Const.CSGOKNIFE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOFRAT:
        return Const.CSGOFRAT_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_MOBILELEGEND:
        return Const.MOBILELEGENDS_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOMISSY:
        return Const.CSGOMISSY_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOBRO:
        return Const.CSGOBRO_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOOF:
        return Const.CSGOOF_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGODADDY:
        return Const.CSGODADDY_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOABSTRACT:
        return Const.CSGOABSTRACT_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOBALLER:
        return Const.CSGOBALLER_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOBULLET:
        return Const.CSGOBULLET_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOTANK:
        return Const.CSGOTANK_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOCANDY:
        return Const.CSGOCANDY_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOFART:
        return Const.CSGOFART_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOREHAB:
        return Const.CSGOREHAB_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOFREE:
        return Const.CSGOFREE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOCASES:
        return Const.CSGOCASES_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOSNAKE:
        return Const.CSGOSNAKE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOINACTIVE:
        return Const.CSGOINACTIVE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_AEROFAM420:
        return Const.AEROFAM420_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOBEAST:
        return Const.CSGOBEAST_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOHAMZA:
        return Const.CSGOHAMZA_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_SPIN2WIN:
        return Const.SPIN2WIN_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_UNICORN:
        return Const.UNICORN_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_VASCO:
        return Const.VASCO_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOCASESONLY:
        return Const.CSGOCASESONLY_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_LORDHELIX:
        return Const.LORDHELIX_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_OZZNY09:
        return Const.OZZNY09_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_FOSSYGFX:
        return Const.FOSSYGFX_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_REALCSGOFIRE:
        return Const.REALCSGOFIRE_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_JERRYXTC:
        return Const.JERRYXTC_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_TELLFULGAMES:
        return Const.TELLFULGAMES_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_LITSKINS:
        return Const.LITSKINS_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_SUFFERCSGO:
        return Const.SUFFERCSGO_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_BOTWREK:
        return Const.BOTWREK_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_MAINGAME:
        return Const.MAINGAME_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_JAN:
        return Const.JAN_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_ITSNANCY:
        return Const.ITSNANCY_ACCESS_TOKEN

    elif bot_type == Const.BOT_TYPE_CSGOHOPE:
        return Const.CSGOHOPE_ACCESS_TOKEN

    # elif bot_type == Const.:
    #     return Const.



def bot_webhook_type(webhook):
    logger.info("bot_webhook_type(webhook=%s)" % (webhook,))

    if webhook == "gamebots":
        return Const.BOT_TYPE_GAMEBOTS

    elif webhook == "gamebae":
        return Const.BOT_TYPE_GAMEBAE

    elif webhook == "h1z1":
        return Const.BOT_TYPE_H1Z1

    elif webhook == "dota2":
        return Const.BOT_TYPE_DOTA2

    elif webhook == "csgospice":
        return Const.BOT_TYPE_CSGOSPICE

    elif webhook == "csgobunny":
        return Const.BOT_TYPE_CSGOBUNNY

    elif webhook == "csgoburrito":
        return Const.BOT_TYPE_CSGOBURRITO

    elif webhook == "csgopizza":
        return Const.BOT_TYPE_CSGOPIZZA

    elif webhook == "csgosushi":
        return Const.BOT_TYPE_CSGOSUSHI

    elif webhook == "csgostoner":
        return Const.BOT_TYPE_CSGOSTONER

    elif webhook == "csgoblaze":
        return Const.BOT_TYPE_CSGOBLAZE

    elif webhook == "tac0":
        return Const.BOT_TYPE_TAC0

    elif webhook == "battlecrew-space-pirates":
        return Const.BOT_TYPE_BSP

    elif webhook == "payday-2":
        return Const.BOT_TYPE_PAYDAY2

    elif webhook == "ballistic-overkill":
        return Const.BOT_TYPE_BALLISTICOVERKILL

    elif webhook == "killing-floor-2":
        return Const.BOT_TYPE_KILLINGFLOOR2

    elif webhook == "team-fortress-2":
        return Const.BOT_TYPE_TF2

    elif webhook == "day-of-infamy":
        return Const.BOT_TYPE_DOI

    elif webhook == "cczar":
        return Const.BOT_TYPE_CCZAR

    elif webhook == "csgohomie":
        return Const.BOT_TYPE_CSGOHOMIE

    elif webhook == "csgofnatic":
        return Const.BOT_TYPE_CSGOFNATIC

    elif webhook == "csgosk":
        return Const.BOT_TYPE_CSGOSK

    elif webhook == "csgofaze":
        return Const.BOT_TYPE_CSGOFAZE

    elif webhook == "skinhub":
        return Const.BOT_TYPE_SKINHUB

    elif webhook == "csgojuice":
        return Const.BOT_TYPE_CSGOJUICE

    elif webhook == "csgofaded":
        return Const.BOT_TYPE_CSGOFADED

    elif webhook == "csgoboom":
        return Const.BOT_TYPE_CSGOBOOM

    elif webhook == "csgosmoke":
        return Const.BOT_TYPE_CSGOSMOKE

    elif webhook == "csgofast":
        return Const.BOT_TYPE_CSGOFAST

    elif webhook == "csgoflashy":
        return Const.BOT_TYPE_CSGOFLASHY

    elif webhook == "csgonasty":
        return Const.BOT_TYPE_CSGONASTY

    elif webhook == "csgololz":
        return Const.BOT_TYPE_CSGOLOLZ

    elif webhook == "csgobeef":
        return Const.BOT_TYPE_CSGOBEEF

    elif webhook == "csgowild":
        return Const.BOT_TYPE_CSGOWILD

    elif webhook == "csgomassive":
        return Const.BOT_TYPE_CSGOMASSIVE

    elif webhook == "csgochamp":
        return Const.BOT_TYPE_CSGOCHAMP

    elif webhook == "csgocartel":
        return Const.BOT_TYPE_CSGOCARTEL

    elif webhook == "csgomafia":
        return Const.BOT_TYPE_CSGOMAFIA

    elif webhook == "csgomickey":
        return Const.BOT_TYPE_CSGOMICKEY

    elif webhook == "csgobiggie":
        return Const.BOT_TYPE_CSGOBIGGIE

    elif webhook == "csgonuke":
        return Const.BOT_TYPE_CSGONUKE

    elif webhook == "csgokanye":
        return Const.BOT_TYPE_CSGOKANYE

    elif webhook == "csgopie":
        return Const.BOT_TYPE_CSGOPIE

    elif webhook == "csgowhip":
        return Const.BOT_TYPE_CSGOWHIP

    elif webhook == "csgocray":
        return Const.BOT_TYPE_CSGOCRAY

    elif webhook == "csgowu":
        return Const.BOT_TYPE_CSGOWU

    elif webhook == "csgoknife":
        return Const.BOT_TYPE_CSGOKNIFE

    elif webhook == "csgofrat":
        return Const.BOT_TYPE_CSGOFRAT

    elif webhook == "mobile-legend":
        return Const.BOT_TYPE_MOBILELEGEND

    elif webhook == "csgomissy":
        return Const.BOT_TYPE_CSGOMISSY

    elif webhook == "csgobro":
        return Const.BOT_TYPE_CSGOBRO

    elif webhook == "csgomissy":
        return Const.BOT_TYPE_CSGOMISSY

    elif webhook == "csgoof":
        return Const.BOT_TYPE_CSGOOF

    elif webhook == "csgodaddy":
        return Const.BOT_TYPE_CSGODADDY

    elif webhook == "csgoabstract":
        return Const.BOT_TYPE_CSGOABSTRACT

    elif webhook == "csgoballer":
        return Const.BOT_TYPE_CSGOBALLER

    elif webhook == "csgobullet":
        return Const.BOT_TYPE_CSGOBULLET

    elif webhook == "csgotank":
        return Const.BOT_TYPE_CSGOTANK

    elif webhook == "csgocandy":
        return Const.BOT_TYPE_CSGOCANDY

    elif webhook == "csgofart":
        return Const.BOT_TYPE_CSGOFART

    elif webhook == "csgorehab":
        return Const.BOT_TYPE_CSGOREHAB

    elif webhook == "csgofree":
        return Const.BOT_TYPE_CSGOFREE

    elif webhook == "csgocases":
        return Const.BOT_TYPE_CSGOCASES

    elif webhook == "csgosnake":
        return Const.BOT_TYPE_CSGOSNAKE

    elif webhook == "csgoinactive":
        return Const.BOT_TYPE_CSGOINACTIVE

    elif webhook == "aerofam420":
        return Const.BOT_TYPE_AEROFAM420

    elif webhook == "csgobeast":
        return Const.BOT_TYPE_CSGOBEAST

    elif webhook == "csgohamza":
        return Const.BOT_TYPE_CSGOHAMZA

    elif webhook == "spin2win":
        return Const.BOT_TYPE_SPIN2WIN

    elif webhook == "unicorn":
        return Const.BOT_TYPE_UNICORN

    elif webhook == "vasco-gaming":
        return Const.BOT_TYPE_VASCO

    elif webhook == "csgo-cases-only":
        return Const.BOT_TYPE_CSGOCASESONLY

    elif webhook == "lord-helix":
        return Const.BOT_TYPE_LORDHELIX

    elif webhook == "ozzny09":
        return Const.BOT_TYPE_OZZNY09

    elif webhook == "fossy-gfx":
        return Const.BOT_TYPE_FOSSYGFX

    elif webhook == "real-csgo-fire":
        return Const.BOT_TYPE_REALCSGOFIRE

    elif webhook == "jerry-xtc":
        return Const.BOT_TYPE_JERRYXTC

    elif webhook == "tellful-games":
        return Const.BOT_TYPE_TELLFULGAMES

    elif webhook == "lit-skins":
        return Const.BOT_TYPE_LITSKINS

    elif webhook == "suffercsgo":
        return Const.BOT_TYPE_SUFFERCSGO

    elif webhook == "bot-wrek":
        return Const.BOT_TYPE_BOTWREK

    elif webhook == "maingame":
        return Const.BOT_TYPE_MAINGAME

    elif webhook == "jan":
        return Const.BOT_TYPE_JAN

    elif webhook == "its-nancy":
        return Const.BOT_TYPE_ITSNANCY

    elif webhook == "csgohope":
        return Const.BOT_TYPE_CSGOHOPE

    # elif webhook == "":
    #     return Const.BOT_TYPE_





def bot_title(bot_type=Const.BOT_TYPE_GAMEBOTS):
    logger.info("bot_title(bot_type=%s)" % (bot_type,))

    if bot_type == Const.BOT_TYPE_GAMEBOTS:
        return "Gamebots"

    elif bot_type == Const.BOT_TYPE_GAMEBAE:
        return "GameBAE"

    elif bot_type == Const.BOT_TYPE_H1Z1:
        return "H1Z1"

    elif bot_type == Const.BOT_TYPE_DOTA2:
        return "Dota2"

    elif bot_type == Const.BOT_TYPE_CSGOSPICE:
        return "CSGOSpice"

    elif bot_type == Const.BOT_TYPE_CSGOBUNNY:
        return "CSGOBunny"

    elif bot_type == Const.BOT_TYPE_CSGOBURRITO:
        return "CSGOBurrito"

    elif bot_type == Const.BOT_TYPE_CSGOPIZZA:
        return "CSGOPizza"

    elif bot_type == Const.BOT_TYPE_CSGOSUSHI:
        return "CSGOSushi"

    elif bot_type == Const.BOT_TYPE_CSGOSTONER:
        return "CSGOStoner"

    elif bot_type == Const.BOT_TYPE_CSGOBLAZE:
        return "CSGOBlaze"

    elif bot_type == Const.BOT_TYPE_TAC0:
        return "TAC0"

    elif bot_type == Const.BOT_TYPE_CCZAR:
        return "C-czar"

    elif bot_type == Const.BOT_TYPE_CSGOHOMIE:
        return "CSGOHomie"

    elif bot_type == Const.BOT_TYPE_CSGOFNATIC:
        return "CSGOFnatic"

    elif bot_type == Const.BOT_TYPE_CSGOSK:
        return "Csgosk"

    elif bot_type == Const.BOT_TYPE_CSGOFAZE:
        return "CSGOFaZe"

    elif bot_type == Const.BOT_TYPE_SKINHUB:
        return "SkinHub"

    elif bot_type == Const.BOT_TYPE_CSGOJUICE:
        return "CSGOJuice"

    elif bot_type == Const.BOT_TYPE_CSGOFADED:
        return "CSGOFaded"

    elif bot_type == Const.BOT_TYPE_CSGOBOOM:
        return "CSGOBoom"

    elif bot_type == Const.BOT_TYPE_CSGOSMOKE:
        return "CSGOSmoke"

    elif bot_type == Const.BOT_TYPE_CSGOFAST:
        return "CSGOFast"

    elif bot_type == Const.BOT_TYPE_CSGOFLASHY:
        return "CSGOFlashy"

    elif bot_type == Const.BOT_TYPE_CSGONASTY:
        return "CSGONasty"

    elif bot_type == Const.BOT_TYPE_CSGOLOLZ:
        return "CSGOlolz"

    elif bot_type == Const.BOT_TYPE_CSGOBEEF:
        return "CSGOBeef"

    elif bot_type == Const.BOT_TYPE_CSGOWILD:
        return "CSGOWild"

    elif bot_type == Const.BOT_TYPE_CSGOMASSIVE:
        return "CSGOMassive"

    elif bot_type == Const.BOT_TYPE_CSGOCHAMP:
        return "CSGOChamp"

    elif bot_type == Const.BOT_TYPE_CSGOCARTEL:
        return "CSGOCartel"

    elif bot_type == Const.BOT_TYPE_CSGOMAFIA:
        return "CSGOMafia"

    elif bot_type == Const.BOT_TYPE_CSGOMICKEY:
        return "CSGOMickey"

    elif bot_type == Const.BOT_TYPE_CSGOBIGGIE:
        return "CSGOBiggie"

    elif bot_type == Const.BOT_TYPE_CSGONUKE:
        return "CSGONuke"

    elif bot_type == Const.BOT_TYPE_CSGOKANYE:
        return "CSGOKanye"

    elif bot_type == Const.BOT_TYPE_CSGOPIE:
        return "CSGOPie"

    elif bot_type == Const.BOT_TYPE_CSGOWHIP:
        return "CSGOWhip"

    elif bot_type == Const.BOT_TYPE_CSGOCRAY:
        return "CSGOCray"

    elif bot_type == Const.BOT_TYPE_CSGOWU:
        return "CSGOWu"

    elif bot_type == Const.BOT_TYPE_CSGOKNIFE:
        return "CSGOKnife"

    elif bot_type == Const.BOT_TYPE_CSGOFRAT:
        return "CSGOFrat"

    elif bot_type == Const.BOT_TYPE_MOBILELEGEND:
        return "Mobile Legend"

    elif bot_type == Const.BOT_TYPE_CSGOMISSY:
        return "CSGOMissy"

    elif bot_type == Const.BOT_TYPE_CSGOBRO:
        return "CSGOBro"

    elif bot_type == Const.BOT_TYPE_CSGOOF:
        return "CSGOof"

    elif bot_type == Const.BOT_TYPE_CSGODADDY:
        return "CSGODaddy"

    elif bot_type == Const.BOT_TYPE_CSGOABSTRACT:
        return "CSGOAbstract"

    elif bot_type == Const.BOT_TYPE_CSGOBALLER:
        return "CSGOBaller"

    elif bot_type == Const.BOT_TYPE_CSGOBULLET:
        return "CSGOBullet"

    elif bot_type == Const.BOT_TYPE_CSGOTANK:
        return "CSGOTank"

    elif bot_type == Const.BOT_TYPE_CSGOCANDY:
        return "CSGOCandy"

    elif bot_type == Const.BOT_TYPE_CSGOFART:
        return "CSGOFart"

    elif bot_type == Const.BOT_TYPE_CSGOREHAB:
        return "CSGORehab"

    elif bot_type == Const.BOT_TYPE_CSGOFREE:
        return "CSGOFree"

    elif bot_type == Const.BOT_TYPE_CSGOCASES:
        return "CSGOCases"

    elif bot_type == Const.BOT_TYPE_CSGOSNAKE:
        return "CSGOSnake"

    elif bot_type == Const.BOT_TYPE_CSGOINACTIVE:
        return "CSGOInactive"

    elif bot_type == Const.BOT_TYPE_AEROFAM420:
        return "AeroFam420"

    elif bot_type == Const.BOT_TYPE_CSGOBEAST:
        return "CSGO Beast"

    elif bot_type == Const.BOT_TYPE_CSGOHAMZA:
        return "CsgoHamza"

    elif bot_type == Const.BOT_TYPE_SPIN2WIN:
        return "Spin2Win"

    elif bot_type == Const.BOT_TYPE_UNICORN:
        return "Unicorn"

    elif bot_type == Const.BOT_TYPE_VASCO:
        return "VascoGaming"

    elif bot_type == Const.BOT_TYPE_CSGOCASESONLY:
        return "Csgocasesonly"

    elif bot_type == Const.BOT_TYPE_LORDHELIX:
        return "LordHelix"

    elif bot_type == Const.BOT_TYPE_OZZNY09:
        return "Ozzny09"

    elif bot_type == Const.BOT_TYPE_FOSSYGFX:
        return "FossyGfx"

    elif bot_type == Const.BOT_TYPE_REALCSGOFIRE:
        return "Realcsgofire"

    elif bot_type == Const.BOT_TYPE_JERRYXTC:
        return "JerryXtc"

    elif bot_type == Const.BOT_TYPE_TELLFULGAMES:
        return "TellfulGames"

    elif bot_type == Const.BOT_TYPE_LITSKINS:
        return "LitSkins"

    elif bot_type == Const.BOT_TYPE_SUFFERCSGO:
        return "SufferCsgo"

    elif bot_type == Const.BOT_TYPE_BOTWREK:
        return "BOT WREK"

    elif bot_type == Const.BOT_TYPE_MAINGAME:
        return "Maingame"

    elif bot_type == Const.BOT_TYPE_JAN:
        return "Jan"

    elif bot_type == Const.BOT_TYPE_ITSNANCY:
        return "ItsNancy"

    elif bot_type == Const.BOT_TYPE_CSGOHOPE:
        return "CSGOHope"

    # elif bot_type == Const.BOT_TYPE_:
    #     return ""



def send_tracker(fb_psid, category, action=None, label=None, value=None):
    logger.info("send_tracker(fb_psid=%s, category=%s, action=%s, label=%s, value=%s)" % (fb_psid, category, action, label, value))

    action = action or category
    label = label or fb_psid
    value = value or "0"

    payload = {
        'v'   : 1,
        't'   : "event",
        'tid' : Const.GA_TRACKING_ID,
        'cid' : hashlib.md5(fb_psid.encode()).hexdigest(),
        'ec'  : category,
        'ea'  : action,
        'el'  : label,
        'ev'  : value
    }

    c = pycurl.Curl()
    c.setopt(c.URL, Const.GA_TRACKING_URL)
    c.setopt(c.POSTFIELDS, urlencode(payload))
    c.setopt(c.WRITEDATA, StringIO())
    c.perform()
    c.close()


    payload['tid'] = "UA-79705534-4"

    c = pycurl.Curl()
    c.setopt(c.URL, Const.GA_TRACKING_URL)
    c.setopt(c.POSTFIELDS, urlencode(payload))
    c.setopt(c.WRITEDATA, StringIO())
    c.perform()
    c.close()


    return True


def write_message_log(sender_id, message_id, message_txt):
    logger.info("write_message_log(sender_id=%s, message_id=%s, message_txt=%s)" % (sender_id, message_id, json.dumps(message_txt)))

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('INSERT INTO `fbbot_logs` (`id`, `message_id`, `bot_type`, `chat_id`, `body`) VALUES (NULL, %s, %s, %s, %s)', (message_id, get_session_bot_type(sender_id), sender_id, json.dumps(message_txt)))

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


def main_menu_quick_reply():
    logger.info("main_menu_quick_reply()")
    return [{
        'content_type': "text",
        'title'       : "Main Menu",
        'payload'     : "MAIN_MENU"
    }, {
        'content_type': "text",
        'title'       : "Next Item",
        'payload'     : "NEXT_ITEM"
    }]


def home_quick_replies():
    logger.info("home_quick_replies()")
    return main_menu_quick_reply() + [{
        'content_type' : "text",
        'title'        : "Shop Lmon8",
        'payload'      : "LMON8_REFERRAL"
    }, {
        'content_type' : "text",
        'title'        : "Invite Friends Now",
        'payload'      : "INVITE"
    }, {
        'content_type' : "text",
        'title'        : "Support",
        'payload'      : "SUPPORT"
    }]


def submit_quick_replies(captions=["Yes", "No"]):
    logger.info("submit_quick_replies()")
    return [{
        'content_type': "text",
        'title'       : captions[0],
        'payload'     : "SUBMIT_YES"
    }, {
        'content_type': "text",
        'title'       : captions[1],
        'payload'     : "SUBMIT_NO"
    }, {
        'content_type': "text",
        'title'       : "Cancel",
        'payload'     : "SUBMIT_CANCEL"
    }]


def coin_flip_quick_replies():
    logger.info("coin_flip_quick_replies()")
    return [{
        'content_type': "text",
        'title'       : "Next Item",
        'payload'     : "NEXT_ITEM"
    }, {
        'content_type': "text",
        'title'       : "Get 2 More Wins",
        'payload'     : "DISCORD"
    }, {
        'content_type': "text",
        'title'       : "FAQ",
        'payload'     : "FAQ"
    }]


def opt_out_quick_replies():
    logger.info("opt_out_quick_replies()")
    return [{
        'content_type' : "text",
        'title'        : "Opt-In",
        'payload'      : "OPT_IN"
    }, {
        'content_type' : "text",
        'title'        : "Cancel",
        'payload'      : "CANCEL"
    }]


def buy_credits_button(sender_id, item_id, price):
    logger.info("buy_credits_button(sender_id=%s item_id=%s, price=%s)" % (sender_id, item_id, price))

    return {
        'type'            : "payment",
        'title'           : "Buy",
        'payload'         : "%s-%d" % ("PURCHASE_ITEM", item_id),
        'payment_summary' : {
            'currency'            : "USD",
            'payment_type'        : "FIXED_AMOUNT",
            'is_test_payment'     : Const.TEST_PAYMENTS == 1,
            'merchant_name'       : "Gamebots",
            'requested_user_info' : [
                "contact_email"
            ],
            'price_list'          : [{
                'label'  : "Subtotal",
                'amount' : price
            }]
        }
    }

def default_carousel(sender_id, amount=1):
    logger.info("default_carousel(sender_id=%s amount=%s)" % (sender_id, amount))

    set_session_item(sender_id)

    elements = []
    for i in range(amount):# + 5 if sender_id in Const.ADMIN_FB_PSID else amount):
        elements.append(coin_flip_element(sender_id))

    if None in elements:
        send_text(sender_id, "No items are available right now, try again later", main_menu_quick_reply())
        return

    send_carousel(
        recipient_id=sender_id,
        elements=elements,
        quick_replies=home_quick_replies()
    )

def send_discord_card(sender_id):
    logger.info("send_discord_card(sender_id=%s)" % (sender_id,))

    send_card(
        recipient_id=sender_id,
        title="{bot_title} on Discord".format(bot_title=bot_title(get_session_bot_type(sender_id))),
        image_url="https://discordapp.com/assets/ee7c382d9257652a88c8f7b7f22a994d.png",
        card_url="http://taps.io/BvR8w",
        quick_replies=main_menu_quick_reply()
    )

def send_install_card(sender_id):
    logger.info("send_install_card(sender_id=%s)" % (sender_id,))

    send_card(
        recipient_id=sender_id,
        title="Earn More Points",
        image_url="https://i.imgur.com/DbcITTT.png",
        card_url="http://taps.io/skins"
    )

    send_text(sender_id, "Unlock two more flips. Install 2 & upload screenshot. (txt \"upload\")", main_menu_quick_reply())

def send_ad_card(sender_id):
    logger.info("send_ad_card(sender_id=%s)" % (sender_id,))

    send_card(
        recipient_id=sender_id,
        title="Unlock Your Win",
        image_url="https://i.ytimg.com/vi/WkMgq2Y9c4o/maxresdefault.jpg",
        card_url="http://taps.io/skins",
        quick_replies=main_menu_quick_reply()
    )

def send_pay_wall(sender_id, item):
    logger.info("send_pay_wall(sender_id=%s, item=%s)" % (sender_id, item))

    send_tracker(fb_psid=sender_id, category="pay-wall", label=item['asset_name'])

    if flips_last_day(sender_id) >= Const.MAX_FLIPS_PER_DAY:
        send_text(sender_id, "You have hit the daily win limit for free users. Please purchase credits to continue.")

    if item is not None:
        element = {
            'title'    : item['asset_name'].encode('utf8'),
            'subtitle' : "${price:.2f}".format(price=item['price']) if sender_id == "1219553058088713" else "You could win this!",
            'image_url': item['image_url'],
            'item_url' : None,
            'buttons'  : []
        }

        graph = fb_graph_user(sender_id)
        if graph is not None and graph['is_payment_enabled'] is True and get_session_bot_type(sender_id) == Const.BOT_TYPE_GAMEBOTS:
            element['buttons'].append(buy_credits_button(sender_id, item['id'], max(1, deposit_amount_for_price(item['price']))))

        element['buttons'].append({
            'type'                : "web_url",
            'url'                 : "http://gamebots.chat/paypal/{fb_psid}/{price}".format(fb_psid=sender_id, price=max(2, deposit_amount_for_price(item['price']))),  # if sender_id in Const.ADMIN_FB_PSID else "http://paypal.me/gamebotsc/{price}".format(price=price),
            'title'               : "Paypal - ${price}".format(price=max(2, deposit_amount_for_price(item['price']))),
            'webview_height_ratio': "tall"
        })

        if get_session_bot_type(sender_id) == Const.BOT_TYPE_GAMEBOTS:
            element['buttons'].append({
                'type'   : "postback",
                'payload': "POINTS-{price}".format(price=max(2, deposit_amount_for_price(item['price']))),
                'title'  : "{points} Points".format(points=locale.format('%d', max(2, deposit_amount_for_price(item['price'])) * 250000, grouping=True))
            })

        else:
            element['buttons'].append({
                'type'                : "web_url",
                'url'                 : "http://gamebots.chat/crossbot",
                'title'               : "More Wins - Tap Here",
                'webview_height_ratio': "full"
            })

    else:
        element = coin_flip_element(sender_id, True)


    send_carousel(
        recipient_id=sender_id,
        elements=[element],
        quick_replies=coin_flip_quick_replies()
    )


def pay_wall_deposit(sender_id, min_price, max_price):
    logger.info("pay_wall_deposit(sender_id=%s, min_price=%s, max_price=%s)" % (sender_id, min_price, max_price))

    bot_type = get_session_bot_type(sender_id)
    if bot_type == Const.BOT_TYPE_GAMEBOTS:
        game_name = "CS:GO"
    elif bot_type == Const.BOT_TYPE_H1Z1:
        game_name = "H1Z1"
    elif bot_type == Const.BOT_TYPE_DOTA2:
        game_name = "Dota 2"
    elif bot_type == Const.BOT_TYPE_BSP:
        game_name = ""
    elif bot_type == Const.BOT_TYPE_PAYDAY2:
        game_name = ""
    elif bot_type == Const.BOT_TYPE_BALLISTICOVERKILL:
        game_name = ""
    elif bot_type == Const.BOT_TYPE_KILLINGFLOOR2:
        game_name = ""
    elif bot_type == Const.BOT_TYPE_TF2:
        game_name = ""
    elif bot_type == Const.BOT_TYPE_DOI:
        game_name = ""
    else:
        game_name = "CS:GO"

    row = None

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            logger.info("1ST ATTEMPT AT PAYWALL-ITEM FOR (%s) =|=|=|=|=|=|=|=|=|=|=|=> %s" % (sender_id, ('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `price` >= %s ORDER BY RAND() LIMIT 1;' % (game_name, min_price)),))
            cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `price` >= %s AND `price` < %s ORDER BY RAND() LIMIT 1;', (game_name, min_price, max_price))
            row = cur.fetchone()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    item = row
    if item is not None:
        element = {
            'title'    : item['asset_name'].encode('utf8'),
            'subtitle' : "${price:.2f}".format(price=item['price']) if sender_id == "1219553058088713" else "You could win this!",
            'image_url': item['image_url'],
            'item_url' : None,
            'buttons'  : []
        }

        graph = fb_graph_user(sender_id)
        if graph is not None and graph['is_payment_enabled'] is True and get_session_bot_type(sender_id) == Const.BOT_TYPE_GAMEBOTS:
            element['buttons'].append(buy_credits_button(sender_id, item['id'], max(1, deposit_amount_for_price(item['price']))))

        element['buttons'].append({
            'type'                : "web_url",
            'url'                 : "http://gamebots.chat/paypal/{fb_psid}/{price}".format(fb_psid=sender_id, price=max(1, deposit_amount_for_price(item['price']))),  # if sender_id in Const.ADMIN_FB_PSID else "http://paypal.me/gamebotsc/{price}".format(price=price),
            'title'               : "Paypal - ${price}".format(price=deposit_amount_for_price(item['price'])),
            'webview_height_ratio': "tall"
        })

        if get_session_bot_type(sender_id):
            element['buttons'].append({
                'type'   : "postback",
                'payload': "POINTS-{price}".format(price=deposit_amount_for_price(item['price'])),
                'title'  : "{points} Points".format(points=locale.format('%d', max(1, deposit_amount_for_price(item['price'])) * 1250000, grouping=True))
            })

        else:
            element['buttons'].append({
                'type'                : "web_url",
                'url'                 : "http://gamebots.chat/crossbot",
                'title'               : "More Wins - Tap Here",
                'webview_height_ratio': "full"
            })

    else:
        element = coin_flip_element(sender_id, True)

    send_carousel(
        recipient_id=sender_id,
        elements=[element],
        quick_replies=coin_flip_quick_replies()
    )


def mobile_legend_item(sender_id):
    logger.info("mobile_legend_item(sender_id=%s)" % (sender_id,))

    items = []
    with open("/var/www/FacebookBot/FacebookBot/data/csv/mobile-legend.csv", 'rb') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            items.append(row)

    return random.choice(items)


def next_coin_flip_item(sender_id, pay_wall=False):
    logger.info("next_coin_flip_item(sender_id=%s, pay_wall=%s)" % (sender_id, pay_wall))

    row = None
    item_id = None
    deposit = get_session_deposit(sender_id)
    left = deposit - win_value_last_day(sender_id)

    min_price = 0.00
    if pay_wall is True or random.uniform(0, 1) <= 1 / float(3):
        pay_wall = True
        deposit_cycle = cycle([0.00, 2.00])
        next_deposit = deposit_cycle.next()
        while next_deposit <= deposit:
            next_deposit = deposit_cycle.next()
        deposit = next_deposit

    min_price, max_price = price_range_for_deposit(deposit)

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)

            bot_type = get_session_bot_type(sender_id)
            if bot_type == Const.BOT_TYPE_GAMEBOTS:
                game_name = "CS:GO"
            elif bot_type == Const.BOT_TYPE_H1Z1:
                game_name = "H1Z1"
            elif bot_type == Const.BOT_TYPE_DOTA2:
                game_name = "Dota 2"
            elif bot_type == Const.BOT_TYPE_BSP:
                game_name = ""
            elif bot_type == Const.BOT_TYPE_PAYDAY2:
                game_name = ""
            elif bot_type == Const.BOT_TYPE_BALLISTICOVERKILL:
                game_name = ""
            elif bot_type == Const.BOT_TYPE_KILLINGFLOOR2:
                game_name = ""
            elif bot_type == Const.BOT_TYPE_TF2:
                game_name = ""
            elif bot_type == Const.BOT_TYPE_DOI:
                game_name = ""
            else:
                game_name = "CS:GO"

            if get_session_bonus(sender_id) is None:
                if pay_wall is True:
                    logger.info("1ST ATTEMPT AT PAYWALL-ITEM FOR (%s) =|=|=|=|=|=|=|=|=|=|=|=> %s" % (sender_id, ('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `price` >= %s ORDER BY RAND() LIMIT 1;' % (game_name, min_price)),))
                    cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `price` >= %s ORDER BY RAND() LIMIT 1;', (game_name, min_price))

                else:
                    logger.info("1ST ATTEMPT AT ITEM FOR (%s) =|=|=|=|=|=|=|=|=|=|=|=> %s" % (sender_id, ('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `price` >= %s AND `price` < %s AND `type_id` = 1 AND `enabled` = 1 ORDER BY RAND() LIMIT 1;' % (game_name, min_price, max_price)),))
                    cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `price` >= %s AND `price` < %s AND `type_id` = 1 AND `enabled` = 1 ORDER BY RAND() LIMIT 1;', (game_name, min_price, max_price))

                row = cur.fetchone()
                if row is None:
                    logger.info("ROW WAS BLANK!! -- 2nd ATTEMPT AT (%s)ITEM FOR (%s) =|=|=|=|=|=|=|=|=|=|=|=> %s" % ("PAYWALL-" if pay_wall is True else "", sender_id, ('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `price` <= %s AND `type_id` = 1 ORDER BY RAND() LIMIT 1;' if pay_wall is False and deposit == get_session_deposit(sender_id) else 'SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `price` <= %s AND `type_id` = 1 ORDER BY `price` DESC LIMIT 1;' % (game_name, max_price)),))
                    cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `price` <= %s AND `type_id` = 1 ORDER BY RAND() LIMIT 1;' if pay_wall is False and deposit == get_session_deposit(sender_id) else 'SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `price` <= %s AND `type_id` = 1 ORDER BY `price` DESC LIMIT 1;', (game_name, max_price))
                    row = cur.fetchone()

            else:
                logger.info("BONUS ATTEMPT AT ITEM FOR (%s) =|=|=|=|=|=|=|=|=|=|=|=> %s" % (sender_id, ('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `type_id` = 3 AND `enabled` = 1 ORDER BY RAND() LIMIT 1;' % (game_name,)),))
                cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `price` FROM `flip_items` WHERE `game_name` = %s AND `quantity` > 0 AND `type_id` = 3 AND `enabled` = 1 ORDER BY RAND() LIMIT 1;', (game_name,))
                row = cur.fetchone()

            if row is not None:
                item_id = row['id']
                set_session_item(sender_id, item_id)

            else:
                clear_session_dub(sender_id)


    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return row


def coin_flip_element(sender_id, pay_wall=False):
    logger.info("coin_flip_element(sender_id=%s, pay_wall=%s)" % (sender_id, pay_wall))

    element = None
    row = next_coin_flip_item(sender_id, pay_wall)
    if row is not None:
        item_id = row['id']
        set_session_item(sender_id, item_id)

        if pay_wall is False:# and deposit_amount_for_price(row['price'] <= get_session_deposit(sender_id)):
            element = {
                'title'    : row['asset_name'].encode('utf8'),
                'subtitle' : "${price:.2f}".format(price=row['price']) if sender_id == "1219553058088713" else None if pay_wall is False else "Requires ${price:.2f} deposit".format(price=deposit_amount_for_price(row['price'])),
                'image_url': row['image_url'],
                'item_url' : None,
                'buttons'  : [{
                    'type'   : "postback",
                    'payload': "FLIP_COIN-{item_id}".format(item_id=item_id),
                    'title'  : "Flip Coin"
                }, {
                    'type'   : "postback",
                    'payload': "INVITE",
                    'title'  : "Share"
                }]
            }

        else:
            image_url = ""
            if deposit_amount_for_price(row['price']) == 1:
                image_url = "https://i.imgur.com/KrObpgY.png"

            elif deposit_amount_for_price(row['price']) == 2:
                image_url = "https://i.imgur.com/SFCsAGx.png"

            elif deposit_amount_for_price(row['price']) == 5:
                image_url = "https://i.imgur.com/IDdqOWO.png"

            elif deposit_amount_for_price(row['price']) == 10:
                image_url = "https://i.imgur.com/9s1JeqD.png"

            else:
                image_url = "https://i.imgur.com/KrObpgY.png"

            element = {
                'title'    : row['asset_name'].encode('utf8'),
                'subtitle' : "${price:.2f}".format(price=row['price']) if sender_id == "1219553058088713" else "You could win this!",
                'image_url': row['image_url'],
                'item_url' : None,
                'buttons': []
            }

            graph = fb_graph_user(sender_id)
            if graph is not None and graph['is_payment_enabled'] is True and get_session_bot_type(sender_id) == Const.BOT_TYPE_GAMEBOTS:
                element['buttons'].append(buy_credits_button(sender_id, item_id, max(1, deposit_amount_for_price(row['price']))))

            element['buttons'].append({
                'type'                : "web_url",
                'url'                 : "http://gamebots.chat/paypal/{fb_psid}/{price}".format(fb_psid=sender_id, price=max(1, deposit_amount_for_price(row['price']))),  # if sender_id in Const.ADMIN_FB_PSID else "http://paypal.me/gamebotsc/{price}".format(price=price),
                'title'               : "Paypal - ${price}".format(price=max(1, deposit_amount_for_price(row['price']))),
                'webview_height_ratio': "tall"
            })

            element['buttons'].append({
                'type'   : "postback",
                'payload': "POINTS-{price}".format(price=deposit_amount_for_price(row['price'])),
                'title'  : "{points} Points".format(points=locale.format('%d', max(1, deposit_amount_for_price(row['price'])) * 2500000, grouping=True))
            })

    return element


def coin_flip_prep(sender_id, deposit=0, item_id=None, interval=12):
    logger.info("coin_flip_prep(sender_id=%s, deposit=%s, item_id=%s, interval=%s)" % (sender_id, deposit, item_id, interval))

    item = get_item_details(item_id)
    # return False if sender_id in Const.ADMIN_FB_PSID else coin_flip(wins_last_day(sender_id), min(max(get_session_loss_streak(sender_id), 1), int(Const.MAX_LOSSING_STREAK)), deposit, item['price'], item['quantity'], all_available_quantity())
    return coin_flip(
        wins=wins_last_day(sender_id),
        losses=min(max(get_session_loss_streak(sender_id), 1), int(Const.MAX_LOSSING_STREAK)),
        deposit=deposit,
        item_cost=item['price'],
        quantity=item['quantity'],
        total_quantity=all_available_quantity()
    )


def coin_flip(wins=0, losses=0, deposit=0, item_cost=0.01, quantity=1, total_quantity=1):
    logger.info("coin_flip(wins=%s, losses=%s, deposit=%s, item_cost=%s, quantity=%s)" % (wins, losses, deposit, item_cost, quantity))

    if losses >= Const.MAX_LOSSING_STREAK:
        return True

    probility = statistics.stdev([min(max(random.expovariate(1.0 / float(wins * 3.0) if wins >= 1 else float(3.0)), 0), 1) for i in range(int(random.gauss(21, 3 + (1 / float(3)))))]) if deposit >= deposit_amount_for_price(item_cost) else 0.00
    probility += (losses / float(Const.MAX_LOSSING_STREAK))
    probility *= (1 / float(2)) if deposit == 0 else 1.125
    # dice_roller = 1 - int(round(random.uniform(1, 6))) / float(6)
    dice_roller = 1 - random.uniform(0, 1)
    outcome = probility >= dice_roller
    logger.info("[:::::::] wins=%02d, losses=%02d, dep=$%05.2f, cost=$%05.2f, quant=%03d, tot_quant=%03d [::::] FLIP-CHANCE --> %5.2f%% // %.2f -[%s]-" % (wins, losses, deposit, item_cost, quantity, total_quantity, probility * 100, dice_roller, ("%s" % (outcome,)[0])))

    return outcome


def coin_flip_results(sender_id, item_id=None):
    logger.info("coin_flip_results(sender_id=%s, item_id=%s)" % (sender_id, item_id))

    send_tracker(fb_psid=sender_id, category="flip")

    image_url = Const.FLIP_COIN_START_GIF_URL
    bot_type = get_session_bot_type(sender_id)
    if bot_type == Const.BOT_TYPE_GAMEBOTS:
        image_url = Const.FLIP_COIN_START_GIF_URL
    elif bot_type == Const.BOT_TYPE_GAMEBAE:
        image_url = "https://i.imgur.com/f3U5sBr.png"
    elif bot_type == Const.BOT_TYPE_DOTA2:
        image_url = "https://i.imgur.com/NHN7nk0.gif"
    elif bot_type == Const.BOT_TYPE_H1Z1:
        image_url = "https://i.imgur.com/jyd44FT.gif"
    elif bot_type == Const.BOT_TYPE_CSGOSPICE:
        image_url = "https://i.imgur.com/47K1hfu.gif"
    elif bot_type == Const.BOT_TYPE_CSGOBUNNY:
        image_url = "https://i.imgur.com/XlqMZSb.gif"
    elif bot_type == Const.BOT_TYPE_CSGOBURRITO:
        image_url = "https://i.imgur.com/UQUrXrZ.gif"
    elif bot_type == Const.BOT_TYPE_CSGOPIZZA:
        image_url = "https://i.imgur.com/cEVnFMg.gif"
    elif bot_type == Const.BOT_TYPE_CSGOSUSHI:
        image_url = "https://i.imgur.com/XXMjN0t.gif"
    elif bot_type == Const.BOT_TYPE_CSGOBLAZE:
        image_url = "https://i.imgur.com/QsGWVaM.gif"
    elif bot_type == Const.BOT_TYPE_BSP:
        image_url = "https://i.imgur.com/3lK61LN.gif"
    elif bot_type == Const.BOT_TYPE_PAYDAY2:
        image_url = "https://i.imgur.com/OkjfCg7.gif"
    elif bot_type == Const.BOT_TYPE_BALLISTICOVERKILL:
        image_url = "https://i.imgur.com/GIDi8Ux.gif"
    elif bot_type == Const.BOT_TYPE_KILLINGFLOOR2:
        image_url = "https://i.imgur.com/JZ6vQWo.gif"
    elif bot_type == Const.BOT_TYPE_TF2:
        image_url = "https://i.imgur.com/ymgYHaY.gif"
    elif bot_type == Const.BOT_TYPE_DOI:
        image_url = "https://i.imgur.com/x98Xb0I.gif"
    elif bot_type == Const.BOT_TYPE_CCZAR:
        image_url = "https://i.imgur.com/pOIpYt0.gif"
    elif bot_type == Const.BOT_TYPE_CSGOHOMIE:
        image_url = "https://i.imgur.com/EpY5kAM.gif"
    elif bot_type == Const.BOT_TYPE_CSGOFNATIC:
        image_url = "https://i.imgur.com/9gI8Yq0.gif"
    elif bot_type == Const.BOT_TYPE_CSGOSK:
        image_url = "https://i.imgur.com/CeD4hmk.gif"
    elif bot_type == Const.BOT_TYPE_CSGOFAZE:
        image_url = "https://i.imgur.com/n04OafU.gif"
    elif bot_type == Const.BOT_TYPE_CSGOJUICE:
        image_url = "https://i.imgur.com/9L8tfTc.gif"
    elif bot_type == Const.BOT_TYPE_CSGOFADED:
        image_url = "https://i.imgur.com/RPdcHth.gif"
    elif bot_type == Const.BOT_TYPE_CSGOHOMIE:
        image_url = "https://i.imgur.com/cnD7Wjo.gif"
    elif bot_type == Const.BOT_TYPE_CSGOBOOM:
        image_url = "https://i.imgur.com/npTubyP.gif"
    elif bot_type == Const.BOT_TYPE_CSGOSMOKE:
        image_url = "https://i.imgur.com/hPhkG5C.gif"
    elif bot_type == Const.BOT_TYPE_CSGOCRAY:
        image_url = "https://i.imgur.com/wS0SZ08.gif"
    elif bot_type == Const.BOT_TYPE_CSGODADDY:
        image_url = "https://i.imgur.com/wiqPOjf.gif"
    elif bot_type == Const.BOT_TYPE_CSGOWHIP:
        image_url = "https://i.imgur.com/MAGiLy1.gif"
    elif bot_type == Const.BOT_TYPE_CSGOKNIFE:
        image_url = "https://i.imgur.com/LEOeTeq.gif"
    elif bot_type == Const.BOT_TYPE_CSGOFRAT:
        image_url = "https://i.imgur.com/H0j8OyI.gif"
    elif bot_type == Const.BOT_TYPE_CSGOBRO:
        image_url = "https://i.imgur.com/k672Axy.gif"
    elif bot_type == Const.BOT_TYPE_CSGOABSTRACT:
        image_url = "https://i.imgur.com/EfNdLiu.gif"
    elif bot_type == Const.BOT_TYPE_CSGONUKE:
        image_url = "https://i.imgur.com/4UwJdXW.gif"
    # elif bot_type == Const.BOT_TYPE_CSGOBULLET:
    #     image_url = "https://i.imgur.com/6fasR4D.gif"
    elif bot_type == Const.BOT_TYPE_CSGOMICKEY:
        image_url = "https://i.imgur.com/ILr7ZQi.gif"
    # elif bot_type == Const.BOT_TYPE_CSGOFART:
    #     image_url = "https://i.imgur.com/T9Zea6a.gif"
    # elif bot_type == Const.BOT_TYPE_CSGOCANDY:
    #     image_url = "https://i.imgur.com/PIpqrwd.gif"
    # elif bot_type == Const.BOT_TYPE_CSGOREHAB:
    #     image_url = "https://i.imgur.com/I71pFKG.gif"
    # elif bot_type == Const.BOT_TYPE_CSGORAMEN:
    #     image_url = "https://i.imgur.com/FDnuinr.gif"
    # elif bot_type == Const.BOT_TYPE_CSGOFML:
    #     image_url = "https://i.imgur.com/GyW6xVi.gif"
    # elif bot_type == Const.BOT_TYPE_CSGOWTF:
    #     image_url = "https://i.imgur.com/UkhWfAU.gif"
    # elif bot_type == Const.BOT_TYPE_CSGOCHEESE:
    #     image_url = "https://i.imgur.com/wVW8E5Q.gif"
    elif bot_type == Const.BOT_TYPE_CSGOBALLER:
        image_url = "https://i.imgur.com/ky312Vd.gif"
    elif bot_type == Const.BOT_TYPE_CSGOMISSY:
        image_url = "https://i.imgur.com/e3TWIqq.gif"
    elif bot_type == Const.BOT_TYPE_CSGOINACTIVE:
        image_url = "https://i.imgur.com/3fLwVbG.gif"
    elif bot_type == Const.BOT_TYPE_CSGOSNAKE:
        image_url = "https://i.imgur.com/RUZT1Vr.gif"
    elif bot_type == Const.BOT_TYPE_CSGOBEAST:
        image_url = "https://i.imgur.com/NNKie1P.gif"
    elif bot_type == Const.BOT_TYPE_UNICORN:
        image_url = "https://i.imgur.com/OUv9W9o.gif"
    elif bot_type == Const.BOT_TYPE_LORDHELIX:
        image_url = "https://i.imgur.com/mWKd5Ag.gif"
    elif bot_type == Const.BOT_TYPE_OZZNY09:
        image_url = "https://i.imgur.com/uw9dX1w.gif"
    elif bot_type == Const.BOT_TYPE_SUFFERCSGO:
        image_url = "https://i.imgur.com/pOBhKza.gif"
    elif bot_type == Const.BOT_TYPE_TELLFULGAMES:
        image_url = "https://i.imgur.com/2LViM6t.gif"
    elif bot_type == Const.BOT_TYPE_VASCO:
        image_url = "https://i.imgur.com/wfgNUl6.gif"
    elif bot_type == Const.BOT_TYPE_CSGOHOPE:
        image_url = "https://media.giphy.com/media/K0WEtL8FbxgYM/giphy.gif"
    elif bot_type == Const.BOT_TYPE_MAINGAME:
        image_url = "https://i.imgur.com/CeFy6C0.gif"
    elif bot_type == Const.BOT_TYPE_ITSNANCY:
        image_url = "http://i.imgur.com/UJpnZeD.gif"
    elif bot_type == Const.BOT_TYPE_JAN:
        image_url = "https://media.giphy.com/media/K0WEtL8FbxgYM/giphy.gif"


    send_image(sender_id, image_url)
    time.sleep(3.33)

    if item_id is None:
        send_text(sender_id, "Can't find your item! Try flipping for it again", main_menu_quick_reply())
        default_carousel(sender_id)
        return "OK", 200

    flip_item = None

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)

            cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `quantity`, `price` FROM `flip_items` WHERE `id` = %s LIMIT 1;', (item_id,))
            row = cur.fetchone()
            if row is not None:
                flip_item = {
                    'item_id'    : row['id'],
                    'type_id'    : row['type_id'],
                    'asset_name' : row['asset_name'].encode('utf8'),
                    'game_name'  : row['game_name'],
                    'image_url'  : row['image_url'],
                    'quantity'   : row['quantity'],
                    'price'      : row['price'],
                    'claim_id'   : None,
                    'claim_url'  : None,
                    'pin_code'   : hashlib.md5(str(time.time()).encode()).hexdigest()[-4:].upper()
                }

                if flip_item['type_id'] == 3:
                    cur.execute('UPDATE `bonus_codes` SET `enabled` = 0 WHERE `code` = %s LIMIT 1;', (get_session_bonus(sender_id),))
                    conn.commit()

            else:
                send_text(sender_id, "Looks like that item isn't available anymore, try another one")
                send_carousel(recipient_id=sender_id, elements=[coin_flip_element(sender_id)])
                return "OK", 0

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    set_session_bonus(sender_id)

    if coin_flip_prep(sender_id, get_session_deposit(sender_id), item_id) is True or sender_id in Const.ADMIN_FB_PSID:
        send_tracker(fb_psid=sender_id, category="win", label=flip_item['asset_name'], value=flip_item['price'])
        send_tracker(fb_psid=sender_id, category="transaction", label=flip_item['asset_name'], value=flip_item['price'])

        payload = {
            'v'   : 1,
            't'   : "event",
            'tid' : "UA-79705534-2",
            'cid' : hashlib.md5(sender_id.encode()).hexdigest(),
            'ec'  : "purchase",
            'ea'  : "purchase",
            'el'  : flip_item['asset_name'],
            'ev'  : flip_item['price']
        }

        c = pycurl.Curl()
        c.setopt(c.URL, Const.GA_TRACKING_URL)
        c.setopt(c.POSTFIELDS, urlencode(payload))
        c.setopt(c.WRITEDATA, StringIO())
        c.perform()
        c.close()


        set_session_loss_streak(sender_id)
        record_coin_flip(sender_id, item_id, True)

        full_name, f_name, l_name = get_session_name(sender_id)
        payload = {
            'channel'   : "#wins-001",
            'username ' : bot_title(get_session_bot_type(sender_id)),
            'icon_url'  : "https://i.imgur.com/bhSzZiO.png",
            'text'      : "Flip Win by *{user}* ({sender_id})\n{trade_url}\n\n_{item_name}_".format(user=sender_id if full_name is None else full_name, sender_id=sender_id, trade_url=get_session_trade_url(sender_id), item_name=flip_item['asset_name']),
        }
        response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('INSERT INTO `item_winners` (`bot_type`, `fb_id`, `pin`, `item_id`, `item_name`, `claimed`, `added`) VALUES (%s, %s, %s, %s, %s, %s, NOW());', (get_session_bot_type(sender_id), sender_id, flip_item['pin_code'], flip_item['item_id'], flip_item['asset_name'], 0 if flip_item['price'] < 1.00 and get_session_deposit(sender_id) < 1.00 else 4))

                if sender_id not in Const.ADMIN_FB_PSID:
                    cur.execute('UPDATE `flip_items` SET `quantity` = `quantity` - 1 WHERE `id` = %s AND quantity > 0 LIMIT 1;', (flip_item['item_id'],))

                conn.commit()
                cur.execute('SELECT @@IDENTITY AS `id` FROM `item_winners`;')
                flip_item['claim_id'] = cur.fetchone()['id']

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(sender_id, "You won {item_name}.".format(item_name=flip_item['asset_name']))

        if bot_type == Const.BOT_TYPE_GAMEBOTS:
            send_text(sender_id, "Tap on the following link to confirm... taps.io/skins")

        send_video(sender_id, "http://prebot.me/videos/MobileLegends.mp4")
        send_ad_card(sender_id)

        if get_session_trade_url(sender_id) is None:
            set_session_trade_url(sender_id, "_{PENDING}_")
            set_session_state(sender_id, Const.SESSION_STATE_FLIP_TRADE_URL)
            send_text(sender_id, "Enter your Steam Trade URL now.")

        else:
            trade_url = get_session_trade_url(sender_id)
            send_text(
                recipient_id=sender_id,
                message_text="Your Steam Trade URL is set to:\n\n{trade_url}".format(trade_url=trade_url),
                quick_replies=[{
                    'content_type': "text",
                    'title'       : "Confirm",
                    'payload'     : "TRADE_URL_OK"
                }, {
                    'content_type': "text",
                    'title'       : "Edit URL",
                    'payload'     : "TRADE_URL_CHANGE"
                }]
            )

    else:
        send_tracker(fb_psid=sender_id, category="loss", label=flip_item['asset_name'], value=flip_item['price'])
        record_coin_flip(sender_id, item_id, False)
        inc_session_loss_streak(sender_id)

        # send_image(sender_id, Const.FLIP_COIN_LOSE_GIF_URL)
        send_text(
            recipient_id=sender_id,
            message_text="TRY AGAIN! You lost {item_name}.".format(item_name=flip_item['asset_name']),
            quick_replies=coin_flip_quick_replies()
        )
        clear_session_dub(sender_id)



def record_coin_flip(sender_id, item_id, won):
    logger.info("record_coin_flip(sender_id=%s, item_id=%s, won=%s)" % (sender_id, item_id, won))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('INSERT INTO flips (id, fb_psid, item_id, won, added) VALUES (NULL, ?, ?, ?, ?);', (sender_id, item_id, 1 if won is True else 0, int(time.time())))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::record_coin_flip[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('INSERT INTO `fb_flips` (`id`, `fb_psid`, `type_id`, `item_id`, `won`, `added`) VALUES (NULL, %s, %s, %s, %s, NOW());', (sender_id, get_session_bot_type(sender_id), item_id, 1 if won is True else 0))
            conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


def get_session_bot_type(sender_id):
    logger.info("get_session_bot_type(sender_id=%s)" % (sender_id))

    bot_type = 0
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT bot_type FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            bot_type = row['bot_type']

        logger.info("bot_type=%s" % (bot_type,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_state[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return bot_type


def set_session_bot_type(sender_id, bot_type):
    logger.info("set_session_bot_type(sender_id=%s, bot_type=%s)" % (sender_id, bot_type))
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET bot_type = ? WHERE fb_psid = ?;', (bot_type, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_state[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_state(sender_id):
    logger.info("get_session_state(sender_id=%s)" % (sender_id))
    state = Const.SESSION_STATE_NEW_USER

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT state FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            state = row['state']

        logger.info("state=%s" % (state,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_state[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return state


def set_session_state(sender_id, state=Const.SESSION_STATE_HOME):
    logger.info("set_session_state(sender_id=%s, state=%s)" % (sender_id, state))

    current_state = get_session_state(sender_id)
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if current_state == Const.SESSION_STATE_NEW_USER:
            cur.execute('INSERT INTO sessions (id, fb_psid, state, added) VALUES (NULL, ?, ?, ?);', (sender_id, state, int(time.time())))

        else:
            cur.execute('UPDATE sessions SET state = ? WHERE fb_psid = ?;', (state, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_state[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_name(sender_id):
    logger.info("get_session_name(sender_id=%s)" % (sender_id,))

    f_name = None
    l_name = None
    full_name = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT f_name, l_name FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            f_name = row['f_name']
            l_name = row['l_name']
            full_name = "%s %s" % (f_name, l_name)

        logger.info("get_session_name=%s" % (full_name,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_name[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return (full_name, f_name, l_name)


def set_session_name(sender_id, first_name=None, last_name=None):
    logger.info("set_session_name(sender_id=%s, first_name=%s, last_name=%s)" % (sender_id, first_name, last_name))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET f_name = ?, l_name = ? WHERE fb_psid = ?;', (first_name, last_name, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_name[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_item(sender_id, item_type="flip"):
    logger.info("get_session_item(sender_id=%s, item_type=%s)" % (sender_id, item_type))
    item_id = None

    if item_type == "flip":
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('SELECT flip_id FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
            row = cur.fetchone()

            if row is not None:
                item_id = row['flip_id']

            logger.info("item_id=%s" % (item_id,))

        except sqlite3.Error as er:
            logger.info("::::::get_session_item[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

        finally:
            if conn:
                conn.close()

    else:
        purchase_id, item_id = get_session_purchase(sender_id)

    return item_id

def set_session_item(sender_id, item_id=0):
    logger.info("set_session_item(sender_id=%s, item_id=%s)" % (sender_id, item_id))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET flip_id = ? WHERE fb_psid = ?;', (item_id, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_item[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_deposit(sender_id, interval=24, remote=False):
    logger.info("get_session_deposit(sender_id=%s, interval=%s, remote=%s)" % (sender_id, interval, remote))

    deposit = 0
    if remote is True:
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('SELECT SUM(`amount`) AS `tot` FROM `fb_purchases` WHERE `fb_psid` = %s AND `added` >= DATE_SUB(NOW(), INTERVAL %s HOUR);', (sender_id, interval))
                row = cur.fetchone()
                deposit = row['tot'] or 0

            logger.info("(%s)-> deposit=%s" % (sender_id, deposit))


        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()


    else:
        conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        try:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('SELECT deposit FROM sessions WHERE fb_psid = ? LIMIT 1;', (sender_id,))
            row = cur.fetchone()

            if row is not None:
                deposit = row['deposit']

            logger.info("deposit=%s" % (deposit,))

        except sqlite3.Error as er:
            logger.info("::::::get_session_deposit[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

        finally:
            if conn:
                conn.close()

    return round(deposit, 2)# if sender_id not in Const.ADMIN_FB_PSID else random.choice([0.00, 1.00, 2.00, 5.00, 15.00])


def set_session_deposit(sender_id, amount=1):
    logger.info("set_session_deposit(sender_id=%s, amount=%s)" % (sender_id, amount))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET deposit = ? WHERE fb_psid = ?;', (amount, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_deposit[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def sync_session_deposit(sender_id):
    logger.info("sync_session_deposit(sender_id=%s)" % (sender_id,))
    set_session_deposit(sender_id, get_session_deposit(sender_id, 24, True))


def get_session_bonus(sender_id):
    logger.info("get_session_bonus(sender_id=%s)" % (sender_id,))

    bonus_code = None
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT bonus FROM sessions WHERE fb_psid = ? LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            bonus_code = row['bonus']

        logger.info("bonus_code=%s" % (bonus_code,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_bonus[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return bonus_code


def set_session_bonus(sender_id, bonus_code=None):
    logger.info("set_session_bonus(sender_id=%s, bonus_code=%s)" % (sender_id, bonus_code))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET bonus = ? WHERE fb_psid = ?;', (bonus_code, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_bonus[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_trade_url(sender_id):
    logger.info("get_session_trade_url(sender_id=%s)" % (sender_id,))
    trade_url = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT trade_url FROM sessions WHERE fb_psid = ? AND trade_url IS NOT NULL LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            trade_url = row['trade_url']

        logger.info("trade_url=%s" % (trade_url))

    except sqlite3.Error as er:
        logger.info("::::::get_session_trade_url[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return trade_url


def set_session_trade_url(sender_id, trade_url=None):
    logger.info("set_session_trade_url(sender_id=%s, trade_url=%s)" % (sender_id, trade_url))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET trade_url = ? WHERE fb_psid = ?;', (trade_url, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_trade_url[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_session_purchase(sender_id):
    logger.info("get_session_purchase(sender_id=%s)" % (sender_id,))
    purchase_id = None
    flip_id = None

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT purchase_id FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()

        if row is not None:
            purchase_id = row['purchase_id']
            cur.execute('SELECT flip_id FROM payments WHERE id = ? ORDER BY added DESC LIMIT 1;', (purchase_id,))
            row = cur.fetchone()
            if row is not None:
                flip_id = row['flip_id']


        logger.info("purchase_id=%s, flip_id=" % (purchase_id,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_item[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    return (purchase_id, flip_id)


def set_session_purchase(sender_id, purchase_id=0):
    logger.info("set_session_purchase(sender_id=%s, purchase_id=%s)" % (sender_id, purchase_id))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET purchase_id = ? WHERE fb_psid = ?;', (purchase_id, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_item[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()


def get_item_details(item_id):
    logger.info("get_item_details(item_id=%s)" % (item_id,))

    item = None
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `type_id`, `asset_name`, `game_name`, `image_url`, `quantity`, `price` FROM `flip_items` WHERE `id` = %s LIMIT 1;', (item_id,))
            row = cur.fetchone()
            if row is not None:
                item = row

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return item


def get_session_loss_streak(sender_id):
    logger.info("get_session_loss_streak(sender_id=%s)" % (sender_id,))

    streak = 0
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT flips FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()
        streak = row['flips'] or 0
        logger.info("streak=%s" % (streak,))

    except sqlite3.Error as er:
        logger.info("::::::get_session_loss_streak[sqlite3.connect] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

        return streak


def inc_session_loss_streak(sender_id, amt=1):
    logger.info("set_session_loss_streak(sender_id=%s, amt=%s)" % (sender_id, amt))
    set_session_loss_streak(sender_id, get_session_loss_streak(sender_id) + amt)


def set_session_loss_streak(sender_id, streak=0):
    logger.info("set_session_loss_streak(sender_id=%s, streak=%s)" % (sender_id, streak))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('UPDATE sessions SET flips = ? WHERE fb_psid = ?;', (streak, sender_id))
        conn.commit()

    except sqlite3.Error as er:
        logger.info("::::::set_session_loss_streak[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()



def all_available_quantity():
    logger.info("all_available_quantity()")

    quantity = 0
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT SUM(`quantity`) AS `tot` FROM `flip_items` WHERE `quantity` > 0;')
            row = cur.fetchone()
            quantity = 0 if row is None else row['tot']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    logger.info("quantity=%d" % quantity)
    return quantity


def win_mulitplier(sender_id):
    logger.info("win_mulitplier(sender_id=%s)" % (sender_id,))

    if get_session_deposit(sender_id) <= 1:
        return 1

    elif get_session_deposit(sender_id) <= 2:
        return 2

    elif get_session_deposit(sender_id) <= 5:
        return 3

    elif get_session_deposit(sender_id) <= 10:
        return 3


def flips_last_day(sender_id):
    logger.info("flips_last_day(sender_id=%s)" % (sender_id,))

    total_flips = 0
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT COUNT(*) AS `tot` FROM `fb_flips` WHERE `fb_psid` = %s AND `enabled` = 1 AND `added` >= DATE_SUB(NOW(), INTERVAL 24 HOUR);', (sender_id,))
            row = cur.fetchone()
            total_flips = 0 if row is None else row['tot']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    logger.info("total_flips=%d" % total_flips)
    return total_flips



def wins_last_day(sender_id):
    logger.info("wins_last_day(sender_id=%s)" % (sender_id,))

    total_wins = 0
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT COUNT(*) AS `tot` FROM `item_winners` WHERE `fb_id` = %s AND `limiter` = 1 AND `added` >= DATE_SUB(NOW(), INTERVAL 24 HOUR);', (sender_id,))
            row = cur.fetchone()
            total_wins = 0 if row is None else row['tot']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    logger.info("total_wins=%d" % total_wins)
    return total_wins


def win_value_last_day(sender_id):
    logger.info("win_value_last_day(sender_id=%s)" % (sender_id,))

    win_val = 0
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT ROUND(SUM(`flip_inventory`.`min_sell`), 2) AS `tot` FROM `flip_inventory` INNER JOIN `item_winners` ON `flip_inventory`.`name` = `item_winners`.`item_name` WHERE `item_winners`.`fb_id` = %s AND `item_winners`.`limiter` = 1 AND `item_winners`.`added` >= DATE_SUB(NOW(), INTERVAL 24 HOUR);', (sender_id,))
            row = cur.fetchone()
            win_val = 0 if row is None else row['tot']

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    logger.info("win_val=%d" % (win_val or 0,))
    return win_val or 0


def deposit_amount_for_price(price):
    logger.info("deposit_amount_for_price(price=%s)" % (price,))

    amount = 0
    if price < 1.00:
        amount = 0

    elif price < 3.00:
        amount = 2

    else:
        amount = 2#int(price)

    logger.info("deposit_amount_for_price(price=%s) ::::: %s" % (price, amount))
    return amount


def price_range_for_deposit(deposit):
    logger.info("price_range_for_deposit(deposit=%s)" % (deposit,))

    if deposit < 2:
        price = (0.00, 1.00)

    else:
        price = (1.00, 3.00)

    return price



def valid_bonus_code(sender_id, deeplink=None):
    logger.info("valid_bonus_code(sender_id=%s, deeplink=%s)" % (sender_id, deeplink))

    is_valid = False
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `enabled` FROM `bonus_codes` WHERE `code` = %s AND `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR) LIMIT 1;', (deeplink.split("/")[-1],))
            row = cur.fetchone()
            if row is not None:
                is_valid = True

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return is_valid


def valid_purchase_code(sender_id, deeplink=None):
    logger.info("valid_purchase_code(sender_id=%s, deeplink=%s)" % (sender_id, deeplink))

    is_valid = False
    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `fb_purchases` WHERE `charge_id` = %s AND `added` > DATE_SUB(NOW(), INTERVAL 24 HOUR) LIMIT 1;', (deeplink.split("/")[-1],))
            is_valid = cur.fetchone() is not None

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    return is_valid


def enter_support(sender_id):
    logger.info("enter_support(sender_id=%s)" % (sender_id,))

    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT support FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        row = cur.fetchone()
        # if row['support'] + 86400 <= int(time.time()):
        cur.execute('UPDATE sessions SET support = ? WHERE fb_psid = ?;', (int(time.time()), sender_id))
        conn.commit()

        set_session_state(sender_id, Const.SESSION_STATE_SUPPORT)

        send_text(sender_id, "Welcome to {bot_title} Support. Your user id has been identified: {fb_psid}".format(bot_title=bot_title(get_session_bot_type(sender_id)), fb_psid=sender_id))
        send_text(
            recipient_id=sender_id,
            message_text="Please describe your support issue (500 character limit). Include purchase ID for faster look up.",
            quick_replies=[{
                'content_type': "text",
                'title'       : "Cancel",
                'payload'     : "NO_THANKS"
            }]
        )

        # else:
        #     send_text(sender_id, "You can only submit 1 support ticket per 24 hours", main_menu_quick_reply())

    except sqlite3.Error as er:
        logger.info("::::::set_session_state[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

def enter_giveaway(sender_id):
    logger.info("enter_giveaway(sender_id=%s)" % (sender_id,))

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id` FROM `giveaways` WHERE `fb_psid` = %s AND `added` >= DATE(NOW()) LIMIT 1;', (sender_id,))
            if cur.fetchone() is not None:
                send_text(sender_id, "You can only enter giveaways once per day", main_menu_quick_reply())

            else:
                bot_type = get_session_bot_type(sender_id)
                response = requests.get("http://steamcommunity.com/inventory/76561198385848170/730/2", data=json.dumps({'l': "english"}))

                if response.json()['total_inventory_count'] == 0:
                    send_text(sender_id, "Giveawsays are unavailable at this time", main_menu_quick_reply())
                    return "OK", 200
                
                elements = []
                for item in response.json()['descriptions']:
                    if len(elements) <= 5:
                        elements.append({
                            'title'    : item['market_name'],
                            'subtitle' : "",
                            'image_url': "https://steamcommunity-a.akamaihd.net/economy/image/{url}".format(url=item['icon_url_large']),
                            'item_url' : "https://twitter.com/intent/tweet?text={tweet}".format(tweet=urllib.quote("GA from {bot_title}.\nFollow + RT + Tag 1\nOpen In Messenger: https://m.me/{page_id}?ref=/giveaway\n#{hashtag}".format(bot_title=bot_title(bot_type), page_id=bot_page_id(bot_type), hashtag=bot_title(bot_type).replace(" ", "")))),
                            'buttons'  : None
                        })

                send_text(sender_id, "You have entered {bot_title}'s daily giveaway for a chance to win one of these items.".format(bot_title=bot_title(bot_type)))
                send_carousel(
                    recipient_id=sender_id,
                    elements=elements
                )

                cur.execute('INSERT INTO `giveaways` (`id`, `bot_type`, `fb_psid`, `added`) VALUES (NULL, %s, %s, NOW());', (bot_type, sender_id))
                conn.commit()
                cur.execute('SELECT COUNT(*) AS `total` FROM `giveaways` WHERE `bot_type` = %s AND `added` >= DATE(NOW());', (bot_type,))
                total = min(100, cur.fetchone()['total'])

                send_text(sender_id, "Rules: This giveaway requires {total} more entries to unlock. Please share URL with friends.".format(total=(100 - total)))
                send_text(sender_id, "https://m.me/{page_id}?ref=/giveaway".format(page_id=bot_page_id(bot_type)))

                trade_url = get_session_trade_url(sender_id)
                set_session_state(sender_id, Const.SESSION_STATE_GIVEAWAY_TRADE_URL)
                if trade_url is None:
                    send_text(sender_id, "To be eligible to win one of the above items, please enter your steam trade url", main_menu_quick_reply())

                else:
                    send_text(
                        recipient_id=sender_id,
                        message_text="Your Steam Trade URL is set to:\n\n{trade_url}".format(trade_url=trade_url),
                        quick_replies=[{
                            'content_type': "text",
                            'title'       : "Main Menu",
                            'payload'     : "MAIN_MENU"
                        }] + submit_quick_replies(["Confirm", "Enter URL"]))

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


def toggle_opt_out(sender_id, is_optout=True):
    logger.info("toggle_opt_out(sender_id=%s, is_optout=%s)" % (sender_id, is_optout))

    is_prev_oo = False
    conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('SELECT id FROM blacklisted_users WHERE `fb_psid` = ?;', (sender_id,))
        row = cur.fetchone()

        is_prev_oo = True if row is not None else False

        if is_prev_oo == False and is_optout == True:
            cur.execute('INSERT INTO blacklisted_users (id, fb_psid, added) VALUES (NULL, ?, ?);', (sender_id, int(time.time())))
            conn.commit()

        elif is_prev_oo == True and is_optout == False:
            cur.execute('DELETE FROM blacklisted_users WHERE `fb_psid` = ?;', (sender_id,))
            conn.commit()


        conn.close()


    except sqlite3.Error as er:
        logger.info("::::::opt_out[cur.execute] sqlite3.Error - %s" % (er.message,))

    finally:
        if conn:
            conn.close()

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('UPDATE `fbbot_logs` SET `enabled` = %s WHERE `chat_id` = %s;', (1 if is_optout else 0, sender_id,))
            conn.commit()

    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()

    if is_optout:
        send_text(sender_id, "You have opted out of Gamebots & will no longer recieve messages from Gamebots. If you need help visit facebook.com/gamebotsc", opt_out_quick_replies())
        return "OK", 200


def clear_session_dub(sender_id):
    logger.info("clear_session_dub(sender_id=%s)" % (sender_id,))

    set_session_item(sender_id)

    if get_session_trade_url(sender_id) == "_{PENDING}_":
        set_session_trade_url(sender_id)


    set_session_state(sender_id)



def purchase_item(sender_id, payment):
    logger.info("purchase_item(sender_id=%s, payment=%s)" % (sender_id, payment))
    send_tracker(fb_psid=sender_id, category="fb-purchase")
    send_tracker(fb_psid=sender_id, category="transaction", label="fb-purchase")

    purchase_id = 0
    item_id = re.match(r'^PURCHASE_ITEM\-(?P<item_id>\d+)$', payment['payload']).group('item_id')
    item_name = None
    customer_email = payment['requested_user_info']['contact_email']
    amount = payment['amount']['amount']
    fb_payment_id = payment['payment_credential']['fb_payment_id']
    provider = payment['payment_credential']['provider_type']
    charge_id = payment['payment_credential']['charge_id']

    full_name, f_name, l_name = get_session_name(sender_id)

    conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
    try:
        with conn:
            cur = conn.cursor(mdb.cursors.DictCursor)
            cur.execute('SELECT `id`, `name`, `info`, `image_url`, `price` FROM `fb_products` WHERE `id` = %s LIMIT 1;', (item_id,))
            row = cur.fetchone()

            if row is not None:
                item_name = row['asset_name']

            full_name, f_name, l_name = get_session_name(sender_id)
            cur.execute('INSERT INTO `fb_purchases` (`id`, `fb_psid`, `first_name`, `last_name`, `email`, `item_id`, `amount`, `fb_payment_id`, `provider`, `charge_id`, `added`) VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP());', (sender_id, f_name or "", l_name or "", customer_email, item_id, amount, fb_payment_id, provider, charge_id))
            conn.commit()

            cur.execute('SELECT @@IDENTITY AS `id` FROM `fb_purchases`;')
            row = cur.fetchone()
            purchase_id = row['id']


    except mdb.Error, e:
        logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

    finally:
        if conn:
            conn.close()


    if purchase_id != 0:
        set_session_deposit(sender_id, amount)
        set_session_purchase(sender_id, purchase_id)
        flip_id = get_session_item(sender_id)

        try:
            conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute('INSERT INTO payments (id, fb_psid, email, item_id, flip_id, amount, fb_payment_id, provider, charge_id, added) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);', (purchase_id, sender_id, customer_email, item_id, flip_id, amount, fb_payment_id, provider, charge_id, int(time.time())))
            conn.commit()

        except sqlite3.Error as er:
            logger.info("::::::payment[cur.execute] sqlite3.Error - %s" % (er.message,))

        finally:
            if conn:
                conn.close()


    # -- state 10 means purchased, but no trade url yet…
    set_session_state(sender_id, Const.SESSION_STATE_PURCHASED_ITEM)
    payload = {
        'channel'  : "#gamebots-purchases",
        'username' : "gamebotsc",
        'icon_url' : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
        'text': "*{user}* just added ${amount:.2f} in credits.".format(user=sender_id if full_name is None else full_name, amount=float(amount)),
    }
    response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

    time.sleep(3.33)

    min_price, max_price = price_range_for_deposit(amount)
    send_text(sender_id, "You have unlocked high tier wins. Happy flipping!", main_menu_quick_reply())


def item_setup(sender_id, item_id, preview=False):
    logger.info("item_setup(sender_id=%s, item_id=%s, preview=%s)" % (sender_id, item_id, preview))

    if flips_last_day(sender_id) >= Const.MAX_FLIPS_PER_DAY:
        send_text(sender_id, "To Flip high tier items you must make a deposit. Get 2 More Wins Below or wait 24 hours.", main_menu_quick_reply())
        return "OK", 200

    set_session_item(sender_id, item_id)
    item = get_item_details(item_id)
    logger.info("ITEM --> %s", item)

    if (item['price'] > 1.00 and get_session_deposit(sender_id) < 1.00) or deposit_amount_for_price(item['price']) > get_session_deposit(sender_id):
        send_text(sender_id, "To Flip high tier items you must make a deposit. Get 2 More Wins Below or wait 24 hours.")
        send_pay_wall(sender_id, item)
        send_video(sender_id, "http://prebot.me/videos/MobileLegends.mp4")
        send_ad_card(sender_id)
        return "OK", 200

    if item is None:
        send_text(sender_id, "Can't find that item! Try flipping again", main_menu_quick_reply())
        return "OK", 200

    if get_session_bonus(sender_id) is not None:
        coin_flip_results(sender_id, item_id)
        return "OK", 200

    if wins_last_day(sender_id) >= Const.MAX_TIER_WINS * win_mulitplier(sender_id):
        send_pay_wall(sender_id, item)
        send_video(sender_id, "http://prebot.me/videos/MobileLegends.mp4")
        send_ad_card(sender_id)


    else:
        if preview:
            send_card(
                recipient_id=sender_id,
                title=item['asset_name'].encode('utf8'),
                image_url=item['image_url'],
                subtitle="${price:.2f}".format(price=item['price']) if sender_id == "1219553058088713" else None
            )
        coin_flip_results(sender_id, item_id)



# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#


@app.route('/<bot_webhook>/', methods=['GET'])
def verify(bot_webhook):
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= VERIFY (%s)->%s [%s]\n" % (bot_webhook, request.args.get('hub.mode'), request))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == Const.VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args['hub.challenge'], 200

    return "OK", 200


@app.route('/tac0/webhook/', methods=['GET'])
def tac0_verify():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= VERIFY ->%s [%s]\n" % (request.args.get('hub.mode'), request))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.args.get('hub.mode') == "subscribe" and request.args.get('hub.challenge'):
        if not request.args.get('hub.verify_token') == Const.VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args['hub.challenge'], 200

    return "OK", 200


@app.route('/tac0/webhook/', methods=['POST'])
def tac0_webhook():
    bot_type = bot_webhook_type("tac0")

    data = request.get_json()

    logger.info("[=-=-=-=-=-=-=-[POST DATA]-=-=-=-=-=-=-=-=]")
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    logger.info(data)

    if data['object'] == "page":
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                if 'delivery' in messaging_event:  # delivery confirmation
                    logger.info("-=- DELIVERY CONFIRM -=-")
                    return "OK", 200

                if 'read' in messaging_event:  # read confirmation
                    logger.info("-=- READ CONFIRM -=- %s" % (messaging_event,))
                    # send_tracker(fb_psid=messaging_event['sender']['id'], category="read-receipt")
                    # send_tracker(fb_psid=messaging_event['sender']['id'], category="active")
                    return "OK", 200

                if 'optin' in messaging_event:  # optin confirmation
                    logger.info("-=- OPT-IN -=-")
                    return "OK", 200

                sender_id = messaging_event['sender']['id']
                message = messaging_event['message'] if 'message' in messaging_event else None
                message_id = message['mid'] if message is not None and 'mid' in message else messaging_event['id'] if 'id' not in entry else entry['id']
                quick_reply = messaging_event['message']['quick_reply']['payload'] if 'message' in messaging_event and 'quick_reply' in messaging_event['message'] and 'quick_reply' in messaging_event['message']['quick_reply'] else None  # (if 'message' in messaging_event and 'quick_reply' in messaging_event['message'] and 'payload' in messaging_event['message']['quick_reply']) else None:
                logger.info("QR --> %s" % (quick_reply or None,))

                referral = None if 'referral' not in messaging_event else messaging_event['referral']['ref'].encode('ascii', 'ignore')
                if referral is None and 'postback' in messaging_event and 'referral' in messaging_event['postback']:
                    referral = messaging_event['postback']['referral']['ref'].encode('ascii', 'ignore')

                # -- insert to log
                write_message_log(sender_id, message_id, {key: messaging_event[key] for key in messaging_event if key != 'timestamp'})
                sync_session_deposit(sender_id)

                # -- new entry
                if get_session_state(sender_id) == Const.SESSION_STATE_NEW_USER:
                    logger.info("----------=NEW SESSION @(%s)=----------" % (time.strftime('%Y-%m-%d %H:%M:%S')))
                    send_tracker(fb_psid=sender_id, category="sign-up")

                    set_session_state(sender_id)
                    set_session_bot_type(sender_id, bot_type)
                    send_text(sender_id, "Welcome to {bot_title}. To opt-out of further messaging, type exit, quit, or stop.".format(bot_title=bot_title(bot_type)))
                    graph = fb_graph_user(sender_id)
                    if graph is not None:
                        set_session_name(sender_id, graph['first_name'] or "", graph['last_name'] or "")

                # -- existing
                elif get_session_state(sender_id) >= Const.SESSION_STATE_HOME and get_session_state(sender_id) < Const.SESSION_STATE_PURCHASED_ITEM:
                    if referral is not None:
                        send_tracker(fb_psid=sender_id, category="referral", label=referral)
                        logger.info("REFERRAL ---> %s", (referral,))
                        return "OK", 200

                    # -- actual message w/ txt
                    if 'message' in messaging_event:
                        logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECIEVED ->%s" % (messaging_event['sender']))

                        send_card(
                            recipient_id=sender_id,
                            title="Deposit Items",
                            image_url="https://i.imgur.com/OKbWbDm.png",
                            buttons=[
                                {
                                    'type'                : "web_url",
                                    'url'                 : "http://lmon.us/claim.php?fb_psid={fb_psid}".format(fb_psid=sender_id),
                                    'title'               : "Deposit",
                                    'webview_height_ratio': "tall"
                                }, {
                                    'type': "element_share"
                                }
                            ],
                            quick_replies=[
                                {
                                    'content_type': "text",
                                    'title'       : "Deposit",
                                    'payload'     : "TAC0__DEPOSIT"
                                }, {
                                    'content_type': "text",
                                    'title'       : "Share",
                                    'payload'     : "TAC0__SHARE"
                                }, {
                                    'content_type': "text",
                                    'title'       : "Lmon8",
                                    'payload'     : "TAC0__LMON8"
                                }
                            ]
                        )

                        # ------- POSTBACK BUTTON MESSAGE
                        if 'postback' in messaging_event:  # user clicked/tapped "postback" button in earlier message
                            logger.info("POSTBACK --> %s" % (messaging_event['postback']['payload']))
                            tac0_payload(sender_id, messaging_event['postback']['payload'])
                            return "OK", 200

                        # ------- QUICK REPLY BUTTON / POSTBACK BUTTON MESSAGE
                        if 'quick_reply' in message and message['quick_reply']['payload'] is not None or 'postback' in messaging_event:
                            logger.info("QR --> %s" % (messaging_event['message']['quick_reply']['payload']))
                            tac0_payload(sender_id, messaging_event['message']['quick_reply']['payload'])
                            return "OK", 200

                        # ------- TYPED TEXT MESSAGE
                        if 'text' in message:
                            # recieved_text_reply(sender_id, message['text'])
                            return "OK", 200

                        # ------- ATTACHMENT SENT
                        if 'attachments' in message:
                            for attachment in message['attachments']:
                                pass
                                # recieved_attachment(sender_id, attachment['type'], attachment['payload'])
                            return "OK", 200

    return "OK", 200


def tac0_payload(sender_id, payload):
    logger.info("tac0_payload(sender_id=%s, payload=%s)" % (sender_id, payload))

    bot_type = get_session_bot_type(sender_id)
    if payload == "TAC0__LMON8":
        pass



@app.route('/tac0/steam/', methods=['POST'])
def tac0_steam():
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/tac0/steam/'" )
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.STEAM_TOKEN:
        logger.info("TOKEN VALID!")

        fb_psid = request.form['fb_psid']
        steam_id64 = request.form['steam_id64']

        send_text(fb_psid, "Steam auth complete!\n\nSubmit your items to this trade URL, you have 15 minutes\n\n{trade_url}".format(trade_url="https://steamcommunity.com/tradeoffer/new/?partner=317337787&token=5W7Z44R-s"))

    return "OK", 200


@app.route('/<bot_webhook>/', methods=['POST'])
def webhook(bot_webhook):
    bot_type = bot_webhook_type(bot_webhook)

    data = request.get_json()

    logger.info("[=-=-=-=-=-=-=-[POST DATA]-=-=-=-=-=-=-=-=]")
    logger.info("[=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=]")
    logger.info(data)

    if data['object'] == "page":
        for entry in data['entry']:
            for messaging_event in entry['messaging']:
                if 'delivery' in messaging_event:  # delivery confirmation
                    logger.info("-=- DELIVERY CONFIRM -=-")
                    return "OK", 200

                if 'read' in messaging_event:  # read confirmation
                    logger.info("-=- READ CONFIRM -=- %s" % (messaging_event,))
                    # send_tracker(fb_psid=messaging_event['sender']['id'], category="read-receipt")
                    return "OK", 200

                if 'optin' in messaging_event:  # optin confirmation
                    logger.info("-=- OPT-IN -=-")
                    return "OK", 200

                sender_id = messaging_event['sender']['id']
                message = messaging_event['message'] if 'message' in messaging_event else None
                message_id = message['mid'] if message is not None and 'mid' in message else messaging_event['id'] if 'id' not in entry else entry['id']
                quick_reply = messaging_event['message']['quick_reply']['payload'] if 'message' in messaging_event and 'quick_reply' in messaging_event['message'] and 'quick_reply' in messaging_event['message']['quick_reply'] else None  # (if 'message' in messaging_event and 'quick_reply' in messaging_event['message'] and 'payload' in messaging_event['message']['quick_reply']) else None:
                logger.info("QR --> %s" % (quick_reply or None,))

                if sender_id == "1395098457218675" or sender_id == "1034583493310197" or sender_id == "1467685003302859" or sender_id == "1439329449472645" or sender_id == "1332667396813897" or sender_id == "1155606227881526":
                    logger.info("-=- BYPASS-USER -=-")
                    return "OK", 200

                referral = None if 'referral' not in messaging_event else messaging_event['referral']['ref'].encode('ascii', 'ignore')
                if referral is None and 'postback' in messaging_event and 'referral' in messaging_event['postback']:
                    referral = messaging_event['postback']['referral']['ref'].encode('ascii', 'ignore')


                if bot_type == Const.BOT_TYPE_MOBILELEGEND:
                    set_session_state(sender_id, 1)
                    set_session_bot_type(sender_id, Const.BOT_TYPE_MOBILELEGEND)
                    payload = None

                    # ------- POSTBACK BUTTON MESSAGE
                    if 'postback' in messaging_event:  # user clicked/tapped "postback" button in earlier message
                        payload = messaging_event['postback']['payload']
                        logger.info("POSTBACK --> %s" % (payload,))

                    if 'message' in messaging_event:
                        message = messaging_event['message']
                        if 'quick_reply' in message and message['quick_reply']['payload'] is not None:
                            payload = message['quick_reply']['payload']
                            logger.info("QR --> %s" % (payload, ))

                        if 'text' in message and payload is None:
                            message_text = message['text']

                            if get_session_trade_url(sender_id) == "_{PENDING}_":
                                set_session_trade_url(sender_id, message_text)
                                send_text(sender_id, "Your username / email has been set to:{trade_url}".format(trade_url=message_text))

                                send_carousel(
                                    recipient_id=sender_id,
                                    elements=[{
                                        'title'    : "Open Mobile Legends",
                                        'subtitle' : "Tap here to launch",
                                        'image_url': "https://i.ytimg.com/vi/WkMgq2Y9c4o/maxresdefault.jpg",
                                        'item_url' : "http://taps.io/BvqCg",
                                        'buttons'  : [{
                                            'type'                : "web_url",
                                            'url'                 : "http://taps.io/BvqCg",
                                            'title'               : "Launch",
                                            'webview_height_ratio': "full"
                                        }]}],
                                    quick_replies=[{
                                        'content_type': "text",
                                        'title'       : "Next Item",
                                        'payload'     : "NEXT_ITEM"
                                    }]
                                )

                            else:
                                item = mobile_legend_item(sender_id)
                                send_carousel(
                                    recipient_id=sender_id,
                                    elements=[{
                                        'title'    : item[1].encode('utf8'),
                                        'subtitle' : "${price:.2f}".format(price=float(item[1])),
                                        'image_url': item[3],
                                        'item_url' : None,
                                        'buttons'  : [{
                                            'type'   : "postback",
                                            'payload': "FLIP_COIN-{item_id}".format(item_id=item[0]),
                                            'title'  : "Flip to Win Items"
                                        }]}],
                                    quick_replies=[{
                                        'content_type': "text",
                                        'title'       : "Next Item",
                                        'payload'     : "NEXT_ITEM"
                                    }]
                                )


                    if payload == "WELCOME_MESSAGE":
                        logger.info("----------=NEW SESSION @(%s)=----------" % (time.strftime('%Y-%m-%d %H:%M:%S')))
                        send_video(sender_id, "http://prebot.me/videos/MobileLegends.mp4")

                        send_text(sender_id, "Welome to Mobile Legends on Messenger! Flip here to win items.")

                        item = mobile_legend_item(sender_id)
                        send_carousel(
                            recipient_id=sender_id,
                            elements=[{
                                'title'    : item[1].encode('utf8'),
                                'subtitle' : "${price:.2f}".format(price=float(item[1])),
                                'image_url': item[3],
                                'item_url' : None,
                                'buttons'  : [{
                                    'type'   : "postback",
                                    'payload': "FLIP_COIN-{item_id}".format(item_id=item[0]),
                                    'title'  : "Flip to Win Items"
                            }]}],
                            quick_replies=[{
                                'content_type': "text",
                                'title'       : "Next Item",
                                'payload'     : "NEXT_ITEM"
                            }]
                        )

                    elif payload == "NEXT_ITEM":
                        item = mobile_legend_item(sender_id)
                        send_carousel(
                            recipient_id=sender_id,
                            elements=[{
                                'title'    : item[2].encode('utf8'),
                                'subtitle' : "${price:.2f}".format(price=float(item[1])),
                                'image_url': item[3],
                                'item_url' : None,
                            }],
                        )

                        if item is not None:
                            send_image(sender_id, "https://i.imgur.com/qJu6BtA.gif")
                            outcome = random.uniform(0, 1) >= 0.75
                            if outcome is True:
                                send_text(sender_id, "You won {item_name}!\n\nEnter your Mobile Legends username or email.".format(item_name=item[2]))
                                set_session_trade_url(sender_id, "_{PENDING}_")

                            else:
                                send_text(
                                    recipient_id=sender_id,
                                    message_text="TRY AGAIN! You lost {item_name}.".format(item_name=item[2]),
                                    quick_replies=[{
                                        'content_type': "text",
                                        'title'       : "Next Item",
                                        'payload'     : "NEXT_ITEM"
                                    }]
                                )

                        else:
                            send_text(sender_id, "Couldn't find that item!")

                    elif re.search(r'FLIP_COIN-(\d+)', payload or "") is not None:
                        item_id = re.match(r'FLIP_COIN-(?P<item_id>\d+)', payload or "").group('item_id')
                        item = None

                        with open("/var/www/FacebookBot/FacebookBot/data/csv/mobile-legend.csv", 'rb') as csvfile:
                            reader = csv.reader(csvfile)
                            for row in reader:
                                if row[0] == item_id:
                                    item = row
                                    break

                        if item is not None:
                            send_image(sender_id, "https://i.imgur.com/qJu6BtA.gif")
                            outcome = random.uniform(0, 1) >= 0.75
                            if outcome is True:
                                send_text(sender_id, "You won {item_name}!\n\nEnter your Mobile Legends username or email.".format(item_name=item[2]))
                                set_session_trade_url(sender_id, "_{PENDING}_")

                            else:
                                send_text(
                                    recipient_id=sender_id,
                                    message_text="TRY AGAIN! You lost {item_name}.".format(item_name=item[2]),
                                    quick_replies=[{
                                        'content_type': "text",
                                        'title'       : "Next Item",
                                        'payload'     : "NEXT_ITEM"
                                    }]
                                )

                        else:
                            send_text(sender_id, "Couldn't find that item!")

                    return "OK", 200


                # -- insert to log
                write_message_log(sender_id, message_id, {key: messaging_event[key] for key in messaging_event if key != 'timestamp'})
                sync_session_deposit(sender_id)

                if sender_id not in Const.ADMIN_FB_PSID and os.getenv('FBBOT_BYPASS', 'False') == 'True':
                    send_text(sender_id, "{bot_title} is currently down for maintenance.".format(bot_title=bot_title(bot_type)))
                    return "OK", 200

                if 'payment' in messaging_event:  # payment result
                    logger.info("-=- PAYMENT -=-")
                    set_session_state(sender_id, Const.SESSION_STATE_PURCHASED_ITEM)
                    purchase_item(sender_id, messaging_event['payment'])
                    return "OK", 200

                # -- new entry
                if get_session_state(sender_id) == Const.SESSION_STATE_NEW_USER:
                    logger.info("----------=NEW SESSION @(%s)=----------" % (time.strftime('%Y-%m-%d %H:%M:%S')))
                    send_tracker(fb_psid=sender_id, category="sign-up")

                    set_session_state(sender_id)
                    set_session_bot_type(sender_id, bot_type)
                    send_text(sender_id, "Welcome to {bot_title}. To opt-out of further messaging, type exit, quit, or stop.".format(bot_title=bot_title(bot_type)))
                    send_image(sender_id, "https://i.imgur.com/mWKd5Ag.gif" if bot_type == Const.BOT_TYPE_LORDHELIX else "https://i.imgur.com/uw9dX1w.gif" if bot_type == Const.BOT_TYPE_OZZNY09 else "https://i.imgur.com/pOBhKza.gif" if bot_type == Const.BOT_TYPE_SUFFERCSGO else "https://i.imgur.com/2LViM6t.gif" if bot_type == Const.BOT_TYPE_TELLFULGAMES else "https://i.imgur.com/wfgNUl6.gif" if bot_type == Const.BOT_TYPE_VASCO else "https://media.giphy.com/media/K0WEtL8FbxgYM/giphy.gif" if bot_type == Const.BOT_TYPE_CSGOHOPE or bot_type == Const.BOT_TYPE_JAN else "http://i.imgur.com/UJpnZeD.gif" if bot_type == Const.BOT_TYPE_ITSNANCY else "https://i.imgur.com/CeFy6C0.gif" if bot_type == Const.BOT_TYPE_MAINGAME else "http://i.imgur.com/QHHovfa.gif")
                    # default_carousel(sender_id)
                    graph = fb_graph_user(sender_id)
                    if graph is not None:
                        set_session_name(sender_id, graph['first_name'] or "", graph['last_name'] or "")

                    enter_giveaway(sender_id)

                # -- existing
                elif get_session_state(sender_id) >= Const.SESSION_STATE_HOME and get_session_state(sender_id) < Const.SESSION_STATE_PURCHASED_ITEM:
                    set_session_bot_type(sender_id, bot_type)
                    if referral is not None:
                        send_tracker(fb_psid=sender_id, category="referral", label=referral)
                        logger.info("REFERRAL ---> %s", (referral,))
                        if referral.split("/")[-1].startswith("gb"):
                            if valid_purchase_code(sender_id, referral):
                                send_tracker(fb_psid=sender_id, category="point-purchase")
                                send_tracker(fb_psid=sender_id, category="transaction", label="point-purchase")

                                purchase_code = referral.split("/")[-1]
                                full_name, first_name, last_name = get_session_name(sender_id)
                                conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
                                try:
                                    with conn:
                                        cur = conn.cursor(mdb.cursors.DictCursor)
                                        cur.execute('UPDATE `fb_purchases` SET `fb_psid` = %s, `first_name` = %s, `last_name` = %s WHERE `charge_id` = %s ORDER BY `added` DESC LIMIT 1;', (sender_id, first_name, last_name, purchase_code))
                                        conn.commit()
                                        cur.execute('SELECT `amount` FROM `fb_purchases` WHERE `charge_id` = %s ORDER BY `added` DESC LIMIT 1;', (purchase_code,))
                                        row = cur.fetchone()
                                        send_text(sender_id, "Your purchase for ${amount:.2f} has been applied!.".format(amount=row['amount']))

                                except mdb.Error, e:
                                    logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

                                finally:
                                    if conn:
                                        conn.close()

                                default_carousel(sender_id)

                        elif referral.split("/")[-1].startswith("giveaway") or referral.split("/")[-1].startswith("ga"):
                            enter_giveaway(sender_id)

                        elif referral.split("/")[-1].startswith("support"):
                            enter_support(sender_id)

                        else:
                            if valid_bonus_code(sender_id, referral):
                                set_session_bonus(sender_id, referral.split("/")[-1])

                                row = next_coin_flip_item(sender_id)
                                if row is not None:
                                    item_id = row['id']
                                    set_session_item(sender_id, item_id)
                                    item = get_item_details(item_id)
                                    logger.info("ITEM --> %s", item)

                                    send_text(sender_id, "You have unlocked a Mystery Flip.")
                                    send_tracker(fb_psid=sender_id, category="transaction", label="mystery-flip")
                                    send_card(
                                        recipient_id=sender_id,
                                        title=row['asset_name'].encode('utf8'),
                                        subtitle="${price:.2f}".format(price=item['price']) if sender_id == "1219553058088713" else None,
                                        image_url=row['image_url'],
                                        buttons=[{
                                            'type'   : "postback",
                                            'payload': "FLIP_COIN-{item_id}".format(item_id=item_id),
                                            'title'  : "Flip Coin"
                                        }, {
                                            'type'   : "postback",
                                            'payload': "MAIN_MENU",
                                            'title'  : "Cancel"
                                        }]
                                    )

                                else:
                                    send_text(sender_id, "You can only use 1 Mystery Flip per day. Please try again in 24 hours.")
                                    default_carousel(sender_id)

                            else:
                                send_text(sender_id, "You have already used this Mystery Flip.")
                                default_carousel(sender_id)

                        return "OK", 200

                    # ------- POSTBACK BUTTON MESSAGE
                    if 'postback' in messaging_event:  # user clicked/tapped "postback" button in earlier message
                        logger.info("POSTBACK --> %s" % (messaging_event['postback']['payload']))
                        handle_payload(sender_id, Const.PAYLOAD_TYPE_POSTBACK, messaging_event['postback']['payload'])
                        return "OK", 200

                    # -- actual message w/ txt
                    if 'message' in messaging_event:
                        logger.info("=-=-=-=-=-=-=-=-=-=-=-=-= MESSAGE RECIEVED ->%s" % (messaging_event['sender']))

                        # ------- QUICK REPLY BUTTON
                        if 'quick_reply' in message and message['quick_reply']['payload'] is not None:
                            logger.info("QR --> %s" % (messaging_event['message']['quick_reply']['payload']))
                            handle_payload(sender_id, Const.PAYLOAD_TYPE_QUICK_REPLY, messaging_event['message']['quick_reply']['payload'])
                            return "OK", 200

                        # ------- TYPED TEXT MESSAGE
                        if 'text' in message:
                            recieved_text_reply(sender_id, message['text'])
                            return "OK", 200

                        # ------- ATTACHMENT SENT
                        if 'attachments' in message:
                            for attachment in message['attachments']:
                                recieved_attachment(sender_id, attachment['type'], attachment['payload'])
                            return "OK", 200

                    set_session_state(sender_id)
                    default_carousel(sender_id)

                else:
                    set_session_state(sender_id)
                    default_carousel(sender_id)

    return "OK", 200


@app.route('/<bot_webhook>/paypal/', methods=['POST'])
def paypal(bot_webhook):
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/%s/paypal'" % (bot_webhook,))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.PAYPAL_TOKEN:
        logger.info("TOKEN VALID!")

        fb_psid = request.form['fb_psid']
        amount = float(request.form['amount'])
        logger.info("fb_psid=%s, amount=%s" % (fb_psid, amount))
        send_tracker(fb_psid=fb_psid, category="paypal-purchase")
        set_session_deposit(fb_psid, int(round(amount)))

        full_name, f_name, l_name = get_session_name(fb_psid)

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('INSERT INTO `fb_purchases` (`id`, `fb_psid`, `first_name`, `last_name`, `amount`, `added`) VALUES (NULL, %s, %s, %s, %s, UTC_TIMESTAMP());', (fb_psid, f_name, l_name, amount))
                conn.commit()

                cur.execute('SELECT @@IDENTITY AS `id` FROM `fb_purchases`;')
                row = cur.fetchone()
                purchase_id = row['id']


        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        min_price, max_price = price_range_for_deposit(amount)
        send_text(fb_psid, "You have unlocked high tier wins. Happy flipping!", main_menu_quick_reply())

        if amount >= 1.00:
            payload = {
                'channel' : "#gamebots-purchases",
                'username': "gamebotsc",
                'icon_url': "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
                'text'    : "*{user}* just added ${amount:.2f} in credits.".format(user=fb_psid if full_name is None else full_name, amount=amount),
            }
            response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

    return "OK", 200


@app.route('/<bot_webhook>/bonus-flip/', methods=['POST'])
def bonus_flip(bot_webhook):
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/%s/bonus-flip/'" % (bot_webhook,))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.BONUS_TOKEN:
        logger.info("TOKEN VALID!")

        if 'bonus_code' in request.form:
            bonus_code = request.form['bonus_code']
            logger.info("bonus_code=%s" % (bonus_code,))

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('SELECT `id` FROM `bonus_codes` WHERE `code` = %s AND `added` > DATE_SUB(UTC_TIMESTAMP(), INTERVAL 24 HOUR) LIMIT 1;', (bonus_code,))
                    if cur.fetchone() is None:
                        cur.execute('INSERT INTO `bonus_codes` (`id`, `code`, `added`) VALUES (NULL, %s, UTC_TIMESTAMP());', (bonus_code,))
                        conn.commit()

                        cur.execute('SELECT @@IDENTITY AS `id` FROM `bonus_codes`;')
                        row = cur.fetchone()

                    else:
                        return "code-exists", 200

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

    return "OK", 200


@app.route('/<bot_webhook>/giveaway/', methods=['POST'])
def giveaway(bot_webhook):
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/%s/giveaway/'" % (bot_webhook,))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.GIVAWAY_TOKEN:
        logger.info("TOKEN VALID!")

        if 'fb_psid' in request.form:
            fb_psid = request.form['fb_psid']
            logger.info("fb_psid=%s" % (fb_psid,))
            trade_url = get_session_trade_url(fb_psid)

            item_name = None

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('SELECT `item_name` FROM `giveaways` WHERE `fb_psid` = %s LIMIT 1;', (fb_psid,))
                    row = cur.fetchone()
                    if row is not None:
                        item_name = row['item_name']
                        cur.execute('UPDATE `giveaways` SET `won` = 1 WHERE `fb_psid` = %s LIMIT 1;', (fb_psid,))
                        conn.commit()

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()


            set_session_state(fb_psid, Const.SESSION_STATE_GIVEAWAY_TRADE_URL)
            send_text(fb_psid, "Congratulations, you've won today's giveaway item\n{item_name}".format(item_name=item_name))
            if trade_url is None:
                send_text(fb_psid, "Please enter your steam trade url to claim")

            else:
                send_text(fb_psid, "Your Steam Trade URL is set to:\n\n{trade_url}".format(trade_url=trade_url), quick_replies=submit_quick_replies(["Confirm", "Enter URL"]))


    return "OK", 200



@app.route('/<bot_webhook>/points-purchase/', methods=['POST'])
def points_purchase(bot_webhook):
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\  '/%s/points-purchase/'" % (bot_webhook,))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form),))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.POINTS_TOKEN:
        logger.info("TOKEN VALID!")

        if 'purchase_code' in request.form and 'amount' in request.form:
            purchase_code = request.form['purchase_code']
            amount = request.form['amount']
            logger.info("amount=%s" % (amount,))

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('SELECT `id` FROM `fb_purchases` WHERE `charge_id` = %s AND `added` > DATE_SUB(UTC_TIMESTAMP(), INTERVAL 24 HOUR) LIMIT 1;', (purchase_code,))
                    # if cur.fetchone() is None:
                    cur.execute('INSERT INTO `fb_purchases` (`id`, `amount`, `charge_id`, `added`) VALUES (NULL, %s, %s, UTC_TIMESTAMP());', (request.form['amount'], purchase_code,))
                    conn.commit()

                    cur.execute('SELECT @@IDENTITY AS `id` FROM `fb_purchases`;')
                    row = cur.fetchone()

                    # else:
                    #     return "code-exists", 200

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

    return "OK", 200


@app.route('/<bot_webhook>/slack/', methods=['POST'])
def slack(bot_webhook):
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("=-=-=-=-=-= POST --\»  '/%s/slack/'" % (bot_webhook,))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")
    logger.info("request.form=%s" % (", ".join(request.form)))
    logger.info("=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=")

    if request.form['token'] == Const.SLACK_TOKEN:
        if re.search('^(\d+)\ close$', request.form['text'].lower()) is not None:
            fb_psid = re.match(r'(?P<fb_psid>\d+)\ close$', request.form['text'].lower()).group('fb_psid')
            conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            try:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('UPDATE sessions SET support = 0 WHERE fb_psid = ?;', (fb_psid,))
                conn.commit()
                set_session_state(fb_psid, Const.SESSION_STATE_SUPPORT)
                send_text(fb_psid, "Support ticket closed", main_menu_quick_reply())

            except sqlite3.Error as er:
                logger.info("::::::set_session_state[cur.execute] sqlite3.Error - %s" % (er.message,))

            finally:
                if conn:
                    conn.close()

        elif re.search('^(\d+)\ reset$', request.form['text'].lower()) is not None:
            fb_psid = re.match(r'(?P<fb_psid>\d+)\ reset$', request.form['text'].lower()).group('fb_psid')
            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('UPDATE `item_winners` SET `limiter` = 0 WHERE `fb_id` = %s AND `added` >= DATE_SUB(NOW(), INTERVAL 24 HOUR);', (fb_psid,))
                    conn.commit()
            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
            finally:
                if conn:
                    conn.close()



        elif re.search('^(\d+)\ deposit\ (\d+)$', request.form['text']) is not None:
            fb_psid = re.match(r'(?P<fb_psid>\d+)\ deposit\ (?P<amount>\d+)$', request.form['text']).group('fb_psid')
            amount = int(re.match(r'(?P<fb_psid>\d+)\ deposit\ (?P<amount>\d+)$', request.form['text']).group('amount'))

            set_session_deposit(fb_psid, amount)

            full_name, f_name, l_name = get_session_name(fb_psid)

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('INSERT INTO `fb_purchases` (`id`, `fb_psid`, `first_name`, `last_name`, `amount`, `added`) VALUES (NULL, %s, %s, %s, %s, UTC_TIMESTAMP());', (fb_psid, f_name, l_name, amount))
                    conn.commit()

                    cur.execute('SELECT @@IDENTITY AS `id` FROM `fb_purchases`;')
                    row = cur.fetchone()
                    purchase_id = row['id']


            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

            send_text(fb_psid, "You have been rewarded a ${amount:.2f} deposit for the next 24 hours. Happy flipping!".format(amount=amount), main_menu_quick_reply())

        elif re.search('^(\d+)\ (.*)$', request.form['text']) is not None:
            fb_psid = re.match(r'(?P<fb_psid>\d+)\ (?P<message_text>.*)$', request.form['text']).group('fb_psid')
            message_text = re.match(r'(?P<fb_psid>\d+)\ (?P<message_text>.*)$', request.form['text']).group('message_text')

            send_text(fb_psid, "Support says:\n{message_text}".format(message_text=message_text), main_menu_quick_reply())

            conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            try:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('UPDATE sessions SET support = 0 WHERE fb_psid = ?;', (fb_psid,))
                conn.commit()
                set_session_state(fb_psid, Const.SESSION_STATE_SUPPORT)

            except sqlite3.Error as er:
                logger.info("::::::set_session_state[cur.execute] sqlite3.Error - %s" % (er.message,))

            finally:
                if conn:
                    conn.close()

    return "OK", 200


# -- =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-= --#




def recieved_quick_reply(sender_id, quick_reply):
    logger.info("recieved_quick_reply(sender_id=%s, quick_reply=%s)" % (sender_id, quick_reply))
    logger.info("QR --> %s" % (quick_reply,))

    handle_payload(sender_id, Const.PAYLOAD_TYPE_OTHER, quick_reply)


def recieved_trade_url(sender_id, url, action=Const.TRADE_URL_FLIP_ITEM):
    logger.info("recieved_trade_url(sender_id=%s, url=%s, action=%s)" % (sender_id, url, action))

    if action == Const.TRADE_URL_PURCHASE:
        purchase_id, flip_id = get_session_purchase(sender_id)

        if get_session_state(sender_id) == Const.SESSION_STATE_PURCHASED_TRADE_URL:
            send_text(sender_id, "Your Steam Trade URL is set to:\n\n{url}".format(url=url), quick_replies=submit_quick_replies())


    elif action == Const.TRADE_URL_FLIP_ITEM:
        #if get_session_state(sender_id) == Const.SESSION_STATE_FLIP_TRADE_URL:
        send_text(sender_id, "Your Steam Trade URL is set to:\n\n{url}".format(url=url), quick_replies=submit_quick_replies(["Confirm", "Enter URL"]))





def handle_payload(sender_id, payload_type, payload):
    logger.info("handle_payload(sender_id=%s, payload_type=%s, payload=%s)" % (sender_id, payload_type, payload))

    bot_type = get_session_bot_type(sender_id)
    if payload == "MAIN_MENU":
        clear_session_dub(sender_id)
        default_carousel(sender_id)

    elif payload == "MAIN_MENU_ALT":
        clear_session_dub(sender_id)
        default_carousel(sender_id)


    elif payload == "WELCOME_MESSAGE":
        logger.info("----------=NEW SESSION @(%s)=----------" % (time.strftime('%Y-%m-%d %H:%M:%S')))
        send_tracker("sign-up", sender_id, "")
        default_carousel(sender_id)


    elif re.search('DEPOSIT-(\d+)', payload) is not None:
        amount = int(re.match(r'DEPOSIT-(?P<amount>\d+)', payload).group('amount'))
        min_price, max_price = price_range_for_deposit(amount)
        pay_wall_deposit(sender_id, min_price, max_price)


    elif payload == "NEXT_ITEM":
        #send_tracker(fb_psid=sender_id, category="next-item")

        if random.uniform(0, 1) > 0.80:
            if random.uniform(0, 1) > 0.80:
                send_install_card(sender_id)

            else:
                send_discord_card(sender_id)

        else:
            row = next_coin_flip_item(sender_id)

            if row is None:
                send_text(sender_id, "Can't find that item! Try flipping again", main_menu_quick_reply())
                default_carousel(sender_id)
                return "OK", 200

            item_id = row['id']
            item_setup(sender_id, item_id, True)


    elif re.search('FLIP_COIN-(\d+)', payload) is not None:
        #send_tracker(fb_psid=sender_id, category="flip-coin", label=re.match(r'FLIP_COIN-(?P<item_id>\d+)', payload).group('item_id'))
        item_id = re.match(r'FLIP_COIN-(?P<item_id>\d+)', payload).group('item_id')
        if item_id is not None:
            item_setup(sender_id, item_id, False)

        else:
            send_text(sender_id, "Can't find that item! Try flipping again", main_menu_quick_reply())
            return "OK", 200


    elif re.search('POINTS-(\d+)', payload) is not None:
        price = int(re.match(r'POINTS-(?P<price>\d+)', payload).group('price'))
        send_text(sender_id, "Tap below to purchase the item in Lmon8 using Points.")

        image_url = ""
        if price == 1:
            image_url = "https://i.imgur.com/j3zxHam.png"

        elif price == 2:
            image_url = "https://i.imgur.com/jdqSWbe.png"

        elif price == 5:
            image_url = "https://i.imgur.com/KDngY5d.png"

        elif price == 10:
            image_url = "https://i.imgur.com/DAPjlMQ.png"

        send_card(
            recipient_id=sender_id,
            title="Share {bot_title}".format(bot_title=bot_title(bot_type)),
            image_url=image_url,
            card_url="http://m.me/lmon8?ref=GamebotsDeposit{price}".format(price=price),
            buttons=[{
                'type'  : "web_url",
                'url'   : "http://m.me/lmon8?ref=GamebotsDeposit{price}".format(price=price),  # if sender_id in Const.ADMIN_FB_PSID else "http://paypal.me/gamebotsc/{price}".format(price=price),
                'title' : "{points} Points".format(points=locale.format('%d', (price * 1250000), grouping=True))
            }, {
                'type' : "element_share"
            }],
            quick_replies=main_menu_quick_reply()
        )


    elif payload == "DISCORD":
        # send_tracker(fb_psid=sender_id, category="discord")

        send_discord_card(sender_id)
        send_text(sender_id, "Join {bot_title}'s Discord channel. Txt \"upload\" to transfer".format(bot_title=bot_title(get_session_bot_type(sender_id))), main_menu_quick_reply())


    elif payload == "INVITE":
        # send_tracker(fb_psid=sender_id, category="invite-friends")

        send_card(
            recipient_id =sender_id,
            title="Share {bot_title}".format(bot_title=bot_title(bot_type)),
            image_url=Const.SHARE_IMAGE_URL,
            # card_url="http://m.me/{bot_name}".format(bot_name=bot_name(bot_type)),
            card_url="http://m.me/{bot_name}".format(bot_name="gamebotsc"),
            buttons=[{ 'type' : "element_share" }],
            quick_replies=main_menu_quick_reply()
        )


    elif payload == "LMON8_REFERRAL":
        # send_tracker(fb_psid=sender_id, category="lmon8-referral")

        send_card(
            recipient_id=sender_id,
            title="Flip Shops for Points",
            subtitle="Get Lmon8 now on Messenger ",
            image_url="https://i.imgur.com/eOaYJ0G.png",
            buttons=[{
                'type'  : "web_url",
                'url'   : "https://m.me/lmon8",
                'title' : "Get Lmon8"
            }, {
                'type'  : "element_share"
            }],
            quick_replies=main_menu_quick_reply()
        )

    elif payload == "FAQ":
        # send_tracker(fb_psid=sender_id, category="faq")
        send_text(sender_id, "1. Wait up to 24 hours for each trade request.\n\n2. Accept trade request within one hour.\n\n3. You may purchase access to higher priced items.\n\n4. Each purchase gives you 2 more wins and 50 more chances.\n\n5. You may be banned for repeat abuse of our system, mods, support, and social staff.", main_menu_quick_reply())


    elif payload == "SUPPORT":
        send_tracker(fb_psid=sender_id, category="support")

        set_session_state(sender_id, Const.SESSION_STATE_SUPPORT)

        send_text(sender_id, "Welcome to {bot_title} Support. Your user id has been identified: {fb_psid}".format(bot_title=bot_title(bot_type), fb_psid=sender_id))
        send_text(
            recipient_id=sender_id,
            message_text="Please describe your support issue (500 character limit). Include purchase ID for faster look up.",
            quick_replies=[{
                'content_type': "text",
                'title'       : "Cancel",
                'payload'     : "NO_THANKS"
            }]
        )

        # conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
        # try:
        #     conn.row_factory = sqlite3.Row
        #     cur = conn.cursor()
        #     cur.execute('SELECT support FROM sessions WHERE fb_psid = ? ORDER BY added DESC LIMIT 1;', (sender_id,))
        #     row = cur.fetchone()
        #
        #     logger.info("::::::::::::::::::::: %s + 86400 = (%s) [%s]" % (row['support'], row['support'] + 864000, int(time.time())))
        #
        #     if row['support'] + 86400 <= int(time.time()):
        #         set_session_state(sender_id, Const.SESSION_STATE_SUPPORT)
        #
        #         send_text(sender_id, "Welcome to {bot_title} Support. Your user id has been identified: {fb_psid}".format(bot_title=bot_title(bot_type), fb_psid=sender_id))
        #         send_text(
        #             recipient_id=sender_id,
        #             message_text="Please describe your support issue (500 character limit). Include purchase ID for faster look up.",
        #             quick_replies=[{
        #                 'content_type': "text",
        #                 'title'       : "Cancel",
        #                 'payload'     : "NO_THANKS"
        #             }]
        #         )
        #
        #     else:
        #         send_text(sender_id, "You can only submit 1 support ticket per 24 hours")
        #
        # except sqlite3.Error as er:
        #     logger.info("::::::support[cur.execute] sqlite3.Error - %s" % (er.message,))
        #
        # finally:
        #     if conn:
        #         conn.close()

    elif payload == "NO_THANKS":
        # send_tracker(fb_psid=sender_id, category="no-thanks")
        default_carousel(sender_id)

    elif payload == "TRADE_URL_OK":
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('UPDATE `item_winners` SET `trade_url` = %s WHERE `fb_id` = %s ORDER BY `added` DESC LIMIT 1;', (get_session_trade_url(sender_id), sender_id))
                conn.commit()
        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
        finally:
            if conn:
                conn.close()

        trade_url = get_session_trade_url(sender_id)
        # send_tracker(fb_psid=sender_id, category="trade-url-set")

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('UPDATE `item_winners` SET `trade_url` = %s WHERE `fb_id` = %s ORDER BY `added` DESC LIMIT 1;', (trade_url, sender_id))
                conn.commit()
        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
        finally:
            if conn:
                conn.close()

        full_name, f_name, l_name = get_session_name(sender_id)
        payload = {
            'channel'  : "#bot-alerts",
            'username ': "gamebotsc",
            'icon_url' : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
            'text'     : "Trade URL set for *{user}*:\n{trade_url}".format(user=sender_id if full_name is None else full_name, trade_url=trade_url)
        }
        response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})
        send_text(sender_id, "Please wait up to 24 hours to transfer. Keep notifications on and accept trade within 1 hour.")

        set_session_state(sender_id)
        default_carousel(sender_id)


    elif payload == "TRADE_URL_CHANGE":
        set_session_trade_url(sender_id, "_{PENDING}_")
        set_session_state(sender_id, Const.SESSION_STATE_FLIP_TRADE_URL)
        send_text(sender_id, "Enter your Steam Trade URL now.")

    elif payload == "SUBMIT_YES":
        if get_session_state(sender_id) == Const.SESSION_STATE_FLIP_TRADE_URL:
            trade_url = get_session_trade_url(sender_id)
            # send_tracker(fb_psid=sender_id, category="trade-url-set")

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('UPDATE `item_winners` SET `trade_url` = %s WHERE `fb_id` = %s ORDER BY `added` DESC LIMIT 1;', (trade_url, sender_id))
                    conn.commit()
            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
            finally:
                if conn:
                    conn.close()

            full_name, f_name, l_name = get_session_name(sender_id)
            payload = {
                'channel'   : "#bot-alerts",
                'username ' : "gamebotsc",
                'icon_url'  : "https://cdn1.iconfinder.com/data/icons/logotypes/32/square-facebook-128.png",
                'text'      : "Trade URL set for *{user}*:\n{trade_url}".format(user=sender_id if full_name is None else full_name, trade_url=trade_url)
            }
            response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})
            send_text(sender_id, "Please wait up to 24 hours to transfer. Keep notifications on and accept trade within 1 hour.")

            set_session_state(sender_id)
            default_carousel(sender_id)

        elif get_session_state(sender_id) == Const.SESSION_STATE_GIVEAWAY_TRADE_URL:
            trade_url = get_session_trade_url(sender_id)
            # send_tracker(fb_psid=sender_id, category="trade-url-set")

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('UPDATE `giveaways` SET `trade_url` = %s WHERE `fb_psid` = %s ORDER BY `added` DESC LIMIT 1;', (trade_url, sender_id))
                    conn.commit()
            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
            finally:
                if conn:
                    conn.close()

            send_text(sender_id, "Giveaway results are determined once per day. Keep notifications on and accept trade within 1 hour.")
            set_session_state(sender_id)
            default_carousel(sender_id)



        elif get_session_state(sender_id) == Const.SESSION_STATE_FLIP_LMON8_URL:
            send_text(sender_id, "Please wait up to 24 hours to transfer. Keep notifications on and accept trade within 1 hour.")

            clear_session_dub(sender_id)
            default_carousel(sender_id)

        elif get_session_state(sender_id) == Const.SESSION_STATE_PURCHASED_TRADE_URL:
            purchase_id, item_id = get_session_purchase(sender_id)
            trade_url = get_session_trade_url(sender_id)
            send_text(sender_id, "Trade URL set to {trade_url}".format(trade_url=trade_url))

            conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            try:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('UPDATE payments SET `trade_url` = ? WHERE `id` = ? LIMIT 1;', (trade_url, purchase_id))
                conn.commit()

            except sqlite3.Error as er:
                logger.info("::::::payment[cur.execute] sqlite3.Error - %s" % (er.message,))

            finally:
                if conn:
                    conn.close()

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('UPDATE `fb_purchases` SET `trade_url` = %s WHERE `id` = %s LIMIT 1;', (trade_url, purchase_id))
                    conn.commit()

            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

            finally:
                if conn:
                    conn.close()

        else:
            clear_session_dub(sender_id)
            default_carousel(sender_id)

    elif payload == "SUBMIT_NO":
        if get_session_state(sender_id) == Const.SESSION_STATE_FLIP_TRADE_URL:
            send_text(sender_id, "Re-enter your steam trade url to claim {item_name}".format(item_name=get_item_details(get_session_item(sender_id))['asset_name']), main_menu_quick_reply())

        elif get_session_state(sender_id) == Const.SESSION_STATE_PURCHASED_TRADE_URL:
            send_text(sender_id, "Re-enter your steam trade url to recieve {item_name}".format(item_name=get_item_details(get_session_item(sender_id))['asset_name']), main_menu_quick_reply())

        elif get_session_state(sender_id) == Const.SESSION_STATE_FLIP_LMON8_URL:
            send_text(sender_id, "Re-enter your lmon8 shop url to recieve {item_name}".format(item_name=get_item_details(get_session_item(sender_id))['asset_name']), main_menu_quick_reply())

        elif get_session_state(sender_id) == Const.SESSION_STATE_GIVEAWAY_TRADE_URL:
            send_text(sender_id, "Re-enter your steam trade url", main_menu_quick_reply())

        else:
            clear_session_dub(sender_id)
            default_carousel(sender_id)

    elif payload == "SUBMIT_CANCEL":
        clear_session_dub(sender_id)
        default_carousel(sender_id)

    elif payload == "NO_THANKS":
        default_carousel(sender_id)


    elif payload == "CANCEL":
        return "OK", 200

    else:
        default_carousel(sender_id)
    return "OK", 200


def recieved_text_reply(sender_id, message_text):
    logger.info("recieved_text_reply(sender_id=%s, message_text=%s)" % (sender_id, message_text))

    if message_text.lower() in Const.OPT_OUT_REPLIES.split("|"):
        logger.info("-=- ENDING HELP -=- (%s)" % (time.strftime('%Y-%m-%d %H:%M:%S')))
        toggle_opt_out(sender_id, True)

    elif message_text.lower() in Const.MAIN_MENU_REPLIES.split("|"):
        clear_session_dub(sender_id)
        default_carousel(sender_id)

    elif message_text.lower() in Const.FAQ_REPLIES.split("|"):
        send_text(sender_id, "1. Wait up to 24 hours for each trade request.\n\n2. Accept trade request within one hour.\n\n3. You may purchase access to higher priced items.\n\n4. Each purchase gives you 2 more wins and 50 more chances.\n\n5. You may be banned for repeat abuse of our system, mods, support, and social staff.", main_menu_quick_reply())

    elif message_text.lower() in Const.SUPPORT_REPLIES.split("|"):
        enter_support(sender_id)

    elif message_text.lower() in Const.GIVEAWAY_REPLIES.split("|"):
        enter_giveaway(sender_id)

    elif message_text.lower() in Const.TRADE_STATUS_REPLIES.split("|"):
        trades = {
            'open'  : 0,
            'traded': 0
        }
        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('SELECT `claimed` FROM `item_winners` WHERE `fb_id` = %s AND `added` >= DATE_SUB(NOW(), INTERVAL 24 HOUR);', (sender_id,))
                for row in cur.fetchall():
                    if row['claimed'] == 0:
                        trades['open'] += 1

                    else:
                        trades['traded'] += 1


        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(sender_id, "You have {open_total} trade{p1} outstanding and {traded_total} trade{p2} completed.".format(open_total=trades['open'], p1="" if trades['open'] == 1 else "s", traded_total=trades['traded'], p2="" if trades['traded'] == 1 else "s"))
        send_text(sender_id, "Trades may be rejected from abuse, spamming the system, or a dramatic change in market place prices.", main_menu_quick_reply())


    elif message_text.lower() in Const.UPLOAD_REPLIES.split("|"):
        send_text(sender_id, "Upload screenshots now.")

    elif message_text.lower() in Const.APPNEXT_REPLIES.split("|"):
        send_text(sender_id, "Instructions…\n\n1. GO: taps.io/skins\n\n2. OPEN & Screenshot each free game or app you install.\n\n3. SEND screenshots for proof on Twitter.com/gamebotsc\n\nEvery free game or app you install increases your chances of winning.", main_menu_quick_reply())

    elif message_text.lower() in Const.MODERATOR_REPLIES.split("|"):
        send_text(sender_id, "You have signed up to be a mod. We will send you details shortly.", main_menu_quick_reply())

    elif message_text.lower() in Const.FBPSID_REPLIES.split("|"):
        send_text(sender_id, "Your ID is:")
        send_text(sender_id, sender_id, main_menu_quick_reply())



    # elif message_text.lower() in Const.TASK_REPLIES.split("|"):
    #     send_text(sender_id, "Mod tasks:\n\n1. 100 PTS: Invite a friend to join & txt Lmon8 your referral ID.\n2. 50 PTS: Add \"mod for @gamebotsc\" to your Twitter & Steam Profile. \n3. 1000 PTS: Become a reseller and sell an item on Lmon8. Sale has to complete. \n4. 100 PTS: Like & 5 star review Lmon8 on Facebook. fb.com/lmon8\n5. 100 PTS: Like & 5 star review {bot_title} on Facebook. fb.com/gamebotsc \n6. 25 PTS: Invite friends to @lmon8 and @gamebotsc in Twitter. Have each invite @reply us your Lmon8 referral id.\n7. 500 PTS: Install 10 free games taps.io/skins\n8: 50 PTS: add your referral id to your Twitter and Steam Profile.".format(bot_name=bot_title(get_session_bot_type(sender_id))))

    elif message_text.lower() == ":payment":
        amount = get_session_deposit(sender_id)
        set_session_deposit(sender_id, -amount)

        conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
        try:
            with conn:
                cur = conn.cursor(mdb.cursors.DictCursor)
                cur.execute('UPDATE `fb_purchases` SET `amount` = 0 WHERE `fb_psid` = %s;', (sender_id,))
                conn.commit()

        except mdb.Error, e:
            logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))

        finally:
            if conn:
                conn.close()

        send_text(sender_id, "Cleared payments!")


    else:
        if get_session_state(sender_id) == Const.SESSION_STATE_SUPPORT:
            conn = sqlite3.connect("{script_path}/data/sqlite3/fb_bot.db".format(script_path=os.path.dirname(os.path.abspath(__file__))))
            try:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute('UPDATE `sessions` SET `support` = ? WHERE `fb_psid` = ?;', (int(time.time()), sender_id))
                conn.commit()

            except sqlite3.Error as er:
                logger.info("::::::set_session_state[cur.execute] sqlite3.Error - %s" % (er.message,))

            finally:
                if conn:
                    conn.close()

            send_text(sender_id, "Your message has been sent to support. You can upload screenshots by txting \"upload\" now.", main_menu_quick_reply())

            full_name, f_name, l_name = get_session_name(sender_id)
            payload = {
                'channel'    : "#support-001",
                'username '  : bot_title(get_session_bot_type(sender_id)),
                'icon_url'   : "https://i.imgur.com/bhSzZiO.png",
                'text'       : "*Support Request*\n_{full_name} ({fb_psid}) says:_\n{message_text}".format(full_name=sender_id if full_name is None else full_name, fb_psid=sender_id, message_text=message_text)
            }
            response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})
            clear_session_dub(sender_id)

        elif get_session_state(sender_id) == Const.SESSION_STATE_FLIP_TRADE_URL or get_session_state(sender_id) == Const.SESSION_STATE_PURCHASED_TRADE_URL or get_session_state(sender_id) == Const.SESSION_STATE_GIVEAWAY_TRADE_URL:
            if re.search(r'.*steamcommunity\.com\/tradeoffer\/.*$', message_text) is not None:
                set_session_trade_url(sender_id, message_text)
                recieved_trade_url(sender_id, message_text)

            else:
                send_text(
                    recipient_id=sender_id,
                    message_text="Invalid URL, try again...",
                    quick_replies=main_menu_quick_reply()
                )

        elif get_session_state(sender_id) == Const.SESSION_STATE_FLIP_LMON8_URL:
            url = "http://m.me/lmon8?ref={deeplink}".format(deeplink=re.sub(r'[\,\'\"\`\~\ \:\;\^\%\#\&\*\$\@\!\/\?\=\+\-\|\(\)\[\]\{\}\\\<\>]', "", message_text.encode('ascii', 'ignore')))
            send_text(sender_id, "Set your lmon8 shop link to {url}?".format(url=url), quick_replies=submit_quick_replies())

            conn = mdb.connect(host=Const.DB_HOST, user=Const.DB_USER, passwd=Const.DB_PASS, db=Const.DB_NAME, use_unicode=True, charset='utf8')
            try:
                with conn:
                    cur = conn.cursor(mdb.cursors.DictCursor)
                    cur.execute('UPDATE `item_winners` SET `prebot_url` = %s WHERE `fb_id` = %s ORDER BY `added` DESC LIMIT 1;', (url, sender_id))
                    conn.commit()
            except mdb.Error, e:
                logger.info("MySqlError (%s): %s" % (e.args[0], e.args[1]))
            finally:
                if conn:
                    conn.close()

        else:
            default_carousel(sender_id)


def recieved_attachment(sender_id, attachment_type, attachment):
    logger.info("recieved_attachment(sender_id=%s, attachment_type=%s, attachment=%s)" % (sender_id, attachment_type, attachment))

    if attachment_type == Const.PAYLOAD_ATTACHMENT_IMAGE.split("-")[-1] and re.search('^.*t39\.1997\-6.*$', attachment['url']) is None:
        full_name, f_name, l_name = get_session_name(sender_id)
        payload = {
            'channel'     : "#uploads-001",
            'username '   : bot_title(get_session_bot_type(sender_id)),
            'icon_url'    : "https://i.imgur.com/bhSzZiO.png",
            'text'        : "Image upload from *{user}* _{fb_psid}_\n{trade_url}".format(user=sender_id if full_name is None else full_name, fb_psid=sender_id, trade_url=get_session_trade_url(sender_id)),
            'attachments' : [{
                'image_url' : attachment['url']
            }]
        }
        response = requests.post("https://hooks.slack.com/services/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", data={'payload': json.dumps(payload)})

        #send_text(sender_id, "You have won 100 skin pts! Every 1000 skin pts you get a MAC 10 Neon Rider!\n\nTerms: your pts will be rewarded once the screenshot you upload is verified.", main_menu_quick_reply())
        send_text(sender_id, "Please wait up to 12 hours for approval.", main_menu_quick_reply())

    elif attachment_type != Const.PAYLOAD_ATTACHMENT_URL.split("-")[-1] or attachment_type != Const.PAYLOAD_ATTACHMENT_FALLBACK.split("-")[-1]:
        send_text(sender_id, "I'm sorry, I cannot understand that type of message.", home_quick_replies())


def send_typing_indicator(recipient_id, is_typing):
    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'sender_action' : "typing_on" if is_typing else "typing_off"
    }

    send_message(get_session_bot_type(recipient_id), json.dumps(data))


def send_text(recipient_id, message_text, quick_replies=None):
    logger.info("send_text(recipient_id=%s, message_text=%s, quick_replies=%s)" % (recipient_id, message_text, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message'   : {
            'text' : message_text
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(get_session_bot_type(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_card(recipient_id, title, image_url, card_url=None, subtitle=None, buttons=None, quick_replies=None):
    logger.info("send_card(recipient_id=%s, title=%s, image_url=%s, card_url=%s, subtitle=%s, buttons=%s, quick_replies=%s)" % (recipient_id, title, image_url, card_url, subtitle, buttons, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message'   : {
            'attachment' : {
                'type'    : "template",
                'payload' : {
                    'template_type' : "generic",
                    'elements'      : [{
                        'title'     : title,
                        'item_url'  : card_url,
                        'image_url' : image_url,
                        'subtitle'  : subtitle or "",
                        'buttons'   : buttons
                    }]
                }
            }
        }
    }

    if buttons is not None:
        data['message']['attachment']['payload']['elements'][0]['buttons'] = buttons

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(get_session_bot_type(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_carousel(recipient_id, elements, quick_replies=None):
    logger.info("send_carousel(recipient_id=%s, elements=%s, quick_replies=%s)" % (recipient_id, elements, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message'   : {
            'attachment'  : {
                'type'    : "template",
                'payload' : {
                    'template_type' : "generic",
                    'elements'      : elements
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(get_session_bot_type(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_image(recipient_id, url, quick_replies=None):
    logger.info("send_image(recipient_id=%s, url=%s, quick_replies=%s)" % (recipient_id, url, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id'          : recipient_id
        },
        'message'   : {
            'attachment'  : {
                'type'    : "image",
                'payload' : {
                    'url' : url
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(get_session_bot_type(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_video(recipient_id, url, quick_replies=None):
    logger.info("send_image(recipient_id=%s, url=%s, quick_replies=%s)" % (recipient_id, url, quick_replies))
    send_typing_indicator(recipient_id, True)

    data = {
        'recipient' : {
            'id' : recipient_id
        },
        'message'   : {
            'attachment' : {
                'type'    : "video",
                'payload' : {
                    'url' : url
                }
            }
        }
    }

    if quick_replies is not None:
        data['message']['quick_replies'] = quick_replies

    send_message(get_session_bot_type(recipient_id), json.dumps(data))
    send_typing_indicator(recipient_id, False)


def send_message(bot_type, payload):
    logger.info("send_message(bot_type=%s, payload=%s)" % (bot_type, payload))

    response = requests.post(
        url="https://graph.facebook.com/v2.6/me/messages?access_token={token}".format(token=bot_type_token(bot_type)),
        params={ 'access_token' : bot_type_token(bot_type) },
        json=json.loads(payload)
    )

    logger.info("GRAPH RESPONSE (%s): %s" % (response.status_code, response.text))
    return True


def fb_graph_user(recipient_id):
    logger.info("fb_graph_user(recipient_id=%s)" % (recipient_id))
    params = {
        'fields'      : "first_name,last_name,profile_pic,locale,timezone,gender,is_payment_enabled",
        'access_token': bot_type_token(get_session_bot_type(recipient_id))
    }
    response = requests.get("https://graph.facebook.com/v2.6/{recipient_id}".format(recipient_id=recipient_id), params=params)
    return None if 'error' in response.json() else response.json()

if __name__ == '__main__':
    app.run(debug=True)


# =- -=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=-=#=- -=#
