<<<<<<< HEAD

#!/bin/bash - 
=======
#!/bin/bash
>>>>>>> v1.0.1-resubmit



#-- project path
app_path=/opt/kik_bot


#-- start
clear
printf "Listening in on %s/* for changes...\n" "${app_path}"
last_event=$(date +%s)


#-- begin monitoring
inotifywait --monitor --recursive --quiet --event create --event modify --event delete --exclude '.*(\.pyc|\.db)' --timefmt '%Y-%m-%d %H:%M:%S' --format '%w\t%f\t%e\t%T' ${app_path} | while read l; do

   #-- somethin happened!
   if [ "$last_event" -ne "$(date +%s)" ]; then
      printf "%s\n" "${l}"

      #-- kill bot
      pid=$(ps ax | grep kik_bot| grep -v grep | cut -d\  -f1)
      kill -9 $pid

      #-- redo bot
      /usr/local/bin/kik_bot
      #--systemctl restart kik_bot.service
   fi

   #-- update event timestamp
   last_event=$(date +%s)
done


#-- terminate w/o error
exit 0;



# -[=-=-=--=-=-=--=-=-=--=-=-=--=-=-=--=-=-=--=-=-=--=-=-=--=-=-=]- #




#--# OLD STUFF #--#

#//while true; do
#//  filename=$(inotifywait --quiet --recursive --event create --event modify --event delete --exclude '.*(\.pyc|\.db)' --format 

#//while inotifywait --quiet --recursive --event create --event modify --event delete --exclude '.*(\.pyc|\.db)' ${app_path}; do
#//  printf "FILE CHANGE! @ [%s]\n", $(date +%Y-%m-%d\ %H:%M:%S)
#//  systemctl restart kik_bot.service
#//done
