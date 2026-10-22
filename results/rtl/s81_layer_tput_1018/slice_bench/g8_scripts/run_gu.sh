#!/bin/bash
cd /srv/opentallas-scratch/claude/tok-s81-gu
for m in $@; do
  n=$(python3 -c "import json;print(json.load(open('$m/replay.json'))['ncyc'])")
  OBJ=/srv/opentallas-scratch/claude/tok-s81-gu/out_gu_idle/obj bash K_cut_gu/run_dv_slice.sh K_cut_gu out_$m +IN=/srv/opentallas-scratch/claude/tok-s81-gu/$m/in.txt +OUT=/srv/opentallas-scratch/claude/tok-s81-gu/$m/out.txt +NCYC=$n +TRACE=/srv/opentallas-scratch/claude/tok-s81-gu/out_$m/trace.txt 2>&1 | grep -v MISMATCH; echo "$m rc $?"
  grep -c MISMATCH out_$m/run.log
done
