#!/bin/bash

if [ "$1" == "master" ]; then
    zfw -I -c $(host $(hostname) |awk -F'[[:space:]]+|=' '{print $4}') -m 32 -o 0.0.0.0 -n 0 -l 8081 -h 8081 -t 0 -p tcp
elif [ "$1" == "backup" ]; then
    zfw -D -c $(host $(hostname) |awk -F'[[:space:]]+|=' '{print $4}') -m 32 -o 0.0.0.0 -n 0 -l 8081 -h 8081 -t 0 -p tcp
else
    echo "no valid argument passed"
fi
