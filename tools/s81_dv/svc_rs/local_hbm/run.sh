#!/usr/bin/env bash
set -euo pipefail
O=${1:?out}; mkdir -p "$O"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
V=rtl/hdc/v41x; H=rtl/hdc
SRC="tools/s81_dv/svc_rs/local_hbm/tb_local_hbm.sv $V/ot_hdc_v41x_attn_s.sv $V/ot_hdc_v41x_attn_tile_s.sv $V/ot_hdc_v41x_kreg.sv \
 $V/ot_hdc_v41x_attn_tile_lat.sv $V/ot_hdc_v41x_attn_tile.sv $V/ot_hdc_v41x_attn.sv $V/ot_hdc_v41x_attn_staging.sv \
 $H/ot_hdc_fastfp.sv $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_prefix.sv $H/ot_hdc_fp32_f12.sv \
 $V/ot_dsrom_su_add6.sv $H/ot_hdc_delay.sv $H/ot_hdc_fastfp_lat_f12.sv $H/ot_hdc_fp32_mul_lat.sv tools/s81_dv/svc_rs/merge_sram/att_canonical_ref.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv $V/ot_hdc_v41x_merge_ring_sram.sv $V/ot_hdc_v41x_attn_tr_sram.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v"
SRC="$SRC rtl/hdc/v41x/ot_hdc_v41x_stagepick_n32.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_smj_payload_n32.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_pword_pick_n32.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_offset144_n32.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs_glue.sv rtl/dsrom_sys/s81_dv/svc_rs/ot_s81svc_reset9_n32.sv rtl/dsrom_sys/s81_dv/svc_rs/ot_s81svc_reset132_n32.sv rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att_reset9.sv"
sha256sum $SRC > "$O/sources.sha256"
"$VL" --version > "$O/verilator.version"
"$VL" -DOT_SVC_STAGESEL_N32 -DOT_SVC_SMJ_N32 -DOT_SVC_TAG_N32 -DOT_SVC_ATT_PINREG -DOT_SVC_PSEL_N32 -Irtl/dsrom_sys/s81_dv/svc_rs -DOT_SVC_FMEM_N32 -DOT_SVC_MERGE_SRAM -DOT_SVC_TR_SRAM -DOT_SVC_LAND_SRAM -DOT_SVC_ATT_SRAM -DOT_FP_DATA_NORST --binary --timing -j 4 -Wno-fatal --unroll-count 64 -CFLAGS -O1 --top-module tb_attn1_current_att -Mdir "$O/obj" -o sim $SRC > "$O/build.log" 2>&1
for t in 1 33 46; do "$O/obj/sim" +t=$t > "$O/t$t.log" 2>&1; grep CURRENT_ATT "$O/t$t.log"; done
