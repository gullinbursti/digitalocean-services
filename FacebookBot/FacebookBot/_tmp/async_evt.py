


import grequests

urls = [
  'http://www.heroku.com',
  'http://tablib.org',
  'http://httpbin.org',
  'http://python-requests.org',
  'http://kennethreitz.com']
   
rs = (grequests.get(u) for u in urls)
print "rs={req}".format(req=rs)







# import gevent
# from gevent.queue import *
# 
# import time
# import random
# 
# q = JoinableQueue()
# workers = []
# 
# def do_work(wid, value):
#   gevent.sleep(random.randint(0, 2))
#   print 'Task: #{wid} / val:({val})'.format(wid=wid, val=value)
# 
# def worker(wid):
#   print 'Doing task: #{wid}'.format(wid=wid)
#   while True:
#     item = q.get()
#     print 'ATTEMPTING ITEM -->({itm})'.format(itm=item)
#     
#     try:
#       do_work(wid, item)
#     
#     finally:
#       print 'Completed task --> {wid} // {itm}'.format(wid=wid, itm=item)
#       q.task_done()
# 
# 
# def producer():
#   for i in range(4):
#     print 'Generating worker {cnt}/{tot}'.format(cnt=i, tot=4)
#     workers.append(gevent.spawn(worker, random.randint(1, 100000)))
#     
#     for item in range(1, 9):
#       print 'Pushing VAL:{itm} into queue #{queue}...'.format(itm=item, queue=i)
#       q.put(item)
#       
#     gevent.sleep(3)
# 
# producer()
# q.join()
