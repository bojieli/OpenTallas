#!/bin/bash
# DIE-HBM-5 C20i G0 + G0C in parallel (checks bypass admission), tools = worktree die-hbm-5 (1d784227c1)
cd /srv/opentallas-scratch2/claude/die-hbm-5/c20i_out2; mkdir -p gates/g0 gates/g0c
C=/srv/opentallas-scratch2/claude/wt/die-hbm-5/tools/die_plan/check.py
(nice python3 $C die_plan.json --out gates/g0 > gates_g0.log 2>&1; echo $? > gates_g0.exit) &
(nice python3 $C die_plan.json --completeness --out gates/g0c > gates_g0c.log 2>&1; echo $? > gates_g0c.exit) &
wait
