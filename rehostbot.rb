require 'eat'

require 'cinch'

require 'json'



####################
_offset = 300

  _maxViewersOffsetStart = 0

  _maxViewers = Random.rand(100..200)
  _minViewers = 10


  _viewers = 9999999 #set to ridiculously high number
  _displayName = ""
  #page through json until we find the correct offset
 puts "paging..."
  while _viewers > _maxViewers
    
     _jsonString = eat("https://api.twitch.tv/kraken/streams?limit=100&offset=#{_offset}")

     _json = JSON.parse(_jsonString)

     _viewers = _json["streams"][0]["viewers"].to_i
     _displayName = _json["streams"][0]["channel"]["display_name"]
     _offset = _offset + 100
     
     
     puts "offset = #{_offset} viewers = #{_viewers}"
     
     sleep(10) # do this every day
     
  end

  #we've gone too far... roll back the offset and start recording users under the max number of viewers, stop writing to file and end when viewers are below minViewers
 
   puts _viewers
   puts _displayName
  

#################

class MonitorBot 
  include Cinch::Plugin

  listen_to :monitor_msg, :method => :send_msg

  def send_msg(m, msg, channel) 
	  Channel(channel).send "#{msg}"
  end
end


def server(bot, channel, name)
  sleep(5)
  msg =  ("/host " + name)
  bot.handlers.dispatch(:monitor_msg, nil, msg, channel)
  sleep(10)
  bot.handlers.dispatch(:monitor_msg, nil, "julieeetv has added you to her rehost playlsit from modd.live", "#" + name)
  sleep(600)
  bot.quit()
end


#-- convert to array of channels


reHoster = _displayName
channel_names = ["#julieeetv", "#" + reHoster]



#-- config bot
bot = Cinch::Bot.new do
  configure do |c|
    c.server          = "irc.chat.twitch.tv"
    c.port            = 6667
    c.nick            = "julieeetv"
    c.realname        = "julieeetv"
    c.user            = "julieeetv"
    # c.password        = "oauth:zfcxrlmcbtok82iismmtpplevxkxx9" #-- moddboto
    # c.password        = "oauth:d0aggkc01sl4y10h8kytcaktqq1x3o" #-- TeamMODD
    c.password        = "oauth:51l8o72ogtw7nvzxjc8b6qk7pja7i9" #-- julieeetv
    c.channels        = channel_names
    c.verbose         = false
    c.plugins.plugins = [MonitorBot]
  end
  
end


Thread.new { server(bot, "#TeamMODD", reHoster) }

bot.start



