#!/bin/bash

set -e

MYIF=$(/sbin/ip -o link show up|awk '$9=="UP" {print $2;}'|head -1)
MYIP=$(/sbin/ip add show "${MYIF%:}"|awk '$1=="inet" {print $2;}')

if [ "$1" == "master" ]; then
    zfw -I -c $(echo $MYIP |awk -F'/' '{print $1}') -m 32 -o 0.0.0.0 -n 0 -l 8081 -h 8081 -t 0 -p tcp
elif [ "$1" == "backup" ]; then
    zfw -D -c $(echo $MYIP |awk -F'/' '{print $1}') -m 32 -o 0.0.0.0 -n 0 -l 8081 -h 8081 -t 0 -p tcp
else
    echo "no valid argument passed"
fi
