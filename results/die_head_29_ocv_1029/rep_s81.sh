#!/bin/bash
# DIE-HEAD-29 replay: DIE-S81-17 cabind die_sta_related (go15 proof, plan_s11, CA width bind with START ports), base vs new
B=/srv/opentallas-scratch2/claude/die-head-29-ocv-base; W=/srv/opentallas-scratch2/claude/wt/die-head-29-ocv; O=$B/rep
P=/srv/opentallas-scratch2/claude/die-s81-16/go15/proof; PL=/srv/opentallas-scratch2/claude/die-s81-16/plan/plan_s11.json
for T in base new; do
  [ $T = base ] && S=$B/tools/die_plan || S=$W/tools/die_plan
  ( mkdir -p $O/s81_$T; cp -r /srv/opentallas-scratch2/claude/die-s81-17/cabind/sta/regchar $O/s81_$T/; python3 $S/die_sta_related.py $P --plan $PL --out $O/s81_$T --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $P/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --clock-cell inv2 --core-insertion declared --count-align /srv/opentallas-scratch2/claude/die-s81-17/cabind/bind.json --count-align-key region > $O/s81_$T.log 2>&1; echo S81 $T rc $? $(date) ) &
done
wait
