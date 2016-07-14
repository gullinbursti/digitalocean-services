import urllib2

def sendTracker(category, action, label):
  try:
    _response = urllib2.urlopen("http://beta.modd.live/api/bot_tracker.php?category=%s&action=%s&label=%s" % (str(category), str(action), str(label)))
  
  except:
    print "GA ERROR!"
        
  return

