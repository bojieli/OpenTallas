#!/usr/bin/env bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=${1:?out};MUT=${2:-0};COLD=${3:-1}; RP=${4:-0}
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p "$OUT"
verilator --version
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-initial unique --x-assign unique \
 --top-module tb_pv_join_cold -GMUT="$MUT" -GCOLD="$COLD" -GRP="$RP" -Mdir "$OUT/obj" \
 "$R/rtl/test/qwen_kv_die/tb_pv_join_cold.sv" "$R/rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv" \
 "$R/rtl/hdc/nearhbm/ot_qwen_tp8_pv_join_cold_t.sv" "$R/rtl/hdc/ot_hdc_fp32_add_lat.sv" \
 "$R/rtl/hdc/ot_hdc_prefix.sv" "$R/rtl/hdc/ot_hdc_delay.sv" \
 "$R/physical/ref_tile/ot_qkh_ktree_m5/src/rtl/hdc/ot_hdc_fastfp.sv" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_pv_join_cold" +verilator+rand+reset+2 +verilator+seed+331 > "$OUT/verdict.log"
cat "$OUT/verdict.log"
grep -q '^PV_JOIN_COLD PASS' "$OUT/verdict.log"
