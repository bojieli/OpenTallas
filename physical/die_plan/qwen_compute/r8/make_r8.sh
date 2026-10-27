#!/usr/bin/env bash
# QC-P6-XT1 10-23: the plan's R8 data from a bind of THIS plan (recipe bind/asbuilt_xt1.json):
#   r8/bus_groups.json            = BIND_DIR/bus_groups.json (as-built bus groups bound on this plan)
#   r8/qwen_compute_r8_landing.json + r8/qwen_compute_latency.json + r8/qwen_compute_lat_pkg.sv (gen.py latency --groups)
# Plan, bound top (bind.py land_align r8) and compiler (regen_constants) read this one table; the CB16 reduction-tree
# alignment pads (bind/qc_tree_pads.json, bind/qc_tree_pads.py) ride on top of it as asbuilt.land_r8_extra.
#   bash physical/die_plan/qwen_compute/r8/make_r8.sh BIND_DIR
set -euo pipefail
D=$(cd "$(dirname "$0")/.." && pwd); R=$(cd "$D/../../.." && pwd); B=$1
cp "$B/bus_groups.json" "$D/r8/bus_groups.json"
python3 "$R/tools/die_plan/gen.py" latency "$D/die_plan.json" --out "$D/r8" --groups "$D/r8/bus_groups.json"
