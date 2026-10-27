#!/bin/bash
# gate.sh PLAN_DIR GATE_DIR [diag]: copy die_plan.json + cores/ and run check.py G0 and G0C (diag = schema errors recorded, ignored)
P=$1; G=$2; M=${3:-strict}; T=${GT:-/srv/opentallas-scratch2/claude/hbm-mu-quad-3-1027/schema_test/b1n/tools/die_plan}
rm -rf $G; mkdir -p $G; cp $P/die_plan.json $G/; cp -r $P/cores $G/; [ -f $P/core_conns.json ] && cp $P/core_conns.json $G/
cd $G
if [ $M = diag ]; then RUN="python3 /srv/opentallas-scratch2/claude/hbm-mu-quad-2-1026/diag_check.py $T"; else RUN="python3 $T/check.py"; fi
$RUN die_plan.json --out gates/g0 > g0.log 2>&1; echo $? > g0.exit
$RUN die_plan.json --completeness --out gates/g0c > g0c.log 2>&1; echo $? > g0c.exit
tail -1 g0.log; tail -1 g0c.log
