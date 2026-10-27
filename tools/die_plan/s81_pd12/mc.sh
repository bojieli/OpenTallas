#!/bin/bash
# PATH-S81-PD9 mesh MC sign-off (KV R18 recipe: main kv_r18/mesh_mc18.py, 24 samples, vt 10 mV, wire 5 %, tree 2 ps/stage,
# tree wire RC 3 %/edge, gradient 0.21 %/mm) on the me1 routed mesh; rec = s81_pd9/mesh_rec_s81.py (M8-row drivers)
R=/srv/opentallas-scratch2/claude/path-s81-pd12-1027; W=/srv/opentallas-scratch2/claude/wt/main-tools-pd9/tools/die_plan
P9=/srv/opentallas-scratch2/claude/wt/path-s81-pd9-1027/tools/die_plan; cd $R; B=${B:-me1}; mkdir -p mc
export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r18-1027/in/pylib
echo start $(date -Is)
python3 $P9/s81_pd9/mesh_rec_s81.py $B rec_$B.json > rec_$B.log 2>&1 || { cat rec_$B.log; exit 1; }
cat rec_$B.log
for C in TT FF; do python3 /srv/opentallas-scratch2/claude/wt/mc-gapfold-1027/tools/die_plan/kv_r18/mesh_mc18.py rec_$B.json --thev /srv/opentallas-scratch2/claude/clock-kv-r17-1027/thev_qc_m2.json --corner $C --samples 24 --routed $B/mesh_$C.json --out mc/${B}_$C.json --qc $W/kv_r7 ${EXTRA} > mc/${B}_$C.log 2>&1 & done; wait
grep -h SUMMARY mc/${B}_*.log
echo MC_DONE $(date -Is)
