#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "$1"); MUT=${2:-0}; mkdir -p "$OUT"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --version
P=rtl/hbm_accel/generic/collective/p2p
sed 's/ot_hbm_xp_aq_tree13 #(.MUT(MUT))/ot_hgi_coll_aq13 #(.LMUT(MUT))/' physical/hbm_xp_aq_tree13_1014/tb_aq_tree13.sv > "$OUT/tb.sv"
verilator --binary --timing -j 4 -DOT_COLLQ_SRAM -GMUT="$MUT" -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb --Mdir "$OUT/obj" "$OUT/tb.sv" \
 "$P/ot_hgi_coll_aq13.sv" "$P/ot_hgi_coll_aq_scale13r.sv" rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/ot_hdc_fpu.sv \
 rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_hc.sv rtl/hdc/ot_hdc_cg.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb" | tee "$OUT/run.log"
