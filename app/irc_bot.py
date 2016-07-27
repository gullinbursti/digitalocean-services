import socket, string
import time, requests

import MySQLdb as mysql


DB_HOST = 'external-db.s4086.gridserver.com'
DB_NAME = 'db4086_modd'
DB_USER = 'db4086_modd_usr'
DB_PASS = 'f4zeHUga.age'


SERVER = 'irc.chat.twitch.tv'
PORT = 6667
POST_MESSAGE = 'I recommend you to help me with gamename inside of GameBots! For details please Kik: GameBots.Player'
LEAVE_INTERVAL = 3

def next_request():
  _obj = {}
  
  try:
    conn = mysql.connect(DB_HOST, DB_USER, DB_PASS, DB_NAME);
    with conn:
      cur = conn.cursor(mysql.cursors.DictCursor)
      cur.execute("SELECT `id`, `channel`, `username`, `oauth_token` FROM `help_requests` WHERE `enabled` = 1 ORDER BY `added` LIMIT 1;")
      
      if cur.rowcount == 1:
        row = cur.fetchone()
        _obj = {
          'id': row['id'],
          'username': row['username'],
          'password': "oauth:{token}".format(token=row['oauth_token']),
          'channel': "#{channel}".format(channel=row['channel'])
        }
        print "HELP REQUESTED: ({username})-> ({channel_name})".format(username=_obj['username'], channel_name=_obj['channel'])
        
        cur.execute("UPDATE `help_requests` SET `enabled` = 0 WHERE `id` = %d LIMIT 1;" % (_obj['id']))

  except mdb.Error, e:
    print "MySQL Error #{errno}: {errinfo}".format(errno=e.args[0], errinfo=e.args[1])

  finally:
    if conn:
      conn.close()
      
    return _obj
  

def irc_connect():
  irc_socket.connect((SERVER, PORT))

def login(nickname='nickname', password='oauth:'):
  send_command("PASS %s" % (password))
  send_command("NICK %s" % (nickname))

def join_channel(channel):
  send_command("JOIN %s" % (channel))
  
def leave_channel(channel):
  send_command("PART %s" % (channel))

def send_message(channel, message):
  send_command("PRIVMSG %s :%s" % (channel, message))

def send_command(command):
  # print "[::] sending command - %s" % (command)
  irc_socket.send("%s\n" % (command))



# request_obj = {
#   'username': "streamcard_tv",
#   'password': "oauth:hexvgjgs5jsz99lfwddin2ij3a4f1m",
#   'channel': "#matty_devdev"
# }


request_obj = next_request()
if request_obj:
  irc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  irc_connect()
  login(request_obj['username'], request_obj['password'])
  join_channel(request_obj['channel'])


  messages = []
  while not "PART" in messages:
    buff = irc_socket.recv(1024)
    messages = string.split(buff)
    
    if len(messages) > 0:
      if messages[0] == "PING":
        send_command("PONG %s" % (messages[1]))
      
      if messages[1] == "JOIN":
        send_message(request_obj['channel'], POST_MESSAGE)
        time.sleep(LEAVE_INTERVAL)
        leave_channel("%s" % (request_obj['channel']))
      