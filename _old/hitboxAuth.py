from datetime import date
import tornado.escape
import tornado.ioloop
import tornado.web
import pymysql
import pycurl
import sys
import cStringIO
import json
import time
import httplib, urllib
import requests

class Auth(tornado.web.RequestHandler):

        def get(self):
                print("get")
		#print(self.get_argument("request_token"))
		request_token = self.get_argument("request_token")
		app_token = "p4K3N2xQWkJniI5ZRvoYmMf7j98OlbXTGCEVLHza"
		hash = "cDRLM04yeFFXa0puaUk1WlJ2b1ltTWY3ajk4T2xiWFRHQ0VWTEh6YWk0bEFWSThKZm91TFJEN1hZemE1Y3czRkJ5R1B2UXBIazlTRVoxTlU="

		#print(request_token, app_token, hash)


		r = requests.post("https://api.hitbox.tv/oauth/exchange", data = {'request_token':request_token, 'app_token':app_token, 'hash':hash})
		print(r.status_code, r.reason, r.text)

		data_json = tornado.escape.json_decode(r.text)
		access_token = data_json["access_token"]

		print(access_token)
		r2 = requests.post("https://api.hitbox.tv/auth/login", data = {'app':"moddtest", "authToken":access_token})
		#r2 = requests.post("https://api.hitbox.tv/auth/login", data = {'login':"faroutrob", 'pass':'moddpass', 'rememberme':''})
		print(r2.status_code, r2.reason, r2.text)


	def post(self):
		print("post")
#data_json = tornado.escape.json_decode(self.request.bo
		#response = { 'cohort': "yo" }
		self.write("OK 200")


application = tornado.web.Application([(r"/hitbox/auth", Auth)])
if __name__ == "__main__":
    application.listen(8890)
    tornado.ioloop.IOLoop.instance().start()

