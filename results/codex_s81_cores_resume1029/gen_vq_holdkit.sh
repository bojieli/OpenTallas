#!/bin/bash
set -euo pipefail
repo=$1; out=$2; slices=$3
python3 "$repo/physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py" --module ot_s81sl_vq --recipes "$repo/results/codex_s81_cores_resume1029/vq_hold_recipe.json" --out "$out" --suffix hold1029b --master-slice "$slices" --trial
cp "$repo/results/codex_s81_cores_resume1029/vq_hold_after_grt.tcl" "$out/ot_s81sl_vq_hold1029b/vq_hold_after_grt.tcl"
