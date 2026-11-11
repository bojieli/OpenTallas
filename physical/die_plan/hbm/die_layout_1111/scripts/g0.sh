#!/bin/bash
# usage: g0.sh PLANDIR OUTDIR  (G0 = check.py of tools d54b96cc27, as HBM-COMPOSE)
W=/srv/opentallas-scratch3/claude/die-layout-hbm; P=$1; O=$2; mkdir -p $O
cd $W/tools_d54 && nice -n 19 python3 -I tools/die_plan/check.py $P/die_plan.json --out $O/g0_report.json --quiet > $O/g0.log 2>&1; echo "rc $?" >> $O/g0.log
python3 -I $W/hcbin/g0cmp.py $W/b0/t10.g0/g0_report.json/g0_report.json $O/g0_report.json/g0_report.json > $O/g0cmp.txt 2>&1
