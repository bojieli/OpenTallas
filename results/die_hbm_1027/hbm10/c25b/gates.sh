#!/bin/bash
# DIE-HBM-10: G0/G0C on C25a with the SAME tools snapshot as the C21 / C20j runs (die-hbm-9/mainsnap), for a clean diff
cd /srv/opentallas-scratch2/claude/die-hbm-10/c25b
C=/srv/opentallas-scratch2/claude/die-hbm-9/mainsnap/tools/die_plan/check.py
ulimit -v 24000000
(nice python3 $C die_plan.json --out gates/g0 > gates_g0.log 2>&1; echo $? > gates_g0.exit) &
(nice python3 $C die_plan.json --completeness --out gates/g0c > gates_g0c.log 2>&1; echo $? > gates_g0c.exit) &
wait
