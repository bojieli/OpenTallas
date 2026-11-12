#!/bin/bash
R=/srv/opentallas-scratch2/claude/die-s81-85/compose1111; cd $R/repo
O=$R/out/s87_ready12b2s; mkdir -p $O
python3 -I $R/s87/apply_psplit_1112.py $R/out/s87_ready12b2-test/plan.json $O/plan.json $O/apply_report.json --splits $R/s87/split_all.json > $O/apply.log 2>&1 || { echo APPLYFAIL >> $O/g0.rc; exit 1; }
H=physical/die_plan/s81
cp $O/plan.json $H/.g0_r12b2s.json; mkdir -p $O/g0c $O/g0_plain
nice -n 19 python3 -I tools/die_plan/check.py $H/.g0_r12b2s.json --completeness --out $O/g0c --quiet > $O/g0c.log 2>&1; echo "c rc=$?" >> $O/g0.rc
nice -n 19 python3 -I tools/die_plan/check.py $H/.g0_r12b2s.json --out $O/g0_plain --quiet > $O/g0_plain.log 2>&1; echo "p rc=$?" >> $O/g0.rc
rm -f $H/.g0_r12b2s.json; echo DONE >> $O/g0.rc
