#!/bin/bash
# HBM-GAPS-2 gqmx event replay + checks. Run from the worktree root. RR = scratch dir for base/new plans and reports.
set -e
RR=${RR:-/srv/opentallas-scratch2/claude/hbm-gaps-2/rgqmx}; D=physical/die_plan/hbm/plan_of_record/d44v; F=results/die_hbm_1105/gq_land_mx
export PYTHONDONTWRITEBYTECODE=1
rm -rf $RR; mkdir -p $RR/g0 $RR/geom
cp -r $D $RR/base; (cd $RR/base; find . -name "*.gz" -exec gunzip {} +)
[ "$(awk "\$2==\"die_plan.json\"{print \$1}" $RR/base/SHA256SUMS)" = "$(sha256sum $RR/base/die_plan.json | cut -d" " -f1)" ] && echo base plan = SHA256SUMS || { echo MISMATCH; exit 3; }
cp -al $RR/base $RR/new; cp --remove-destination $RR/base/die_plan.json $RR/new/die_plan.json
python3 -I $F/mk_gqmx.py $RR/new
export PYTHONPATH=tools/die_plan:tools/autopilot
for N in base new; do
( prlimit --as=48000000000 timeout 1500 python3 tools/die_plan/check.py $RR/$N/die_plan.json --out $RR/g0/$N --core-conns $RR/$N/core_conns.json --core-macros $RR/$N/core_macros.json --plan-geom off > $RR/g0/$N.log 2>&1; echo G0$N rc $? ) &
( prlimit --as=48000000000 timeout 1500 python3 tools/die_plan/plan_geom.py $RR/$N/die_plan.json --json $RR/geom/plan_geom_$N.json > $RR/geom/geom_$N.log 2>&1; echo GEOM$N rc $? ) & done; wait
python3 -I results/die_hbm_1103/reform/g0cmp.py $RR/g0/base/g0_report.json $RR/g0/new/g0_report.json 2>&1 | cut -c1-300 | head -12 | tee $RR/g0.txt
python3 -I results/die_hbm_1103/reform/geomcmp.py $RR/geom/plan_geom_base.json $RR/geom/plan_geom_new.json 2>&1 | cut -c1-300 | head -10 | tee $RR/geom.txt
echo DONE
