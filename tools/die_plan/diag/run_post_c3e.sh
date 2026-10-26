#!/bin/bash
set -e
PYTHONPATH=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/pylib bash /srv/opentallas-scratch2/claude/wt/path-kv-clk-1026/tools/die_plan/die_clock_mesh_post.sh /srv/opentallas-scratch2/claude/path-kv-clk-1026/c3e /srv/opentallas-scratch2/claude/codex-kv-mesh-1026/plan.json
PYTHONPATH=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/pylib python3 /srv/opentallas-scratch2/claude/wt/path-kv-clk-1026/tools/die_plan/die_clock_mesh.py render /srv/opentallas-scratch2/claude/path-kv-clk-1026/c3e --plan /srv/opentallas-scratch2/claude/codex-kv-mesh-1026/plan.json --out /srv/opentallas-scratch2/claude/path-kv-clk-1026/c3e/c3e.png || true
echo PROTO_DONE
