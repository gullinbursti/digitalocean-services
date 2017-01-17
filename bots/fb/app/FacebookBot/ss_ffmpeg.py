import os
import time
import subprocess


url = "https://video.xx.fbcdn.net/v/t42.3356-2/15951681_10154942576307244_6623908278554329088_n.mp4/video-1483829972.mp4?vabr=256804&oh=706e26022e6e28856566d750265ceb7b&oe=58730CC0"
image_file = "/var/www/html/thumbs/{timestamp}.jpg".format(file_path=os.path.dirname(os.path.realpath(__file__)), timestamp=int(time.time()))


print("OPENING %s" % (url))
#p = subprocess.Popen("/usr/bin/ffmpeg -ss 00:00:03 -i %s -frames:v 1 %s" % (url, image_file), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
#output = p.communicate()[0]
#print("::::: subprocess.Popen --> %s" % (output))

subprocess.call(['/usr/bin/ffmpeg', '-ss', '00:00:03', '-i', '{url}'.format(url=url), '-frames:v', '1', '{image_file}'.format(image_file=image_file)])
