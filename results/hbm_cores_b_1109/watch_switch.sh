#!/bin/bash
# waits (up to 3h) until the QC die entry in the hub kit_wave.json references the qct11/wave src_lf tree.
end=$(( $(date +%s)+10800 ))
while [ $(date +%s) -lt $end ]; do
  s=$(ssh -n -o ControlPath=none -o ConnectTimeout=20 intel2 'python3 -I -c "
import json,os
d=json.load(open(os.path.expanduser(\"~/coord/autopilot/kit_wave.json\")))[\"dies\"][\"qwen_compute\"]
print(d.get(\"src\"),d.get(\"plan\"),d.get(\"src_sha\"))"' 2>/dev/null)
  case "$s" in *qct11/wave*|*7e4789*|*plan_qc53v4nS*) echo "SWITCHED: $s"; exit 0;; esac
  sleep 180
done
echo TIMEOUT; exit 1
