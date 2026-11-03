#!/usr/bin/env bash
# DIE-S81-51/RF-D 11-03: run_bksel_c_rnf.sh <out> [mut 0|1] [seed]  (from the source root; exit 0 = expected verdict)
set -u
OUT=$1; MUT=${2:-0}; SEED=${3:-1}; mkdir -p "$OUT"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ "$MUT" = 1 ] && D="+define+OT_RFD_MUT_RNF"
M128=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
M256=physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
FILES="rtl/common/ot_fwd_link_stage.sv rtl/hdc/ot_hdc_prefix.sv $M256 $M128 rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_pp.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bksel_c.sv rtl/dsrom_sys/s81_dv/unit/bk/test/tb_dsdv_bksel_c_rnf.sv"
$V --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style $D +define+OT_S81PH_SEL_SAFE +define+OT_S81PH_SEL_FRPR +define+OT_S81PH_SEL_ILD \
  --top-module tb_dsdv_bksel_c_rnf -Mdir "$OUT/obj$MUT" $FILES > "$OUT/build$MUT.log" 2>&1 || { echo "BKSELC_RNF FAIL build"; tail -8 "$OUT/build$MUT.log"; exit 2; }
"$OUT/obj$MUT/Vtb_dsdv_bksel_c_rnf" +seed=$SEED +ncyc=${NCYC:-2000} > "$OUT/run$MUT.log" 2>&1
R=$(grep -m1 "^BKSELC_RNF" "$OUT/run$MUT.log"); echo "$R mut=$MUT seed=$SEED"; grep -m3 MISMATCH "$OUT/run$MUT.log"
if [ "$MUT" = 0 ]; then echo "$R" | grep -q " PASS "; else echo "$R" | grep -q " FAIL "; fi
