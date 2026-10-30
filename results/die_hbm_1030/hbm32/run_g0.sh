#!/bin/bash
# G0 + G0C on plan dir $1 with tools of claude/die-hbm-31-wrap-1030@9a8d05473a3 (FLOW-5 alias + bind mapping)
T=/srv/opentallas-scratch2/claude/wt/die-hbm-32-tools/tools/die_plan; D=$1; O=$2; mkdir -p $O
rm -f $D/g0_report.json
systemd-run --user --scope -q -p MemoryMax=32G python3 $T/check.py $D/die_plan.json > $O/g0.log 2>&1; mv $D/g0_report.json $O/g0_report.json
systemd-run --user --scope -q -p MemoryMax=32G python3 $T/check.py $D/die_plan.json --completeness > $O/g0c.log 2>&1; mv $D/g0_report.json $O/g0c_report.json
echo done > $O/done
