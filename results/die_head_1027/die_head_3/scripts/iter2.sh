#!/bin/bash
# DIE-HEAD-3 hybrid v2: forced cuts = in-region pairs failing die STA after HB4 under EITHER HB4 delay model (plan, abutted)
set -u
WT=/srv/opentallas-scratch2/claude/wt/die-head-1; B=/srv/opentallas-scratch2/claude/die-head-3; S=$WT/results/die_head_1027/scripts
RUN=/srv/opentallas-scratch2/claude/die-head-1/sfb250c; J=/srv/opentallas-scratch2/claude/land-head-1/compose/fb1_lat.json
P=$WT/physical/die_plan/s81_head/die_plan.json; O=$B/hyb2; mkdir -p $O; cp $B/hyb/cut.txt $O/cut.txt
ulimit -v 32000000
for it in 1 2 3 4 5 6; do
  python3 $B/feed_map_x.py $J $RUN/landed_ocv.json $O/map_raw.json --dmax 300 --cut $O/cut.txt
  python3 $S/box_fix.py $J $O/map_raw.json $O/map.json | tail -1 | cut -c1-30
  python3 $S/mk_proof.py $RUN $O/map.json $O/proof > $O/mk_proof.log 2>&1
  n=0
  for M in plan abutted; do
    python3 $WT/tools/die_plan/die_sta_related.py $O/proof --plan $P --out $O/sta_$M --corner TT --corner FF \
      --clock-ocv table --clock-droop shared --droop-regions $O/proof/droop_regions.json --hold-buffers HB4 --hb4-delay $M > $O/sta_$M.log 2>&1
    grep SUMMARY $O/sta_$M.log | python3 -c "import json,sys;s=json.loads(sys.stdin.read()[8:]);print('$M',json.dumps(s['seam'])[:330])"
    m=$(python3 $B/addcut.py $O/sta_$M/die_sta_related.json $P $O/cut.txt); n=$((n+m))
  done
  echo "iter $it new cuts $n"; [ "$n" = 0 ] && break
done
