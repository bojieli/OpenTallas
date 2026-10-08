#!/bin/bash
# memory is the hard limit: if MemAvailable < 80 GB, kill this recheck's verilator_bin / cc1plus (lorentz-margin paths only)
D=/srv/opentallas-scratch/claude/tk-hbm-harvest/fsr
while [ ! -f $D/stop_guard ]; do
 a=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)
 if [ "$a" -lt 80 ]; then
  for p in $(ps -eo pid,args | awk '/tk-hbm-harvest\/lorentz-margin/ && /(verilator_bin|cc1plus)/ && !/awk/ {print $1}'); do kill $p; done
  echo "$(date) memguard kill avail=$a" >> $D/memguard.log
 fi
 sleep 15; done
