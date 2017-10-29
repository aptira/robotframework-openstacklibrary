#!/bin/bash

KEY_FILE=$1
MONITOR_HOST=$2

ssh -i $KEY_FILE cloud-user@$MONITOR_HOST "sudo vmstat 2" 2>/dev/null