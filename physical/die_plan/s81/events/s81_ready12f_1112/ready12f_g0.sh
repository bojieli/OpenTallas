#!/bin/bash
R=/srv/opentallas-scratch2/claude/die-s81-85/compose1111; cd $R/repo
H=physical/die_plan/s81; O=$R/out/s87_ready12fs
cp $O/plan.json $H/.g0_r12f_ws811.json
mkdir -p $O/g0c $O/g0_plain
nice -n 19 python3 -I tools/die_plan/check.py $H/.g0_r12f_ws811.json --completeness --out $O/g0c --quiet > $O/g0c.log 2>&1; echo "c rc=$?" > $O/g0.rc
nice -n 19 python3 -I tools/die_plan/check.py $H/.g0_r12f_ws811.json --out $O/g0_plain --quiet > $O/g0_plain.log 2>&1; echo "p rc=$?" >> $O/g0.rc
rm -f $H/.g0_r12f_ws811.json
echo DONE >> $O/g0.rc
