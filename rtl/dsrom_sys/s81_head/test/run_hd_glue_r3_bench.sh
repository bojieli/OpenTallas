#!/usr/bin/env bash
# S81 HEAD glue R3 (STW-S81c-HEAD-GLUE 10-22): the unchanged HD-CTL bench (tb_s81hd_ctl.sv) on the reconstruction
# ot_s81hd_ctl_peer (= R3 ot_s81hd_ctl_glue + the CLOSED dsfd_mtp_seq peer), Verilator 5.050 (closure daemon version).
# Usage: run_hd_glue_r3_bench.sh OUTDIR [all | sim base|SLICE|TIE|TKF]   (TKF: R3 mutant, token free pulse dropped)
set -u; O=${1:?outdir}; WHAT=${2:-all}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
T=rtl/dsrom_sys/s81_head
sed "s/ot_s81hd_ctl dut/ot_s81hd_ctl_peer dut/" $T/test/tb_s81hd_ctl.sv > $O/peer_tb.sv
SRCS="rtl/lib/ot_rst_relay_tree3.sv $T/ot_s81hd_util.sv $T/ot_s81hd_ctl.sv $T/ot_s81hd_glue_rg.sv $T/ot_s81hd_ctl_glue_r3.sv
 $T/test/ot_s81hd_ctl_peer_wrap.sv rtl/dsrom_sys/mtp/dsfd_mtp_tops.sv rtl/dsrom_sys/mtp/ot_dsrom_mtp_seq.sv
 rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
build() { n=$1; shift
  $V --version > $O/verilator_version.txt
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style "$@" \
    --top-module tb_s81hd_ctl -Mdir $O/$n $SRCS $O/peer_tb.sv --build-jobs ${J:-8} \
    > $O/build_$n.log 2>&1 || { echo "BUILD_FAILED $n"; grep -m10 %Error $O/build_$n.log; return 2; }
}
def() { case $1 in SLICE) echo +define+OT_S81HD_CTL_MUT_SLICE ;; TIE) echo +define+OT_S81HD_CMP_MUT_TIE ;; TKF) echo +define+OT_S81HD_R3_MUT_TKF ;; esac; }
if [ "$WHAT" = sim ]; then n=sim_${3:-base}
  build $n $(def ${3:-base}) || exit 2; $O/$n/Vtb_s81hd_ctl > $O/$n.log 2>&1; cat $O/$n.log; grep -q '^PASS hd_ctl' $O/$n.log; exit $?
fi
bad=0
for m in base SLICE TIE TKF; do
  build $m $(def $m) || { bad=1; continue; }
  $O/$m/Vtb_s81hd_ctl > $O/$m.log 2>&1; v=$(grep -m1 -E "^(PASS|FAIL) hd_ctl" $O/$m.log); echo "$m: $v"
  if [ $m = base ]; then echo "$v" | grep -q '^PASS hd_ctl' || bad=1; else echo "$v" | grep -q '^FAIL hd_ctl' || { echo "  $m NOT detected"; bad=1; }; fi
done
[ $bad = 0 ] && echo "HD_GLUE_R3_BENCH PASS" || echo "HD_GLUE_R3_BENCH FAIL"; exit $bad
