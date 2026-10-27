#!/bin/bash
cd /srv/opentallas-scratch2/claude/kv-cores-r6; ulimit -v 48000000
T=/srv/opentallas-scratch2/claude/clock-kv-r24-1027/tools/die_plan
export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r19-1027/in/pylib:$T
CE=/srv/opentallas-scratch2/claude/kv-core-slice-1-1027/pd/hm_cells_evidence.json
(python3 $T/check.py pdR6/hm_r24.json --out g0_r6 --cells-evidence $CE > g0_r6.log 2>&1; echo g0 rc=$? >> g0.done) &
(python3 $T/check.py pdR6/hm_r24.json --out g0c_r6 --completeness --cells-evidence $CE > g0c_r6.log 2>&1; echo g0c rc=$? >> g0.done) &
wait; echo ALL >> g0.done
