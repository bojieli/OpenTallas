#!/usr/bin/env bash
# SVCATT: Codex current ATT T1/T33/T46 fixture (fmem_n32/tb_att_fmem.sv) with a chosen opt-in define set.
# usage (repo root): run_att_all.sh OUT "DEFINES"
set -euo pipefail
O=${1:?out}; DEFS=${2:?defines}; mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
V=rtl/hdc/v41x; H=rtl/hdc; D=rtl/dsrom_sys/s81_dv/svc_rs
SRC="tools/s81_dv/svc_rs/fmem_n32/tb_att_fmem.sv $V/ot_hdc_v41x_attn_s.sv $V/ot_hdc_v41x_attn_tile_s.sv $V/ot_hdc_v41x_kreg.sv \
 $V/ot_hdc_v41x_attn_tile_lat.sv $V/ot_hdc_v41x_attn_tile.sv $V/ot_hdc_v41x_attn.sv $V/ot_hdc_v41x_attn_staging.sv \
 $H/ot_hdc_fastfp.sv $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_prefix.sv $H/ot_hdc_fp32_f12.sv \
 $V/ot_dsrom_su_add6.sv $H/ot_hdc_delay.sv $H/ot_hdc_fastfp_lat_f12.sv $H/ot_hdc_fp32_mul_lat.sv tools/s81_dv/svc_rs/merge_sram/att_canonical_ref.sv $D/dsdv_svc_att.sv $V/ot_hdc_v41x_merge_ring_sram.sv $V/ot_hdc_v41x_attn_tr_sram.sv \
 $V/ot_hdc_v41x_stagepick_n32.sv $D/dsdv_svc_smj_payload_n32.sv $D/dsdv_svc_pword_pick_n32.sv $D/dsdv_svc_offset144_n32.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
sha256sum $SRC > "$O/sources.sha256"; echo "$DEFS" > "$O/defines.txt"
"$VL" --version > "$O/verilator.version"
"$VL" $DEFS -I$D --binary --timing -j 4 -Wno-fatal --unroll-count 64 -CFLAGS -O1 --top-module tb_attn1_current_att -Mdir "$O/obj" -o sim $SRC > "$O/build.log" 2>&1 || { tail -20 "$O/build.log"; echo ATT_BUILD_FAIL; exit 2; }
for t in 1 33 46; do "$O/obj/sim" +t=$t > "$O/t$t.log" 2>&1; grep CURRENT_ATT "$O/t$t.log"; done
