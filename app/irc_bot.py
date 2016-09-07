
import os, sys
import socket, requests
import time, string, json


IRC_SERVER = "irc.chat.twitch.tv"
IRC_PORT = 6667
BUFFER_SIZE = 4096

MESSAGE_POST = u"I recommend you to help me with {game_name}! For details please visit hearthstonehelp\xb7com"


def connect_server():
  try:
    irc_socket.connect((IRC_SERVER, IRC_PORT))
    
  except socket.error:
    print "socket.error!"
    
  
def disconnect_server():
  send_command("QUIT :Bye!")
  

def login(nickname='nickname', password='oauth:'):
  send_command("PASS {pwrd}".format(pwrd=password))
  send_command("NICK {nick}".format(nick=nickname))
  

def join_channel(channel):
  send_command("JOIN #{chan}".format(chan=channel.lower()))
  
  
def leave_channel(channel):
  send_command("PART #{chan}".format(chan=channel.lower()))
  

def send_message(channel, message):
  send_command("PRIVMSG #{chan} :{msg}".format(chan=channel.lower(), msg=message))
  

def send_command(command):
  print "[::] sending command - {cmd}".format(cmd=command)
  
  try:
    irc_socket.send("{cmd}\r\n".format(cmd=command))
    
  except socket.error:
    print "socket.error!"


messages = []
timestamp = 0

#-- define socket
irc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connect_server()
login(sys.argv[1], "oauth:{token}".format(token=sys.argv[2]))


#-- hasn't left
while "PART" not in messages:
  messages = string.split(irc_socket.recv(BUFFER_SIZE))
  
  #-- leave after PONG
  if "PONG" in messages and messages[-1][1:] == str(timestamp):
    timestamp = 0
    leave_channel(sys.argv[3])
   
  #-- received something
  if len(messages) > 0:
    print messages
 
  #-- welcome message, join channel
  if messages[0][1:] == "tmi.twitch.tv" and messages[1] == "001":
    join_channel(sys.argv[3])

  #-- pong back
  if messages[0] == "PING":
    send_command("PONG {msg}".format(msg=messages[1]))

  #-- join flag
  if messages[1] == "JOIN":
    pass

  #-- deliver message after getting names list
  if len(messages) >= 2 and messages[-2] == "/NAMES":
    send_message(sys.argv[3], MESSAGE_POST.encode('utf-8').format(game_name=sys.argv[4]))
    time.sleep(1)
    timestamp = int(time.time())
    send_command("PING %d" % (timestamp))
    
    
#-- drop connection
disconnect_server()
