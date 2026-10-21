#!/usr/bin/env bash
# HD-CTLGATE 10-21: ot_s81hd_lane bench on Verilator 5.050 (closure daemon version).  cwd = repo root / synced src.
#   base  tb_s81hd_lane (PASS expected)
#   OVF   +define+OT_S81HD_LANE_MUT_OVF (static overflow never flagged)  -> FAIL expected
#   RP    +define+OT_S81HD_LANE_MUT_RP  (TX read pointer sticks)        -> FAIL expected
# Usage: run_hd_lane_bench.sh OUTDIR [base|OVF|RP]   (prints the sim log; exit 0 iff the log says PASS hd_lane)
set -u; O=${1:?outdir}; WHAT=${2:-base}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
T=rtl/dsrom_sys/s81_head
SRCS="rtl/link/ot_link_crc32.sv rtl/lib/ot_rst_relay_tree3.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv
 rtl/lib/ot_sram_oldread_b64.sv rtl/lib/ot_sram_showahead_b64.sv rtl/common/ot_link_credit_rx_b64.sv
 rtl/common/ot_link_credit_tx_rc.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv $T/ot_s81hd_util.sv $T/ot_s81hd_lane.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1/ot_sram_1r1w2c_256x64_m1.v"
D=""; [ "$WHAT" = base ] || D="+define+OT_S81HD_LANE_MUT_$WHAT"
$V --version | tee $O/verilator_version.txt
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style \
  +define+OT_COLL_NATIVE32 +define+OT_COLL_NATIVE32_OFF +define+OT_S81HD_LANE_CHK $D \
  --top-module tb_s81hd_lane -Mdir $O/obj_$WHAT $SRCS $T/test/tb_s81hd_lane.sv --build-jobs ${J:-8} \
  > $O/build_$WHAT.log 2>&1 || { echo "BUILD_FAILED $WHAT"; grep -m10 %Error $O/build_$WHAT.log; exit 2; }
$O/obj_$WHAT/Vtb_s81hd_lane > $O/$WHAT.log 2>&1; cat $O/$WHAT.log
grep -q '^PASS hd_lane' $O/$WHAT.log
