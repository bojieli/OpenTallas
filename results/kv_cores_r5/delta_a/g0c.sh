#!/bin/bash
cd /srv/opentallas-scratch2/claude/kv-cores-r5; ulimit -v 48000000
T=/srv/opentallas-scratch2/claude/nc-headtr/tools/die_plan
export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r19-1027/in/pylib:$T
CE=/srv/opentallas-scratch2/claude/kv-core-slice-1-1027/pd/hm_cells_evidence.json
(python3 $T/check.py src_r22b/hm_r22b.json --out g0c_base --completeness --cells-evidence $CE > g0c_base.log 2>&1; echo base rc=$? >> g0c.done) &
(python3 $T/check.py pdA_r22b/hm_r22b_hdA.json --out g0c_A --completeness --cells-evidence $CE > g0c_A.log 2>&1; echo A rc=$? >> g0c.done) &
wait; echo ALL >> g0c.done
