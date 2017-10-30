#!/bin/bash

KEY_FILE=$1
MONITOR_HOST=$2

ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $KEY_FILE cloud-user@$MONITOR_HOST vmstat 1 2>/dev/null
