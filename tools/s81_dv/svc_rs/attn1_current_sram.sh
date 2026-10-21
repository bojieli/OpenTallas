#!/usr/bin/env bash
set -euo pipefail
O=${1:?out}; mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
V=rtl/hdc/v41x; H=rtl/hdc
SRC="tools/s81_dv/svc_rs/tb_attn1_current_sram.sv $V/ot_hdc_v41x_attn_s.sv $V/ot_hdc_v41x_attn_tile_s.sv $V/ot_hdc_v41x_kreg.sv \
 $V/ot_hdc_v41x_attn_tile_lat.sv $V/ot_hdc_v41x_attn_tile.sv $V/ot_hdc_v41x_attn.sv $V/ot_hdc_v41x_attn_staging.sv \
 $H/ot_hdc_fastfp.sv $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_prefix.sv $H/ot_hdc_fp32_f12.sv \
 $V/ot_dsrom_su_add6.sv $H/ot_hdc_delay.sv $H/ot_hdc_fastfp_lat_f12.sv $H/ot_hdc_fp32_mul_lat.sv results/rtl/s81_nt1_static_1021/current_sram/canonical_ref.sv results/rtl/s81_nt1_static_1021/current_sram/candidate.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
sha256sum $SRC > "$O/sources.sha256"
"$VL" --version > "$O/verilator.version"
"$VL" -DOT_SVC_LAND_SRAM -DOT_SVC_ATT_SRAM --binary --timing -j 8 -Wno-fatal --unroll-count 64 -CFLAGS -O1 --top-module tb_attn1_current_att -Mdir "$O/obj" -o sim $SRC > "$O/build.log" 2>&1
for t in 1 33 46; do "$O/obj/sim" +t=$t > "$O/t$t.log" 2>&1; grep CURRENT_ATT "$O/t$t.log"; done
