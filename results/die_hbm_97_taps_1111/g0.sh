#!/bin/bash
# HBM-TAPS G0 (DO_NOT_COUNT): base vs new with the ftres-fix branch tree d54b96cc27
cd /srv/opentallas-scratch2/claude/die-hbm-97-taps/repo
B=/srv/opentallas-scratch2/claude/die-hbm-97/plan_p11t_ftres_pgr; O=/srv/opentallas-scratch2/claude/die-hbm-97/plan_p11t_taps_cyc; G=/srv/opentallas-scratch2/claude/die-hbm-97-taps/g0
nice python3 -I tools/die_plan/check.py $B/die_plan.json --out $G/base/g0_report.json --quiet > $G/base.log 2>&1; echo "base rc $?" >> $G/rc.txt &
nice python3 -I tools/die_plan/check.py $O/die_plan.json --out $G/new/g0_report.json --quiet > $G/new.log 2>&1; echo "new rc $?" >> $G/rc.txt &
wait
