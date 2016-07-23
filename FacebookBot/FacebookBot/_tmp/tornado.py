import grequests

urls = [
  'http://www.heroku.com',
  'http://tablib.org',
  'http://httpbin.org',
  'http://python-requests.org',
  'http://kennethreitz.com']
   
  rs = (grequests.get(u) for u in urls)
  print "rs={req}".format(queue=rs)



req = (grequests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data for url in urls))






grequests.map(rs)