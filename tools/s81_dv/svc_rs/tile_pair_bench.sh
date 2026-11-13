#!/usr/bin/env bash
# HARD-S81-SVC-1 (11-13): H8 RT2 tile as built vs the per-core-pair reset / load form (tb_s81c_tile_pair), seeds 1 2 3.
# Usage (repo root): tools/s81_dv/svc_rs/tile_pair_bench.sh OUTDIR
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1
mkdir -p "$O"
if [ ! -x "$O/obj/Vtb_s81c_tile_pair" ]; then
  "$VL" -DOT_SVC_H8 -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED --binary --top-module tb_s81c_tile_pair -Mdir "$O/obj" -j 4 --output-split 20000 --output-split-cfuncs 2000 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -fno-inline --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O0 \
    rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv \
    rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv \
    rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv \
    physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v \
    rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv \
    rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/v41x/ot_s81c_attn_hcore.sv rtl/hdc/v41x/ot_s81c_attn_hcore_h8.sv rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv \
    rtl/hdc/v41x/test/tb_s81c_tile_pair.sv > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 1; }
fi
for s in 1 2 3;do
 "$O/obj/Vtb_s81c_tile_pair" +seed=$s > "$O/seed$s.log" 2>&1
 grep '^TILE_PAIR' "$O/seed$s.log"
 grep -q '^TILE_PAIR PASS$' "$O/seed$s.log"
done
