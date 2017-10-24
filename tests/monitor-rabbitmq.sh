#!/bin/bash

KEY_FILE=$1
MONITOR_HOST=$2

while true
do
    ssh -i $KEY_FILE heat-admin@$MONITOR_HOST "sudo rabbitmqctl -t 1 list_queues name consumers consumer_utilisation memory 2>/dev/null| grep conductor|grep -v fanout" 2>/dev/null

    sleep 5
done