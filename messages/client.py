#!/usr/bin/env python
# -*- coding: utf-8 -*-


from celery import Celery
from tasks import update_streams, fetch_streams

#-- init celery
celery = Celery()
celery.config_from_object('celeryconfig')


#-- start update_streams
#update_streams()
celery.send_task("tasks.update_streams", [30000])


#-- multiply 5x
#results = []
#for x in range(1,5):
#	results.append(celery.send_task("tasks.multiply", [2, 2]))
