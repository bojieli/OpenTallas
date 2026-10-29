#!/bin/bash
set -euo pipefail
B=/srv/opentallas-scratch2/claude/codex-qc-mesh5-1029
P=/srv/opentallas-scratch2/claude/codex-qc-physical-1029
Q=/srv/opentallas-scratch2/claude/codex-qc-1029/baseline26
A=/srv/opentallas-scratch2/claude/codex-qc-pg-access-1029
python3 "$B/src/results/qc_clock_physical_1029/jog_backbones.py" --joint-clock --failures "$P/prebuild26_columns/base_feasibility.json" --fixed-wires "$P/prebuild26_context/fixed_wires.json" --cell-windows "$Q/islands119_cellmap/cell_windows.json" --geometry "$A/census119/geometry.json" --power-access "$A/access119_minarea/reserved_access.json" --pg "$P/inputs/pg_rects.json" --clock-base "$P/inputs/clock_base_access26_minarea.json" --out "$B/joint_seed"
