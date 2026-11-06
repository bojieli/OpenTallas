#!/bin/bash
# DIE-HBM-75 ev74 follow-on (COORD 14:01 + 15:0x): HBM-BIND-10 C-form delta (apply_event.sh) on the ev74 d44v, then
# L15x1 +1 station (+1 pin cycle on L15/L15m), then ft_nudge + ft_reach_fix for C-form slots under ev74-moved cores,
# then plan-time G0/GEOM vs the ev74 plan (advisory). Run from the worktree root on a tree that has ev74 committed.
set -e
RR=${RR:-/srv/opentallas-scratch2/claude/die-hbm-75/rev75g}; D=physical/die_plan/hbm/plan_of_record/d44v; F=results/hbm_bind_10_1105
export PYTHONDONTWRITEBYTECODE=1
rm -rf $RR; mkdir -p $RR/g0 $RR/geom $RR/ev74
git show ${BASE:-HEAD}:$D/die_plan.json.gz | gunzip -c > $RR/ev74.json   # the ev74 plan as committed (the d44v file in the tree may already hold this event)
python3 -I $F/plan_delta.py apply $RR/ev74.json $F/delta_714_k13f.json.gz $RR/c.json > $RR/apply.log; grep -c CONFLICT $RR/apply.log || true
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_add_station.py $RR/c.json $RR/l15.json $RR/ft_add_station_ledger.json q_b011:L15x1,q_b011__physical_v1:L15x1 L15,L15m
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_nudge.py $RR/l15.json $RR/nudged.json $RR/ft_nudge_ledger.json
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_reach_fix.py $RR/nudged.json $RR/new.json $RR/ft_reach_ledger.json || true
[ "${MKONLY:-0}" = 1 ] && exit 0
export PYTHONPATH=tools/die_plan:tools/autopilot
cp -al $D/. $RR/ev74/ 2>/dev/null || cp -r $D/. $RR/ev74/; (cd $RR/ev74; for f in core_conns clock_entries hard_reset_trees; do gunzip -kf $f.json.gz; done)
for N in ev74 new; do P=$RR/$N.json; [ $N = ev74 ] && P=$RR/ev74.json
( prlimit --as=48000000000 timeout 1500 python3 tools/die_plan/check.py $P --out $RR/g0/$N --core-conns $RR/ev74/core_conns.json --core-macros $D/core_macros.json --plan-geom off > $RR/g0/$N.log 2>&1; echo G0$N rc $? ) &
( prlimit --as=48000000000 timeout 1500 python3 tools/die_plan/plan_geom.py $P --json $RR/geom/plan_geom_$N.json > $RR/geom/geom_$N.log 2>&1; echo GEOM$N rc $? ) & done; wait
python3 -I results/die_hbm_1103/reform/g0cmp.py $RR/g0/ev74/g0_report.json $RR/g0/new/g0_report.json 2>&1 | cut -c1-300 | tee $RR/g0.txt
python3 -I results/die_hbm_1103/reform/geomcmp.py $RR/geom/plan_geom_ev74.json $RR/geom/plan_geom_new.json 2>&1 | cut -c1-300 | head -14 | tee $RR/geom.txt
echo DONE
