#!/bin/bash
# HBM-COMPOSE G0: check.py (tools d54b96cc27, same as the 29333b2b/70c3e990 G0) on PLANDIR/die_plan.json -> PLANDIR.g0/
set -u
W=/srv/opentallas-scratch2/claude/hbm-cut-1111
P=$1; O=$2
mkdir -p $O
cd $W/tools_g0ft0
nice python3 -I tools/die_plan/check.py $P/die_plan.json --out $O/g0_report.json --quiet > $O/g0.log 2>&1
echo "rc $?" >> $O/g0.log
