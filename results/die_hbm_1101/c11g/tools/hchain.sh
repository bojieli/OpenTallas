#!/bin/bash
# DIE-HBM-57 H: su00 L730x1 = G + 1 station (mk_d) -> per-bit siting -> compose (hop-checked) -> latency + G0/G0C
R=/srv/opentallas-scratch2/claude/die-hbm-57; W=/srv/opentallas-scratch2/claude/wt/die-hbm-56; G=$R/plan_s11/G
lat() { (cd $W && python3 tools/die_plan/gen.py latency $1 --inplace) > $1.lat.log 2>&1; echo "lat rc $?" >> $1.lat.log; }
side() { for f in $G/*; do b=$(basename $f); [ "$b" = die_plan.json ] || [ "$b" = c11g_patch.json.gz ] || [ -e $1/$b ] || ln -s $(readlink -f $f) $1/$b; done; }
mkdir -p $R/plan_s11/H0 $R/plan_s11/H $R/swH/t
cd $W && python3 $R/mk_d.py $G/die_plan.json $R/plan_s11/H0/die_plan.json q_su00:L730x1 q_su00__physical_v1:L730x1 > $R/plan_s11/H0.log 2>&1
side $R/plan_s11/H0; lat $R/plan_s11/H0/die_plan.json
for t in q_su00 q_su00__physical_v1; do
  (cd $W && timeout 5400 python3 $R/sweep_site.py $W $R/plan_s11/H0/die_plan.json $R/swH/t/$t.json $R/swH/t/$t.ledger.json --types $t > $R/swH/t/$t.log 2>&1) &
done; wait
cd $W && python3 $R/compose_auto.py $R/plan_s11/H0/die_plan.json $R/swH $R/plan_s11/H/die_plan.json > $R/plan_s11/H.compose.log 2>&1
side $R/plan_s11/H; lat $R/plan_s11/H/die_plan.json
python3 $R/cbox.py $R/plan_s11/H/die_plan.json q_su00 q_su00__physical_v1 > $R/plan_s11/H.cbox.log 2>&1
bash $R/g0.sh c11H $R/plan_s11/H/die_plan.json
touch $R/plan_s11/H.DONE
