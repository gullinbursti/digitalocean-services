#!/bin/bash

token="1b9700e13ea17deb5a487adac8930ad2"
#url="http://159.203.250.4:8080/profile-notify"
url="http://98.248.37.68:8080/profile-notify"

for f in `ls /opt/kik_bot/queue | grep -v sent`
do
  while read line ; do
    from_user=$(echo "${line}" | awk '{print $1}')
    chat_id=$(echo "${line}" | awk '{print $2}')
    to_user=$(echo "${line}" | awk '{print $3}')
    img_url=$(echo "${line}" | awk '{print $4}')
    body=$(echo "${line}" | awk '{print $NF}')

    curl --request POST "${url}" --silent --data "token=${token}" --data "from_user=${from_user}" --data "chat_id=${chat_id}" --data "to_user=${to_user}" --data "img_url=${img_url}" --data "body=${body}"
  done < /opt/kik_bot/queue/$f
  mv /opt/kik_bot/queue/$f /opt/kik_bot/queue/sent
done