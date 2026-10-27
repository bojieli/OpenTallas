#!/bin/bash
# KV-CORE-SLICE-1 static plan gates on the plan with the slice applied (out/pd_slice) + baseline (pd), intel1 docker mem cap
set -x
T=/srv/opentallas-scratch2/claude/wt/kv-core-slice-1/tools/die_plan; W=/srv/opentallas-scratch2/claude/kv-core-slice-1-1027; cd $W
python3 $T/check.py out/pd_slice/hm_r12.json --out g0c_slice --completeness --cells-evidence $W/pd/hm_cells_evidence.json --png > g0c_slice.log 2>&1; tail -2 g0c_slice.log
python3 $T/check.py pd/hm_r12.json --out g0c_base --completeness --cells-evidence $W/pd/hm_cells_evidence.json > g0c_base.log 2>&1; tail -2 g0c_base.log
python3 $T/check.py out/pd_slice/hm_r12.json --out g0_slice --cells-evidence $W/pd/hm_cells_evidence.json > g0_slice.log 2>&1; tail -2 g0_slice.log
echo GATES_DONE $(date -Is)
