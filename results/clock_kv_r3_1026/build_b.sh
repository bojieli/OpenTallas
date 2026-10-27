#!/bin/bash
set -e
O=$1; shift
B=/srv/opentallas-scratch2/claude/clock-kv-r1-1026; T=/srv/opentallas-scratch2/claude/wt/clock-kv-r1-1026/tools/die_plan
IN=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026; PL=$B/plan_win.json; K=$IN/kit
export PYTHONPATH=$IN/pylib
echo "start $(date -Is) tools $(git -C $T rev-parse --short HEAD) dirty $(git -C $T diff --stat | tail -1)"
python3 $T/die_clock_mesh.py build $PL --out $O --nx 32 --ny 64 --m 2 --rep-um 450 --ndr 4w --sites any   --reserve-cell-sites --track-file $K/grt/tracks.tcl --trunk-repeaters --split-yfirst --delta-id D-KV-CLK-R3b "$@"
python3 $T/die_clock_mesh.py render $O --plan $PL --out $O/render.png || true
echo "BUILD_DONE $(date -Is)"
