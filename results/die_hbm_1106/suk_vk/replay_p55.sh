#!/bin/bash
# HBM-CONS-2/SUK d44v part 55 replay.  Run from the repo root.  replay_p55.sh RR   (RR = new work dir, CORES_FILL = full d44 cores dir).
# Unpacks d44v into RR/base, applies mk_p55.py (+ ft_nudge, ft_reach_fix as ev76/p42) on RR/new, then G0 + plan-time GEOM base vs new.  PACK=1 packages RR/new into d44v.
set -e
RR=$1; export PYTHONDONTWRITEBYTECODE=1
D=physical/die_plan/hbm/plan_of_record/d44v; F=results/die_hbm_1106/suk_vk
rm -rf $RR; mkdir -p $RR/base/cores $RR/g0 $RR/geom
for f in $D/*.json $D/*.json.gz; do n=$(basename $f .gz); case $f in *.gz) zcat $f > $RR/base/$n;; *) cp $f $RR/base/$n;; esac; done
for f in $D/cores/*; do n=$(basename $f .gz); case $f in *.gz) zcat $f > $RR/base/cores/$n;; *) cp $f $RR/base/cores/$n;; esac; done
python3 -I results/die_hbm_1105/q3split_p34/fill_cores.py $RR/base ${CORES_FILL:-/srv/opentallas-scratch3/claude/die-hbm-60-plan/p/d44v11/cores}
cp -r $RR/base $RR/new
python3 $F/mk_p55.py $RR/new | tee $RR/mk.log
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_nudge.py $RR/new/die_plan.json $RR/new/die_plan.nudged.json $RR/ft_nudge_ledger.json && mv $RR/new/die_plan.nudged.json $RR/new/die_plan.json
PYTHONPATH=tools/die_plan:tools python3 tools/die_plan/ft_reach_fix.py $RR/new/die_plan.json $RR/new/die_plan.reach.json $RR/ft_reach_ledger.json || true; [ -f $RR/new/die_plan.reach.json ] && mv $RR/new/die_plan.reach.json $RR/new/die_plan.json
echo PLAN_READY > $RR/plan_ready
export PYTHONPATH=tools/die_plan:tools/autopilot
for N in base new; do ( timeout 1800 python3 tools/die_plan/check.py $RR/$N/die_plan.json --out $RR/g0/$N --core-conns $RR/$N/core_conns.json --core-macros $RR/$N/core_macros.json --plan-geom off > $RR/g0/$N.log 2>&1; echo G0$N rc $? ) &
( timeout 1800 python3 tools/die_plan/plan_geom.py $RR/$N/die_plan.json --json $RR/geom/plan_geom_$N.json > $RR/geom/geom_$N.log 2>&1; echo GEOM$N rc $? ) & done; wait
python3 -I results/die_hbm_1103/reform/g0cmp.py $RR/g0/base/g0_report.json $RR/g0/new/g0_report.json 2>&1 | cut -c1-300 | head -14 | tee $RR/g0.txt
python3 -I results/die_hbm_1103/reform/geomcmp.py $RR/geom/plan_geom_base.json $RR/geom/plan_geom_new.json 2>&1 | cut -c1-300 | head -12 | tee $RR/geom.txt
echo REPLAY DONE
