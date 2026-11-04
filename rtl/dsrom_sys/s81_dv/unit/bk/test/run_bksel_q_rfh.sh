#!/usr/bin/env bash
# DIE-S81-51/RF-H 11-03: run_bksel_q_rfh.sh <out> [mut none|face|sel|zchk|zfold] [seed]  (from the source root; exit 0 = expected verdict)
# zchk = the OT_S81PH_PACK_Z0FOLD sim check on a non-constant bit (must fire); zfold = yosys SAT proof, in the flow image, that the bit
# OT_S81PH_PACK_Z0FOLD ties is constant in the pack WITHOUT the define (lane 0 z MSB after group 0), with a non-constant control bit.
set -u
OUT=$1; MUT=${2:-none}; SEED=${3:-1}; mkdir -p "$OUT"
if [ "$MUT" = zfold ]; then
  F=rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv; rc=0
  for PW in 6 7; do for chk in "$((PW+3)) prove" "$PW control"; do set -- $chk
    cat > "$OUT/zfold_${PW}_$2.ys" <<YS
read_verilog -sv -DOT_S81PH_SEL_HQ -DOT_S81PH_SEL_FAN32 -DOT_S81PH_SEL_ACC32 /src/$F
hierarchy -top ot_s81ph_native_sel_pack -chparam W 16 -chparam PW $PW
proc; flatten; async2sync; opt_clean
sat -set-init-undef -set-def-inputs -seq 8 -prove-skip 5 -prove g_cst[0].q[$1] 0 -verify
YS
    docker run --rm --memory=8g -v "$PWD":/src -v "$(cd "$OUT"; pwd)":/o -w /o openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -q -l /o/zfold_${PW}_$2.log /o/zfold_${PW}_$2.ys" > /dev/null 2>&1; r=$?
    v=$(grep -m1 -E "SUCCESS!|FAIL!" "$OUT/zfold_${PW}_$2.log"); echo "ZFOLD PW=$PW bit=$1 $2 rc=$r ${v}"
    if [ "$2" = prove ]; then [ $r = 0 ] && echo "$v" | grep -q SUCCESS || rc=1; else [ $r != 0 ] && echo "$v" | grep -q FAIL || rc=1; fi
  done; done
  echo "BKSELQ_RFH ZFOLD $([ $rc = 0 ] && echo PASS || echo FAIL)"; exit $rc
fi
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""; [ -n "${OT_RFH_B2:-}" ] && D="+define+OT_RFH_B2"; [ "$MUT" = p2 ] && D="$D +define+OT_RFH_MUT_P2"; [ "$MUT" = face ] && D="$D +define+OT_RFH_MUT_FACE"; [ "$MUT" = sel ] && D="$D +define+OT_RFH_MUT_SEL"; [ "$MUT" = zchk ] && D="$D +define+OT_RFH_MUT_ZCHK"
P=physical/die_plan/s81/cores/legacy/profiles
MM=physical/asap7_memory_macros
FILES="rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv rtl/hdc/ot_hdc_prefix.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel.sv rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv rtl/hdc/v41x/ot_hdc_v41x_sel.sv rtl/common/ot_fwd_link_stage.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_half.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_ctl_pp.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv rtl/lib/ot_rst_relay.sv $P/rfc_bk_1103/rtl/ot_s81ph_native_sel_hist_bank.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_hist_bank.sv $P/rfc_bk_1103/rtl/ot_s81ph_hq_parts.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_hq_slice.sv $P/rfh_bk_1103/rtl/ot_s81ph_hq_tile.sv $P/rfh_bk_1103/rtl/dsdv_bksel_c.sv rtl/lib/ot_sram_showahead_1r1w.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_queue_store.sv $MM/ot_sram_1r1w_128x256_m1_r2c2_p192_mir/ot_sram_1r1w_128x256_m1_r2c2_p192_mir.v $MM/ot_sram_1r1w_32x128_m1_p192_rc/ot_sram_1r1w_32x128_m1_p192_rc.v rtl/dsrom_sys/s81_dv/unit/bk/test/tb_dsdv_bksel_q_rfh.sv"
DEFS="+define+OT_S81PH_SEL_INDEXED13 +define+OT_S81PH_FIFO_SRAM +define+OT_SRAM_P192 +define+OT_S81PH_SEL_SUCC +define+OT_S81PH_SEL_FAN32 +define+OT_S81PH_SEL_ACC32 +define+OT_S81PH_SEL_HQ +define+OT_HARD_CHILDREN +define+OT_S81PH_HQ_INPUT_RAW +define+OT_HB_PINCOPY +define+OT_S81PH_PACK_Z0FOLD"
$V --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style --x-initial 0 $D $DEFS \
  --top-module tb_dsdv_bksel_q_rfh -Mdir "$OUT/obj_$MUT" $FILES > "$OUT/build_$MUT.log" 2>&1 || { echo "BKSELQ_RFH FAIL build"; tail -8 "$OUT/build_$MUT.log"; exit 2; }
"$OUT/obj_$MUT/Vtb_dsdv_bksel_q_rfh" +seed=$SEED +ncyc=${NCYC:-4000} > "$OUT/run_$MUT.log" 2>&1
R=$(grep -m1 "^BKSELQ_RFH" "$OUT/run_$MUT.log"); echo "$R mut=$MUT seed=$SEED"; grep -m3 MISMATCH "$OUT/run_$MUT.log"
if [ "$MUT" = zchk ]; then grep -m1 "OT_RFH_MUT_ZCHK fired" "$OUT/run_$MUT.log"; exit $?; fi
if [ "$MUT" = none ]; then echo "$R" | grep -q " PASS "; else echo "$R" | grep -q " FAIL "; fi
