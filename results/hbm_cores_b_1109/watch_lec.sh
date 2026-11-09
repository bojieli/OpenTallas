#!/bin/bash
# waits (up to 3h) for the hinted coll_core LEC ot-run client to end; prints the last log lines. No pgrep: reads the client's own "RAN"/"NOT" line.
L=/home/ubuntu/qct12-logs/coll_core_hint.otrun.log
end=$(( $(date +%s)+10800 ))
while [ $(date +%s) -lt $end ]; do
  s=$(ssh -n -o ControlPath=none -o ConnectTimeout=20 intel2 "tail -n 3 $L" 2>/dev/null)
  if echo "$s" | grep -q 'ot-run: \(RAN on\|NOT\)'; then echo "$s" | cut -c1-300; exit 0; fi
  sleep 120
done
echo TIMEOUT; exit 1
