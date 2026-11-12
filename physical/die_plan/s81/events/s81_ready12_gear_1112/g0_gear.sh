#!/bin/bash
R=/srv/opentallas-scratch2/claude/die-s81-85/compose1111; cd $R/repo
H=physical/die_plan/s81
cp $R/out/s87_ready12g/plan.json $H/.g0_gear_ws811.json
mkdir -p $R/out/s87_ready12g/g0c $R/out/s87_ready12g/g0_plain
nice -n 19 python3 -I tools/die_plan/check.py $H/.g0_gear_ws811.json --completeness --out $R/out/s87_ready12g/g0c --quiet > $R/out/s87_ready12g/g0c.log 2>&1; echo "c rc=$?" > $R/out/s87_ready12g/g0.rc
nice -n 19 python3 -I tools/die_plan/check.py $H/.g0_gear_ws811.json --out $R/out/s87_ready12g/g0_plain --quiet > $R/out/s87_ready12g/g0_plain.log 2>&1; echo "p rc=$?" >> $R/out/s87_ready12g/g0.rc
rm -f $H/.g0_gear_ws811.json
