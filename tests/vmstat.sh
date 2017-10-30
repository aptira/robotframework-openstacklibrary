#!/bin/bash

KEY_FILE=$1
MONITOR_HOST=$2
LOG_FILE=$3

ssh -i $KEY_FILE cloud-user@$MONITOR_HOST vmstat 2 > $LOG_FILE