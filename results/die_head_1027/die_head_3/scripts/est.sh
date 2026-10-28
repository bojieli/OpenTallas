#!/bin/bash
# DIE-HEAD-3 estimate: re-cut maps at dmax D on the routed sfb250c feed, box-clean, then die STA related pairs (main model)
set -u
WT=/srv/opentallas-scratch2/claude/wt/die-head-1; B=/srv/opentallas-scratch2/claude/die-head-3; S=$WT/results/die_head_1027/scripts
RUN=/srv/opentallas-scratch2/claude/die-head-1/sfb250c
J=/srv/opentallas-scratch2/claude/land-head-1/compose/fb1_lat.json
P=$WT/physical/die_plan/s81_head/die_plan.json
ulimit -v 32000000
for D in "$@"; do
  O=$B/d$D; mkdir -p $O
  python3 $S/feed_map.py $J $RUN/landed_ocv.json $O/map_raw.json --dmax $D
  python3 $S/box_fix.py $J $O/map_raw.json $O/map.json | tail -2
  python3 $S/mk_proof.py $RUN $O/map.json $O/proof > $O/mk_proof.log 2>&1 || { echo MKPROOF_FAIL; tail -3 $O/mk_proof.log; }
  for HB in none HB4; do
    python3 $WT/tools/die_plan/die_sta_related.py $O/proof --plan $P --out $O/sta_$HB --corner TT --corner FF \
      --clock-ocv table --clock-droop shared --droop-regions $O/proof/droop_regions.json --hold-buffers $HB > $O/sta_$HB.log 2>&1
    echo "D=$D HB=$HB"; grep -E "seam  |landed  " $O/sta_$HB.log | cut -c1-140; grep SUMMARY $O/sta_$HB.log | python3 -c "import json,sys;s=json.loads(sys.stdin.read()[8:]);print(json.dumps(s['seam'])[:400])"
  done
done
