#!/bin/bash
# usage: gates.sh PLANDIR -> PLANDIR/gates/{b1n,br}_{g0,g0c}
set -u
P=$1; cd $P; mkdir -p gates
B1N=/srv/opentallas-scratch2/claude/codex-hbm-1027/gate_tools
BR=/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-0815/tools/die_plan
run() { python3 $2/check.py die_plan.json --quiet $3 --out gates/$1 > gates/$1.log 2>&1; echo $? > gates/$1.exit; }
run b1n_g0 $B1N "" &
run b1n_g0c $B1N --completeness &
run br_g0 $BR "" &
run br_g0c $BR --completeness &
wait
tail -n 2 gates/*.log
