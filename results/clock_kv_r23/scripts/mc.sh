#!/bin/bash
# CLOCK-KV-R23: KV mesh re-sign with MAIN 8810c5e6a mesh_mc18 (finite physical gradient fix 78c678c92); same args as R18 mc.sh
R=/srv/opentallas-scratch2/claude/clock-kv-r23-1027; W=$R/tools/die_plan; cd $R; B=$1; BD=$2
export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r18-1027/in/pylib; ulimit -v 32000000
python3 $W/kv_r18/mesh_rec18.py $BD mc/rec_$B.json > mc/rec_$B.log 2>&1 || { echo REC_FAIL; exit 1; }
for C in TT FF; do python3 $W/kv_r18/mesh_mc18.py mc/rec_$B.json --thev /srv/opentallas-scratch2/claude/clock-kv-r17-1027/thev_qc_m2.json --corner $C --samples 24 --routed $BD/mesh_$C.json --out mc/${B}_$C.json --qc $W/kv_r7 > mc/${B}_$C.log 2>&1 & done; wait
grep -h SUMMARY mc/${B}_*.log; echo "MC_DONE $B $(date -Is)"
