#!/bin/bash
# CLOCK-KV-R18 mesh re-sign: rec from the R18 build, MC 24 samples incl tree wire-RC 3 %/edge (RULING NUMBER-CHECK-KV-R17)
R=/srv/opentallas-scratch2/claude/clock-kv-r18-1027; W=/srv/opentallas-scratch2/claude/wt/clock-kv-r18/tools/die_plan; cd $R; B=${B:-r18}
export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r18-1027/in/pylib
python3 $W/kv_r18/mesh_rec18.py $B rec_$B.json > rec_$B.log 2>&1 || exit 1
for C in TT FF; do python3 $W/kv_r18/mesh_mc18.py rec_$B.json --thev /srv/opentallas-scratch2/claude/clock-kv-r17-1027/thev_qc_m2.json --corner $C --samples 24 --routed $B/mesh_$C.json --out mc/${B}_$C.json --qc $W/kv_r7 ${EXTRA} > mc/${B}_$C.log 2>&1 & done; wait
grep -h SUMMARY mc/${B}_*.log
