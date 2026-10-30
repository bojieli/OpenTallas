#!/usr/bin/env bash
# DIE-HBM-28 plan event: d26a -> pre-splits -> V-R1 S-row permutation (replan_event11) -> hbm23 post-fixes -> L202m -> latency -> G0
# usage: build_event.sh NAME "SPLIT1" "SPLIT2" ...   (SPLIT = "LANE WIDTHS")
set -eu; R=/srv/opentallas-scratch2/claude/die-hbm-28; TL=/srv/opentallas-scratch2/claude/wt/die-hbm-27/tools/die_plan
H=/srv/opentallas-scratch2/claude/wt/die-hbm-27/results/die_hbm_1029/hbm23/replan; N=$1; shift
cd $R/replan; rm -rf ../plan/${N}p VR1_$N ../plan/$N
cp -r /srv/opentallas-scratch2/claude/die-hbm-26/plan/d26a ../plan/${N}p
for s in "$@"; do python3 lane_presplit.py ../plan/${N}p/die_plan.json $s; done
python3 replan_event11.py $TL ../plan/${N}p VR1.json $PWD/VR1_$N --rows92 rows_vr1.json > VR1_$N.log 2>&1; tail -2 VR1_$N.log
P=VR1_$N/die_plan.json
python3 $H/order_fix.py $TL $P; python3 post_fix_h28.py $P VR1_$N/replan_report.json; python3 $H/post_fix2.py $P; python3 $H/post_fix3.py $TL $P
mv VR1_$N ../plan/$N; rm -rf ../plan/${N}p
python3 add_l202m.py $TL ../plan/$N/die_plan.json | tail -1
python3 $TL/gen.py latency ../plan/$N/die_plan.json --inplace --out ../plan/$N/lat >/dev/null
sha256sum ../plan/$N/die_plan.json | cut -c1-12
python3 $TL/check.py ../plan/$N/die_plan.json 2>&1 | tail -1
