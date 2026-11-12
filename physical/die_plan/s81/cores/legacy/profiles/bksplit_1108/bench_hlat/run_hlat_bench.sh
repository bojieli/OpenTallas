#!/usr/bin/env bash
# S81-ARCH-RTL-2 11-12: HLAT bench (verilator 5.050).  usage: run_hlat_bench.sh <kit_rtl_dir> <profile_rtl_dir> <out> [mut 0|1]
# kit_rtl_dir = the bksel kit rtl/ copy (unchanged support files); profile_rtl_dir = profiles/bksplit_1108/rtl (the three
# edited files + the real pk2); SRAM behavioural models from physical/asap7_memory_macros (cwd = repo root).
set -u
K=$1; P=$2; OUT=$3; MUT=${4:-0}; mkdir -p "$OUT"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D="+define+OT_S81PH_SEL_INDEXED13 +define+OT_S81PH_FIFO_SRAM +define+OT_SRAM_P192 +define+OT_S81PH_SEL_SUCC +define+OT_S81PH_SEL_FAN32 +define+OT_S81PH_SEL_ACC32 +define+OT_S81PH_SEL_HQ +define+OT_S81PH_HQ_INPUT_RAW +define+OT_HB_PINCOPY +define+OT_S81PH_PACK_Z0FOLD +define+OT_BKQ_RCP=16 +define+OT_BKQ_GBREG +define+OT_BKQ_GBREG2 +define+OT_BKQ_BSTG +define+OT_BKQ_FO8 +define+OT_BKQ_ORT +define+OT_BKQ_SPLIT"
[ "$MUT" = 1 ] && D="$D +define+OT_S81PH_HLK_MUT"
F=""
for f in ot_s81ph_sel_pipeline.sv ot_hdc_prefix.sv ot_s81ph_sel.sv ot_hdc_v41x_sel_lib.sv ot_hdc_v41x_sel_slice.sv ot_hdc_v41x_sel.sv ot_fwd_link_stage.sv ot_s81ph_native_sel.sv ot_s81ph_native_sel_lib.sv ot_s81ph_native_sel_slice.sv ot_s81ph_sel_ctl_half.sv ot_s81ph_sel_ctl_pp.sv ot_s81ph_sel_tile.sv ot_rst_relay.sv ot_sram_showahead_1r1w.sv ot_s81ph_queue_store.sv; do F="$F $K/$f"; done
F="$F rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_hist_bank.sv $P/ot_s81ph_hq_parts.sv $P/ot_s81ph_hq_slice.sv $P/ot_s81ph_hq_tile.sv $P/dsdv_bksel_c.sv $P/ot_s81ph_hq_pk2.sv"
F="$F physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir.v physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192_rc/ot_sram_1r1w_32x128_m1_p192_rc.v"
F="$F $(dirname $0)/tb_dsdv_bksel_hlat.sv"
$V --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style --top-module tb_dsdv_bksel_hlat $D -Mdir "$OUT/obj$MUT" $F \
  > "$OUT/build$MUT.log" 2>&1 || { tail -20 "$OUT/build$MUT.log"; exit 2; }
"$OUT/obj$MUT/Vtb_dsdv_bksel_hlat" +ncyc=${NCYC:-400} > "$OUT/sim$MUT.log" 2>&1
R=$(grep -m1 "^DSDV_BKSEL_HLAT" "$OUT/sim$MUT.log"); echo "$R mut=$MUT"
if [ "$MUT" = 0 ]; then echo "$R" | grep -q " PASS "; else echo "$R" | grep -q " FAIL "; fi
