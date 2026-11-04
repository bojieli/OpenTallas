#!/usr/bin/env bash
# DIE-S81-51/RF-H 11-03: run_bksel_q_rfh.sh <out> [mut none|face|sel] [seed]  (from the source root; exit 0 = expected verdict)
set -u
OUT=$1; MUT=${2:-none}; SEED=${3:-1}; mkdir -p "$OUT"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ "$MUT" = face ] && D="+define+OT_RFH_MUT_FACE"; [ "$MUT" = sel ] && D="+define+OT_RFH_MUT_SEL"
P=physical/die_plan/s81/cores/legacy/profiles
MM=physical/asap7_memory_macros
FILES="rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv rtl/hdc/ot_hdc_prefix.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv rtl/common/ot_fwd_link_stage.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_pp.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv rtl/lib/ot_rst_relay.sv $P/rfc_bk_1103/rtl/ot_s81ph_native_sel_hist_bank.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_hist_bank.sv $P/rfc_bk_1103/rtl/ot_s81ph_hq_parts.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_hq_slice.sv $P/rfh_bk_1103/rtl/ot_s81ph_hq_tile.sv $P/rfh_bk_1103/rtl/dsdv_bksel_c.sv rtl/lib/ot_sram_showahead_1r1w.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_queue_store.sv $MM/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir.v $MM/ot_sram_1r1w_32x128_m1_p192_rc/ot_sram_1r1w_32x128_m1_p192_rc.v rtl/dsrom_sys/s81_dv/unit/bk/test/tb_dsdv_bksel_q_rfh.sv"
DEFS="+define+OT_S81PH_SEL_INDEXED13 +define+OT_S81PH_FIFO_SRAM +define+OT_SRAM_P192 +define+OT_S81PH_SEL_SUCC +define+OT_S81PH_SEL_FAN32 +define+OT_S81PH_SEL_ACC32 +define+OT_S81PH_SEL_HQ +define+OT_HARD_CHILDREN +define+OT_S81PH_HQ_INPUT_RAW +define+OT_HB_PINCOPY"
$V --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style --x-initial 0 $D $DEFS \
  --top-module tb_dsdv_bksel_q_rfh -Mdir "$OUT/obj_$MUT" $FILES > "$OUT/build_$MUT.log" 2>&1 || { echo "BKSELQ_RFH FAIL build"; tail -8 "$OUT/build_$MUT.log"; exit 2; }
"$OUT/obj_$MUT/Vtb_dsdv_bksel_q_rfh" +seed=$SEED +ncyc=${NCYC:-4000} > "$OUT/run_$MUT.log" 2>&1
R=$(grep -m1 "^BKSELQ_RFH" "$OUT/run_$MUT.log"); echo "$R mut=$MUT seed=$SEED"; grep -m3 MISMATCH "$OUT/run_$MUT.log"
if [ "$MUT" = none ]; then echo "$R" | grep -q " PASS "; else echo "$R" | grep -q " FAIL "; fi
