#!/bin/bash
set -euo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
export VERILATOR="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
export PATH="$(dirname "$VERILATOR"):$PATH"
"$VERILATOR" --version
"$VERILATOR" --binary --timing -j 4 -O3 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_kfirst_predicate -Mdir "$OUT/predicate_obj" tools/qwen_romleaf/rc16_2000/tb_kfirst_predicate.sv rtl/physical/a0_rc16_selected_2000/ot_qwen_w12_matvec_land32.sv > "$OUT/predicate_build.log" 2>&1
"$OUT/predicate_obj/Vtb_kfirst_predicate" > "$OUT/predicate_PASS.log" 2>&1
grep '^KFIRST_PREDICATE_PASS ' "$OUT/predicate_PASS.log"
