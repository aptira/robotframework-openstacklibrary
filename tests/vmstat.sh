#!/bin/bash

KEY_FILE=$1
MONITOR_HOST=$2
LOG_FILE=$3

ssh -i $KEY_FILE cloud-user@$MONITOR_HOST vmstat 1 1 2>/dev/null
sleep 1
while true
do
    ssh -i $KEY_FILE cloud-user@$MONITOR_HOST vmstat 1 1 2>/dev/null | tail -n1
    sleep 1
done