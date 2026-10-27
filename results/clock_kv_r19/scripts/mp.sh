#!/bin/bash
# CLOCK-KV-R19 task 4: master_plan + G0/G0C on the slice plan with R18 core taps + R19 PHY landed entries
cd /srv/opentallas-scratch2/claude/clock-kv-r19-1027/slice; ulimit -v 48000000; W=/srv/opentallas-scratch2/claude/wt/clock-kv-r19/tools/die_plan
python3 $W/master_plan.py pd/hm_r12.json --out mp_r19 --entries /srv/opentallas-scratch2/claude/kv-core-slice-1-1027/entries.json --mesh /srv/opentallas-scratch2/claude/clock-kv-r15-1026/r15 --no-render > mp_r19.log 2>&1; echo mp rc=$? >> mp.done
python3 $W/check.py pd/hm_r12.json --out g0_r19 --cells-evidence /srv/opentallas-scratch2/claude/kv-core-slice-1-1027/pd/hm_cells_evidence.json > g0_r19.log 2>&1; echo g0 rc=$? >> mp.done
python3 $W/check.py pd/hm_r12.json --out g0c_r19 --completeness --cells-evidence /srv/opentallas-scratch2/claude/kv-core-slice-1-1027/pd/hm_cells_evidence.json > g0c_r19.log 2>&1; echo g0c rc=$? >> mp.done
