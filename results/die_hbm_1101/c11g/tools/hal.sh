#!/bin/bash
# DIE-HBM-57 H: su00 L730x1 single-alpha sweeps on H0, compose each (die-hop checked), G0 on the best kept
R=/srv/opentallas-scratch2/claude/die-hbm-57; W=/srv/opentallas-scratch2/claude/wt/die-hbm-56; H0=$R/plan_s11/H0
for al in .75 .5 .35 .25 .15; do n=${al#.}; mkdir -p $R/swH$n/t
 for t in q_su00 q_su00__physical_v1; do
  (cd $W && timeout 5400 python3 $R/sweep_site.py $W $H0/die_plan.json $R/swH$n/t/$t.json $R/swH$n/t/$t.ledger.json --types $t --alphas $al > $R/swH$n/t/$t.log 2>&1) &
 done
done; wait
for al in .75 .5 .35 .25 .15; do n=${al#.}; mkdir -p $R/plan_s11/H$n
 (cd $W && python3 $R/compose_auto.py $H0/die_plan.json $R/swH$n $R/plan_s11/H$n/die_plan.json > $R/plan_s11/H$n.compose.log 2>&1)
 echo "a$al $(grep -E '^KEPT' $R/plan_s11/H$n.compose.log)"
done > $R/plan_s11/Hal.summary
touch $R/plan_s11/Hal.DONE
