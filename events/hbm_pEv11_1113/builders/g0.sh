#!/bin/bash
# DIE-HBM-102: G0 check.py on a plan (same tool tree as pEv10's G0); usage g0.sh PLAN_NAME
S=/srv/opentallas-scratch2/claude/kw45/src_hbm_main_9fc09952cd_q0g_p18; W=/srv/opentallas-scratch2/claude/die-hbm-102
p=$1; O=$W/g0_$p; mkdir -p $O; cd $S
nice -n 10 python3 -I tools/die_plan/check.py $W/plans/$p/die_plan.json --out $O/g0_report.json --quiet > $O/g0.log 2>&1
echo "G0 $p rc $?"
