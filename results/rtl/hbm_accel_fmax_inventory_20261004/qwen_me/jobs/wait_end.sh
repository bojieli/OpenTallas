#!/bin/bash
# wait until the remote MANIFEST has more END lines than $1 (ssh retried); print the new END lines
n0=$1
while true; do
  out=$(ssh -o ConnectTimeout=20 ot-epyc1tb 'grep END /srv/opentallas-scratch/claude/hbm-fmax-qme/jobs/MANIFEST' 2>/dev/null) || { sleep 60; continue; }
  n=$(echo "$out" | grep -c END)
  if [ "$n" -gt "$n0" ]; then echo "$out" | tail -n $((n-n0)); exit 0; fi
  sleep 60
done
