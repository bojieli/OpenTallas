#!/bin/bash
# DIE-HBM-74 ev74 event replay + plan-time G0/GEOM (advisory). Run from the worktree root. RR = scratch; KP = kit pin tables.
set -e
RR=${RR:-/srv/opentallas-scratch2/claude/die-hbm-74/rev74}; KP=${KP:-/srv/opentallas-scratch2/claude/die-hbm-74/ev/kitpins}
D=physical/die_plan/hbm/plan_of_record/d44v; F=results/die_hbm_1105/ev74
export PYTHONDONTWRITEBYTECODE=1
rm -rf $RR; mkdir -p $RR/g0 $RR/geom
cp -r $D $RR/base; (cd $RR/base; find . -name "*.gz" -exec gunzip {} +)
[ "$(awk "\$2==\"die_plan.json\"{print \$1}" $RR/base/SHA256SUMS)" = "$(sha256sum $RR/base/die_plan.json | cut -d" " -f1)" ] && echo base plan = SHA256SUMS || { echo MISMATCH; exit 3; }
cp -al $RR/base $RR/new; for f in die_plan.json core_macros.json; do cp --remove-destination $RR/base/$f $RR/new/$f; done
python3 -I $F/mk_ev74.py $RR/new physical/die_plan/hbm/plan_of_record $KP | tee $RR/mk.log
# station cells the moved hard cores now cover: minimal re-site (ft_nudge: only hit bits move; counts/windows/pins unchanged)
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_nudge.py $RR/new/die_plan.json $RR/new/die_plan.nudged.json $RR/new/ft_nudge_ledger.json && mv $RR/new/die_plan.nudged.json $RR/new/die_plan.json
# DIE-HBM-75: reach-aware re-site of the S1 bits ft_nudge pushed past 405 um (rc 1 = some bits left, listed in the ledger)
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_reach_fix.py $RR/new/die_plan.json $RR/new/die_plan.reach.json $RR/new/ft_reach_ledger.json || true; mv $RR/new/die_plan.reach.json $RR/new/die_plan.json
[ "${MKONLY:-0}" = 1 ] && exit 0
export PYTHONPATH=tools/die_plan:tools/autopilot
for N in base new; do
( prlimit --as=48000000000 timeout 1500 python3 tools/die_plan/check.py $RR/$N/die_plan.json --out $RR/g0/$N --core-conns $RR/$N/core_conns.json --core-macros $RR/$N/core_macros.json --plan-geom off > $RR/g0/$N.log 2>&1; echo G0$N rc $? ) &
( prlimit --as=48000000000 timeout 1500 python3 tools/die_plan/plan_geom.py $RR/$N/die_plan.json --json $RR/geom/plan_geom_$N.json > $RR/geom/geom_$N.log 2>&1; echo GEOM$N rc $? ) & done; wait
python3 -I results/die_hbm_1103/reform/g0cmp.py $RR/g0/base/g0_report.json $RR/g0/new/g0_report.json 2>&1 | cut -c1-300 | head -20 | tee $RR/g0.txt
python3 -I results/die_hbm_1103/reform/geomcmp.py $RR/geom/plan_geom_base.json $RR/geom/plan_geom_new.json 2>&1 | cut -c1-300 | head -14 | tee $RR/geom.txt
echo DONE
