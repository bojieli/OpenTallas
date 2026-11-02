#!/bin/bash
# DIE-HBM-57: build +1-station variant V (mk_d), regenerate latency table, G0/G0C
R=/srv/opentallas-scratch2/claude/die-hbm-57; W=/srv/opentallas-scratch2/claude/wt/die-hbm-56; S=/srv/opentallas-scratch2/claude/codex-hbm-stationclock-1101/s11
V=$1; shift; mkdir -p $R/plan_s11/$V; cd $W
[ -f $R/plan_s11/$V/die_plan.json ] || python3 $R/mk_d.py $S/die_plan.json $R/plan_s11/$V/die_plan.json "$@" > $R/plan_s11/$V.log 2>&1
for f in $S/*; do b=$(basename $f); [ "$b" = die_plan.json ] || [ -e $R/plan_s11/$V/$b ] || ln -s $f $R/plan_s11/$V/$b; done
python3 tools/die_plan/gen.py latency $R/plan_s11/$V/die_plan.json --inplace > $R/plan_s11/$V.lat.log 2>&1; echo "lat rc $?" >> $R/plan_s11/$V.lat.log
bash $R/g0.sh c11$V $R/plan_s11/$V/die_plan.json; echo DONE >> $R/plan_s11/$V.lat.log
