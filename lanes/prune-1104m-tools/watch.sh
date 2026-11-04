#!/bin/bash
# PRUNE-1104M wake: exits when a scratch disk is low or after $1 minutes. epyc2 trigger is 85 because it already sits under 150.
s=$(date +%s); lim=$(( ${1:-40}*60 ))
while :; do
 for h in intel1:150 intel2:150 epyc2:85; do n=${h%:*}; t=${h#*:}; a=$(ssh -n -o ControlPath=none -o ConnectTimeout=20 $n "df -BG --output=avail /srv/opentallas-scratch2 | tail -1 | tr -dc 0-9"); [ -n "$a" ] && [ "$a" -lt "$t" ] && { echo "LOW $n $a GB $(date)"; exit 0; }; done
 [ $(( $(date +%s)-s )) -gt $lim ] && { echo "TIMER $(date)"; exit 0; }
 sleep 120
done
