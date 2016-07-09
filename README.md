# digitalocean-services[TashaYar]
Services running on DigitalOcean - TashaYar (104.131.141.147)

## Enabled cronjobs:
    */2	*	*	*	*	/var/modd/prod/trailer_maker
    */5	*	*	*	*	/opt/modd/prod/streamer_check >> /home/moddadmin/streamer_check.log 2>&1
    0	0	*	*	*	curl http://beta.modd.live/api/convert_beta.php

## Disabled cronjobs:
    0	*	*	*	*	ruby /opt/modd/prod/rehostbot.rb
    */10	*	*	*	*	/opt/modd/logChatters2.sh
    */10	*	*	*	*	/opt/modd/logPopularChatters.sh
    */30	1	*	*	*	python /opt/modd/cohort.py
