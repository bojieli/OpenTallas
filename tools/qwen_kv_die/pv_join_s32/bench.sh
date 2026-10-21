#!/usr/bin/env bash
# KV-PARAMS4: pv_join_s32 vs ot_qwen_tp8_pv_join_t (RESET_PIN 1; ref reset delayed 2 edges = the +2 boot release edges).
#   bench.sh OUT MUT [DEF]   MUT 0 expect PASS; MUT 1 operand swap / 2 unreset yr / DEF=-DPVJ32_MUT3 expect FAIL
set -euo pipefail
R=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=${1:?out};MUT=${2:-0};DEF=${3:-}
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
mkdir -p "$OUT"
verilator --version
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-initial unique --x-assign unique $DEF \
 --top-module tb_pv_join_s32 -GMUT="$MUT" -GCOLD=1 -GRP=1 -Mdir "$OUT/obj" \
 "$R/rtl/test/qwen_kv_die/tb_pv_join_s32.sv" "$R/rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv" \
 "$R/rtl/hdc/nearhbm/ot_qwen_tp8_pv_join_s32_t.sv" "$R/rtl/lib/ot_rst_relay_bounded32.sv" "$R/rtl/hdc/ot_hdc_fp32_qkh_ncr.sv" \
 "$R/rtl/hdc/ot_hdc_fp32_add_lat.sv" "$R/rtl/hdc/ot_hdc_fp32_add_lat_nr.sv" "$R/rtl/hdc/ot_hdc_prefix.sv" "$R/rtl/hdc/ot_hdc_delay.sv" \
 "$R/physical/ref_tile/ot_qkh_ktree_m5/src/rtl/hdc/ot_hdc_fastfp.sv" > "$OUT/build.log" 2>&1 || { tail -30 "$OUT/build.log"; exit 2; }
for seed in 331 905 173; do
 "$OUT/obj/Vtb_pv_join_s32" +verilator+rand+reset+2 +verilator+seed+$seed > "$OUT/verdict_$seed.log"
 cat "$OUT/verdict_$seed.log"
 grep -q '^PV_JOIN_S32 PASS' "$OUT/verdict_$seed.log" || exit 1
done
