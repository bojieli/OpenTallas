#!/bin/bash
# PATH-KV clock prototype c3 (branch claude/path-kv-clk-1026): 8 partition-aligned regional meshes, PG-free straps.
# GRT TT/FF (kit signals M4-M7 + mesh clock M8-M9), then mesh transient + stub STA + related-pair report + render.
set -e
MEM=24 bash /srv/opentallas-scratch2/claude/path-kv-clk-1026/c3c/run_combo.sh
grep -H EXIT /srv/opentallas-scratch2/claude/path-kv-clk-1026/c3c/combo_TT.log /srv/opentallas-scratch2/claude/path-kv-clk-1026/c3c/combo_FF.log
PYTHONPATH=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/pylib bash /srv/opentallas-scratch2/claude/wt/path-kv-clk-1026/tools/die_plan/die_clock_mesh_post.sh /srv/opentallas-scratch2/claude/path-kv-clk-1026/c3c /srv/opentallas-scratch2/claude/codex-kv-mesh-1026/plan.json
PYTHONPATH=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/pylib python3 /srv/opentallas-scratch2/claude/wt/path-kv-clk-1026/tools/die_plan/die_clock_mesh.py render /srv/opentallas-scratch2/claude/path-kv-clk-1026/c3c --plan /srv/opentallas-scratch2/claude/codex-kv-mesh-1026/plan.json --out /srv/opentallas-scratch2/claude/path-kv-clk-1026/c3c/c3c.png || true
echo PROTO_DONE
