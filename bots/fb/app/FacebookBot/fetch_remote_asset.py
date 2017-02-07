
import os
import urllib, urllib2
import shutil
import subprocess
import threading
import time
import requests

from subprocess import check_output
out = check_output(["ntpq", "-p"])





timestamp = int(time.time())
url = "https://video.xx.fbcdn.net/v/t42.3356-2/15930703_10154939964852244_8434126089172811776_n.mp4/video-1484337103.mp4?vabr=307778&oh=dda6112f39cadc97fbb9d5719ed8f770&oe=587A7679"
local_file = "{file_path}/videos/{timestamp}.mp4".format(file_path=os.path.dirname(os.path.realpath(__file__)), timestamp=timestamp)

subprocess.call("/usr/bin/ffprobe {url}".format(url=url), shell=True)

#std_out=
self.stdout, self.stderr = p.communicate()

response = requests.get(url, stream=True)
if response.status_code == 200:
  with open("{local_file}".format(local_file=local_file), 'wb') as f:
    shutil.copyfileobj(response.raw, f)
  del response
        

quit()

'''
Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'https://video.xx.fbcdn.net/v/t42.3356-2/15930703_10154939964852244_8434126089172811776_n.mp4/video-1484337103.mp4?vabr=307778&oh=dda6112f39cadc97fbb9d5719ed8f770&oe=587A7679':
  Metadata:
    major_brand     : isom
    minor_version   : 512
    compatible_brands: isomiso2avc1mp41
    encoder         : Lavf56.40.101
  Duration: 00:01:44.33, start: 0.023220, bitrate: 306 kb/s
    Stream #0:0(und): Video: h264 (Main) (avc1 / 0x31637661), yuv420p, 320x240 [SAR 1:1 DAR 4:3], 256 kb/s, 15 fps, 15 tbr, 15360 tbn, 30 tbc (default)
    Metadata:
      handler_name    : VideoHandler
    Stream #0:1(und): Audio: aac (LC) (mp4a / 0x6134706D), 44100 Hz, stereo, fltp, 47 kb/s (default)
    Metadata:
      handler_name    : SoundHandler

'''