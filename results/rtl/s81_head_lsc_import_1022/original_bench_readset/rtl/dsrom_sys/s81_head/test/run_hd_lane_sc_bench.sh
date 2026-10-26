#!/usr/bin/env bash
# HEAD LANE (b) STACKED 10-22 (STW-S81c-COLLA2-LANE): benches of the stacked lane on Verilator 5.050 (closure daemon
# version).  cwd = repo root / synced src.
# Usage: run_hd_lane_sc_bench.sh OUTDIR VARIANT KIND [MUT]
#   VARIANT  sc6 (MAIN, 6 sub-children) | sc4 (FB, 4 sub-children)
#   KIND     func: tb_s81hd_lane (the existing lane bench: PASS expected without a mutant)
#            eq:   tb_s81hd_lane_eq (cycle-exact vs the current lane ot_s81hd_lane.sv: PASS expected without a mutant)
#   MUT      base | OVF | RP | SKEW   (OVF / RP = the lane bench mutants; SKEW = one sub-child seam lands a cycle late)
# Prints the sim log; exit 0 iff the log says PASS.  J (build jobs) defaults to 2 (S81 Verilator rule J <= mem_cap/30 GB).
set -u; O=${1:?outdir}; VAR=${2:?sc6|sc4}; KIND=${3:?func|eq}; WHAT=${4:-base}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
T=rtl/dsrom_sys/s81_head
LANE="rtl/link/ot_link_crc32.sv rtl/lib/ot_rst_relay_tree3.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv
 rtl/lib/ot_sram_oldread_b64.sv rtl/lib/ot_sram_showahead_b64.sv rtl/common/ot_link_credit_rx_b64.sv
 rtl/common/ot_link_credit_tx_rc.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv
 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv $T/ot_s81hd_util.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1/ot_sram_1r1w2c_256x64_m1.v"
DUT="$T/ot_s81hd_lsc_parts.sv $T/ot_s81hd_lane_$VAR.sv"
D=""
case $WHAT in base) ;; SKEW) D="+define+OT_S81HD_LSC_MUT_SKEW" ;; *) D="+define+OT_S81HD_LANE_MUT_$WHAT" ;; esac
TAG=${VAR}_${KIND}_${WHAT}
if [ "$KIND" = eq ]; then
    # the reference: the current lane, module renamed, its mutant hooks disabled (the mutant only goes into the DUT)
    sed -e 's/module ot_s81hd_lane (/module ot_s81hd_lane_ref (/' -e 's/ot_s81hd_lane_txs/ot_s81hd_lane_txs_ref/g' \
        -e 's/OT_S81HD_LANE_MUT_/OT_S81HD_LANE_REFNOMUT_/g' -e 's/OT_S81HD_LANE_CHK/OT_S81HD_LANE_REFNOCHK/g' \
        $T/ot_s81hd_lane.sv > $O/ot_s81hd_lane_ref.sv
    TB="$O/ot_s81hd_lane_ref.sv $T/test/tb_s81hd_lane_eq.sv"; TOP=tb_s81hd_lane_eq; PAT='^PASS lsc_eq'
else
    TB="$T/test/tb_s81hd_lane.sv"; TOP=tb_s81hd_lane; PAT='^PASS hd_lane'
fi
$V --version | tee $O/verilator_version.txt
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style \
  +define+OT_COLL_NATIVE32 +define+OT_COLL_NATIVE32_OFF +define+OT_S81HD_LANE_CHK $D \
  --top-module $TOP -Mdir $O/obj_$TAG $LANE $DUT $TB --build-jobs ${J:-2} \
  > $O/build_$TAG.log 2>&1 || { echo "BUILD_FAILED $TAG"; grep -m10 %Error $O/build_$TAG.log; exit 2; }
$O/obj_$TAG/V$TOP > $O/$TAG.log 2>&1; cat $O/$TAG.log
grep -q "$PAT" $O/$TAG.log
