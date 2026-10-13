#!/usr/bin/env bash
# ot_qwen_tile_kvl leaf equivalence bench: run_tb_qwen_tile_kvl.sh OUTDIR [MUT] [SEED]
# MUT 0 prints "PASS <n> cycles ..." (exit 0); MUT 1 (read address one edge late) prints FAIL (exit 1).
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=${1:?outdir}; MUT=${2:-0}; SEED=${3:-7}
mkdir -p "$OUT"
iverilog -g2012 -s tb_qwen_tile_kvl -o "$OUT/tb.vvp" -P tb_qwen_tile_kvl.MUT="$MUT" \
    rtl/test/tb_qwen_tile_kvl.sv rtl/physical/ot_qwen_tile_kvl.sv rtl/hdc/kv/ot_qwen_kv_land_merge.sv \
    rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv \
    physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
vvp -n "$OUT/tb.vvp" +SEED="$SEED" | tee "$OUT/tb.log"
grep -q '^PASS [0-9][0-9]* cycles' "$OUT/tb.log"
