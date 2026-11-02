#!/bin/bash
# New geometry only. Dispatch after independent ROOT/parent image concurrence; ot-run the caller normally.
set -euo pipefail
R=$1;P=$2;I=$3;O=$4
[ ! -e "$O" ] || { echo 'Refuse to overwrite a geometry successor';exit 3; }
[ -f "$I/prep_receipt.json" ]
cd "$R"
python3 physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py \
 --core-json "$P/core.json" --plan "$I/plan.json" --out "$O" --kit-rtl "$P/kit_rtl" \
 --util 0.6 --sigmax M5 --tool "$R/tools/die_plan" --plan-inst kvs_ctl --lec-hints "$P/hint_plan.json"
# Source/defines/SDC/library equality to the retained subject and genuine stage1 reuse are a separate mandatory join.
# No SYNTH/LEC/floorplan/PLACE is invoked by this script.
