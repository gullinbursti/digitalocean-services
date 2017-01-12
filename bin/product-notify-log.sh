#!/bin/bash - 

timestamp=$(ls /opt/kik_bot/var/log | tail -1 | cut -d. -f3)

#-- tail in realtime send+error logs
while true ; do
  clear
  ( wc -l /opt/kik_bot/var/log/product-notify.sent.${timestamp}.csv ; wc -l /opt/kik_bot/var/log/product-notify.error.${timestamp}.csv ) | cat
  sleep 1
done


exit 0;