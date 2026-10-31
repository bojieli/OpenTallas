#!/bin/bash
R=/srv/opentallas-scratch2/claude/die-hbm-42; WT=/srv/opentallas-scratch2/claude/wt/die-hbm-42; P=$1
mkdir -p $R/g0/$P; cd $WT; ulimit -v 30000000
python3 tools/die_plan/check.py $R/plan/$P/die_plan.json --out $R/g0/$P/g0_report.json > $R/g0/$P/g0.log 2>&1; echo $? > $R/g0/$P/g0.rc &
python3 tools/die_plan/check.py $R/plan/$P/die_plan.json --completeness --out $R/g0/$P/g0c_report.json > $R/g0/$P/g0c.log 2>&1; echo $? > $R/g0/$P/g0c.rc
wait
