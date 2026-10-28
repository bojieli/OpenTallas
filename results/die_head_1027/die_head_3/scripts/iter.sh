#!/bin/bash
# DIE-HEAD-3 hybrid: feed40 rule (|d|<=300) but every port whose in-region pair fails die STA (HB4 TT setup<0 or FF hold<0
# after HB4) is forced to be a crossing; iterate union-find -> box_fix -> STA until no in-region pair fails.
set -u
WT=/srv/opentallas-scratch2/claude/wt/die-head-1; B=/srv/opentallas-scratch2/claude/die-head-3; S=$WT/results/die_head_1027/scripts
RUN=/srv/opentallas-scratch2/claude/die-head-1/sfb250c; J=/srv/opentallas-scratch2/claude/land-head-1/compose/fb1_lat.json
P=$WT/physical/die_plan/s81_head/die_plan.json; O=$B/hyb; mkdir -p $O; : > $O/cut.txt
ulimit -v 32000000
for it in 1 2 3 4 5 6 7 8; do
  python3 $B/feed_map_x.py $J $RUN/landed_ocv.json $O/map_raw.json --dmax 300 --cut $O/cut.txt
  python3 $S/box_fix.py $J $O/map_raw.json $O/map.json | tail -1 | cut -c1-30
  python3 $S/mk_proof.py $RUN $O/map.json $O/proof > $O/mk_proof.log 2>&1
  python3 $WT/tools/die_plan/die_sta_related.py $O/proof --plan $P --out $O/sta --corner TT --corner FF \
      --clock-ocv table --clock-droop shared --droop-regions $O/proof/droop_regions.json --hold-buffers HB4 > $O/sta.log 2>&1
  grep -E "seam  " $O/sta.log | cut -c1-120
  n=$(python3 $B/addcut.py $O/sta/die_sta_related.json $P $O/cut.txt); echo "iter $it new cuts $n"
  [ "$n" = 0 ] && break
done
