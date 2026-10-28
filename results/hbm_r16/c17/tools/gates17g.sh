#!/bin/bash
# HBM-R16/C17g = C17 + pin6 re-spread (pin tables only): G0 + G0C
cd /srv/opentallas-scratch2/claude/hbm-r16-1027/c17g
sha256sum die_plan.json > die_plan.sha256; (cd cores && sha256sum *.json) > cores.sha256
C=/srv/opentallas-scratch2/claude/wt/codex-hbm-plan-1351/tools/die_plan/check.py
python3 $C die_plan.json --out gates/br_g0 > gates_br_g0.log 2>&1; echo $? > gates_br_g0.exit &
python3 $C die_plan.json --completeness --out gates/br_g0c > gates_br_g0c.log 2>&1; echo $? > gates_br_g0c.exit &
wait
