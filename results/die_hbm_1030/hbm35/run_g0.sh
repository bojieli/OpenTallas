#!/bin/bash
# G0 + G0C on plan dir $1 -> $2 with main tools (die-hbm-35 sparse worktree, main 16f2590f75f >= 898f22b0f)
T=/srv/opentallas-scratch2/claude/wt/die-hbm-35/tools/die_plan; D=$1; O=$2; mkdir -p $O
cp -a $D $O/plan_copy_tmp 2>/dev/null; rm -rf $O/plan_copy_tmp
# check.py writes g0_report.json next to the plan: work on a hardlinked shadow dir so BASE is never written
S=$O/shadow; rm -rf $S; cp -al $D $S; rm -f $S/g0_report.json
systemd-run --user --scope -q -p MemoryMax=32G python3 $T/check.py $S/die_plan.json > $O/g0.log 2>&1; echo $? > $O/g0.rc; mv $S/g0_report.json $O/g0_report.json
systemd-run --user --scope -q -p MemoryMax=32G python3 $T/check.py $S/die_plan.json --completeness > $O/g0c.log 2>&1; echo $? > $O/g0c.rc; mv $S/g0_report.json $O/g0c_report.json
rm -rf $S; echo done > $O/done
