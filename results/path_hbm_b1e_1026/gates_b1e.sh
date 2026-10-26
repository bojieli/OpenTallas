#!/bin/bash
# b1e static gates: main tools (fec963a5e8 incl. master-plan r3 028148d76) in claude/hbm-b1e-1026 worktree
B=/srv/opentallas-scratch2/claude/path-hbm/b1e_1026; W=/srv/opentallas-scratch2/claude/wt/hbm-b1e-1026
cd $B/plan_b1e
( python3 $W/tools/die_plan/check.py die_plan.json --out gates/g0 --png > gates-g0.log 2>&1; echo $? > gates-g0.exit ) &
( python3 $W/tools/die_plan/check.py die_plan.json --completeness --out gates/g0c > gates-g0c.log 2>&1; echo $? > gates-g0c.exit ) &
( python3 $W/tools/die_plan/die_infra.py master-plan die_plan.json --out $B/mp_main_b1e --entries entries.json > $B/mp_main_b1e.log 2>&1; echo $? > $B/mp_main_b1e.exit ) &
wait; echo done
