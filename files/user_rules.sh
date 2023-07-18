#!/bin/bash
sudo /usr/sbin/zfw -R  $(/sbin/ip -o link show up|awk '$9=="UP" {print $2;}'|head -1|tr -d ":")