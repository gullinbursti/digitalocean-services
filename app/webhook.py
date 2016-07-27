import subprocess

import tornado.escape
import tornado.ioloop
import tornado.web

import json


HTTP_PORT = 8080
VERIFY_TOKEN = 'e967b132621cc66da735eeaa6b34bddf'




class HelpRequest(tornado.web.RequestHandler):
  
  #-- cors
  def set_default_headers(self):
    self.set_header('Access-Control-Allow-Origin', "*")
    self.set_header('Access-Control-Allow-Headers', "x-requested-with")
    self.set_header('Access-Control-Allow-Methods', "POST, GET, OPTIONS")
  
  #-- get request
  def get(self):
    self.set_status(404)
    return
  
  #-- post request  
  def post(self):
    print "X-MODD-Signature: ({sig})\n{body}".format(sig=self.request.headers.get('X-MODD-Signature'), body=self.request.body)
    
    #-- make sure header has right token from api
    if self.request.headers.get('X-MODD-Signature') == VERIFY_TOKEN:
      
      #-- parse as json
      json_data = tornado.escape.json_decode(self.request.body)
      if json_data:
        
        #-- call bot script
        subprocess.call("python irc_bot.py \"{username}\" \"{password}\" \"{channel}\" \"{game_name}\"".format(username=json_data['username'], password=json_data['password'], channel=json_data['channel'], game_name=json_data['game_name']), shell=True)
        
        #-- echo json
        self.write(json.dumps({
          'result': True,
          'channel': json_data['channel'],
          'username': json_data['username']
        }))
        self.set_status(200)
        return
            
            
    #-- error
    self.set_status(403)
    return



#-- endpoints
application = tornado.web.Application([
  (r"/help-request", HelpRequest)
])


#-- start www server
if __name__ == "__main__":
  application.listen(HTTP_PORT)
  tornado.ioloop.IOLoop.instance().start()
