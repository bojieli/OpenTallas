#!/usr/bin/env bash
# DIE-S81-51/RF-C/bk 11-03 (SIM=verilator default | iverilog): OLL (output lockup latch) bench of dsdv_bksel_c / dsdv_bksel_q, old form vs re-formed.
#   usage (from the source root): run_bk_oll_bench.sh c|q <out> [mut 0|1] [rtl file]   (exit 0 = expected verdict)
#   c: main RTL dsdv_bksel_c (selc2 sources); q: dsdv_bksel_q in the dsfd_selt_q2 form (RTL file default = main;
#   the rfc_bk_1103 profile copy wraps dsfd_selt_q_hq with the same dsdv_bk_oll wrapper).
set -u
U=$1; OUT=$2; MUT=${3:-0}; F=${4:-rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bksel_c.sv}
mkdir -p "$OUT"
D=""; [ "$U" = q ] && D="-DTB_Q"; [ "$MUT" = 1 ] && D="$D -DOT_BK_OLL_MUT"
M128=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
M256=physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
FILES="rtl/common/ot_fwd_link_stage.sv rtl/hdc/ot_hdc_prefix.sv $M256 $M128  rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv  rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv  rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv  rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv  rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_pp.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv  $F rtl/dsrom_sys/s81_dv/unit/bk/test/tb_dsdv_bk_oll.sv"
if [ "${SIM:-verilator}" = verilator ]; then
  verilator --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style --top-module tb_dsdv_bk_oll ${D//-D/+define+} \
    +define+OT_S81PH_SEL_SAFE +define+OT_S81PH_SEL_FRPR +define+OT_S81PH_SEL_ILD -Mdir "$OUT/obj_$U$MUT" $FILES \
    > "$OUT/build_$U$MUT.log" 2>&1 || { tail -20 "$OUT/build_$U$MUT.log"; exit 2; }
  "$OUT/obj_$U$MUT/Vtb_dsdv_bk_oll" +ncyc=${NCYC:-300} > "$OUT/sim_$U$MUT.log" 2>&1
else
  iverilog -g2012 -o "$OUT/tb_$U$MUT" $D -DOT_S81PH_SEL_SAFE -DOT_S81PH_SEL_FRPR -DOT_S81PH_SEL_ILD $FILES \
    > "$OUT/build_$U$MUT.log" 2>&1 || { tail -20 "$OUT/build_$U$MUT.log"; exit 2; }
  vvp -n "$OUT/tb_$U$MUT" +ncyc=${NCYC:-300} > "$OUT/sim_$U$MUT.log" 2>&1
fi
V=$(grep -m1 "^DSDV_BK_OLL" "$OUT/sim_$U$MUT.log"); echo "$V mut=$MUT"
if [ "$MUT" = 0 ]; then echo "$V" | grep -q " PASS "; else echo "$V" | grep -q " FAIL "; fi
