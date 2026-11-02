#!/bin/bash
# HBM-CORES-KITS-41 G0/G0C on a plan dir with tools at my wt (main 6defc3c2306). usage: g0.sh NAME PLANDIR
R=/srv/opentallas-scratch2/claude/hbm-cores-kits-41; W=$R/wt; P=$1; D=$2
mkdir -p $R/g0/$P; cd $W; ulimit -v 40000000
( python3 tools/die_plan/check.py $D/die_plan.json --out $R/g0/$P/g0_report.json > $R/g0/$P/g0.log 2>&1; echo $? > $R/g0/$P/g0.rc ) &
( python3 tools/die_plan/check.py $D/die_plan.json --completeness --out $R/g0/$P/g0c_report.json > $R/g0/$P/g0c.log 2>&1; echo $? > $R/g0/$P/g0c.rc ) &
wait
