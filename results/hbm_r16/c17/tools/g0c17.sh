#!/bin/bash
# HBM-R16/C17: G0C in parallel (chain scripts ran G0 then G0C serially: "a; b &" backgrounds only b)
C=/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan/check.py
cd /srv/opentallas-scratch2/claude/hbm-r16-1027/$1
python3 $C die_plan.json --completeness --out gates/br_g0c_p > gates_br_g0c_p.log 2>&1
echo $? > gates_br_g0c_p.exit
