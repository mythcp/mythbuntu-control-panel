#!/bin/sh

LOG="/tmp/hdhomerun_config.out"

for i in $(seq 30); do
    hdhomerun_config discover 2>&1 >> $LOG
    if [ $? -eq 0 ]; then
        echo "HD Homerun is up ($(date))." >> $LOG
        exit 0
    fi
    sleep 2
done

echo "Couldn't see the HDHomerun in 30 seconds!" >> $LOG
exit 1
