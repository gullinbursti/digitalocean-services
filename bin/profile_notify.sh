#!/bin/bash

token="1b9700e13ea17deb5a487adac8930ad2"
url="http://159.203.250.4:8080/profile-notify"
#url="http://98.248.37.68:8080/profile-notify"

for f in `ls /opt/kik_bot/queue | grep -v sent`
do
  while read line ; do
    from_user=$(echo "${line}" | cut -d, -f1)
    chat_id=$(echo "${line}" | cut -d, -f2)
    to_user=$(echo "${line}" | cut -d, -f3)
    game_name=$(echo "${line}" | cut -d, -f4)
    img_url=$(echo "${line}" | cut -d, -f5)
    body=$(echo "${line}" | cut -d, -f6-)

    curl --request POST "${url}" --silent --data "token=${token}" --data "from_user=${from_user}" --data "chat_id=${chat_id}" --data "to_user=${to_user}" --data "game_name=${game_name}" --data "img_url=${img_url}" --data "body=${body}"
  done < /opt/kik_bot/queue/$f
  mv /opt/kik_bot/queue/$f /opt/kik_bot/queue/sent
done
