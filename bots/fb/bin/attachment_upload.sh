#!/bin/bash

#-- fb graph
fb_access_token="EAADzAMIzYPEBAJGk5P18ibMeEBhhdvUzZBsMoItnuB19PEzUGnNZALX5MN1rK0HKEfSG4YsmyVM2NmeK3m9wcmDvmwoB97aqfn1U0KOdvNtv6ZCgPLvqPFr2YbnlinuUUSrPtnphqafj6ad73wIPVBCOhCaiLGfvEZCUr7CxcAZDZD"


media_type="video"
if [ ! -z "$1" ]; then
  media_type="${1}" ; fi


if [ ! -z "$2" ]; then
  media_url="${2}"
else
  printf "No URL specified\n" ; exit 0;
fi


json_data='{
  "recipient":{
    "id":"1117769054987142"
  },
  "message":{
    "attachment":{
      "type":"${media_type}",
      "payload":{
        "url":"${media_url}",
        "is_reusable":true
      }
    }
  }
}'

#-- perform
curl --request POST --header "Content-Type: application/json" --data ${json_data} "https://graph.facebook.com/me/messages?access_token=${fb_access_token}"



exit 0;
