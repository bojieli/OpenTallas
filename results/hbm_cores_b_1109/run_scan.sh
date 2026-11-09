#!/bin/bash
S=/tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad
for h in epyc2 epyc4 epyc5 epyc6; do
 ( ssh -o ControlPath=none -o BatchMode=yes $h 'mkdir -p ~/disk-urgent-3/scan' </dev/null
   scp -q -o ControlPath=none $S/du3_scan.py $h:disk-urgent-3/du3_scan.py
   timeout 3000 ssh -n -o ControlPath=none $h 'cd / && nice -n19 ionice -c3 bash -c "python3 -I ~/disk-urgent-3/du3_scan.py /srv/opentallas-scratch2 ~/disk-urgent-3/scan/s2.jsonl 2 & python3 -I ~/disk-urgent-3/du3_scan.py /srv/opentallas-scratch3 ~/disk-urgent-3/scan/s3.jsonl 2 & wait"; echo finished $(hostname)' ) &
done
wait
echo ALLDONE
