#!/bin/bash
set -euo pipefail
WT=/srv/opentallas-scratch2/claude/wt/codex-s81-pd2-2000
O=/srv/opentallas-scratch2/claude/codex-s81-pd2-2000
SRC=/srv/opentallas-scratch2/claude/path-s81-taps-1026/src/physical/die_plan/s81
for d in "$SRC"/*; do b=$(basename "$d"); case "$b" in die_plan*.json) ;; *) ln -sfn "$d" "$O/plandir/$b";; esac; done
cd "$WT"
python3 results/fallback_s81_1026/compose_plan.py "$SRC/die_plan_phyfit_g0fix.json" "$O/regions/landed_crossings.json" "$O/plandir/die_plan_pd2.json" "$O/side_pd2.json" > "$O/compose_pd2.log" 2>&1
python3 tools/die_plan/gen.py latency "$O/plandir/die_plan_pd2.json" --inplace --out "$O/gen_lat_pd2" > "$O/gen_lat_pd2.log" 2>&1
python3 tools/die_plan/check.py "$O/plandir/die_plan_pd2.json" --out "$O/g0_pd2" > "$O/g0_pd2.log" 2>&1 || true
