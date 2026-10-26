#!/bin/bash
# PATH-KV-R2 clock c3t = c3e + measured per-tap stub trim (die_clock_mesh.py stubtrim, complete tap-level pair
# superset, joint TT+FF LP).  GRT TT/FF (kit signals M4-M7 + mesh clock M8-M9), mesh transient + stub STA + report.
set -e
B=/srv/opentallas-scratch2/claude/path-kv-clk-1026; T=/srv/opentallas-scratch2/claude/wt/path-kv-r2-1026/tools/die_plan
PL=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/plan.json; export PYTHONPATH=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/pylib
MEM=24 bash $B/c3t/run_combo.sh
grep -H EXIT $B/c3t/combo_TT.log $B/c3t/combo_FF.log
bash $T/die_clock_mesh_post.sh $B/c3t $PL
python3 $T/die_clock_mesh.py render $B/c3t --plan $PL --out $B/c3t/c3t.png || true
echo PROTO_DONE
