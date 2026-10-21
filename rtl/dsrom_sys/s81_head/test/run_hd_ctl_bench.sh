#!/usr/bin/env bash
# HD-CTL 10-21: ot_s81hd_ctl smoke bench on Verilator 5.050 (closure daemon version).  cwd = repo root / synced src.
#   base  tb_s81hd_ctl (PASS expected)
#   mut   OT_S81HD_CTL_MUT_SLICE (xa word select wrong) / OT_S81HD_CMP_MUT_TIE (highest id on ties): each must FAIL
# Usage: run_hd_ctl_bench.sh OUTDIR [base|mut|all]
set -u; O=${1:?outdir}; WHAT=${2:-all}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
T=rtl/dsrom_sys/s81_head
SRCS="rtl/lib/ot_rst_relay_tree3.sv $T/ot_s81hd_util.sv $T/ot_s81hd_ctl.sv rtl/dsrom_sys/mtp/dsfd_mtp_tops.sv
 rtl/dsrom_sys/mtp/ot_dsrom_mtp_seq.sv rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
bad=0
build() { n=$1; shift
  $V --version > $O/verilator_version.txt
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style "$@" \
    --top-module tb_s81hd_ctl -Mdir $O/$n $SRCS $T/test/tb_s81hd_ctl.sv --build-jobs ${J:-8} \
    > $O/build_$n.log 2>&1 || { echo "BUILD_FAILED $n"; grep -m10 %Error $O/build_$n.log; return 2; }
}
run() { n=$1; exp=$2
  $O/$n/Vtb_s81hd_ctl > $O/$n.log 2>&1; v=$(grep -m1 -E "^(PASS|FAIL) hd_ctl" $O/$n.log); echo "$n: $v"
  case $exp in PASS) echo "$v" | grep -q '^PASS hd_ctl' || bad=1 ;; FAIL) echo "$v" | grep -q '^FAIL hd_ctl' || { echo "  $n NOT detected"; bad=1; } ;; esac
}
if [ "$WHAT" = base ] || [ "$WHAT" = all ]; then build base || bad=1; run base PASS; fi
if [ "$WHAT" = mut ] || [ "$WHAT" = all ]; then
  for m in OT_S81HD_CTL_MUT_SLICE OT_S81HD_CMP_MUT_TIE; do n=mut_${m##*MUT_}; build $n +define+$m || bad=1; run $n FAIL; done
fi
[ $bad = 0 ] && echo "HD_CTL_BENCH PASS" || echo "HD_CTL_BENCH FAIL"; exit $bad
