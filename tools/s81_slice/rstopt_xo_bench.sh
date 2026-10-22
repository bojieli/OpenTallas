#!/bin/bash
# rstopt_xo_bench.sh <outdir> [MUT none|xooff|xoall|xonoflag|tiercol]  (cwd = repo root): S81-FIX2/XG (10-21)
# The RG-HEAD rstop_xo bench (tools/s81_slice/rstop_xo_bench.sh: tb_s81sl_rstop_sid on 16 straps + tb_s81sl_rstop_xo:
# egress rules on 16 straps + the 16-stop die ring, 80 flagged / 80 unflagged beats) run unchanged against
# ot_s81sl_rstopt_xo (the structurally safe ring stop + head egress in ot_s81sl_xgt_xo): tb copies with the instance master
# swapped (tb sources unchanged), + ot_rst_relay.  MUT none must PASS both; xooff / xoall / xonoflag must FAIL the xo
# bench; tiercol must FAIL the sid bench.  Verilator: the closure daemon's 5.050.  Exit 0 = the expected verdict.
set -u; O=$1; M=${2:-none}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
D=""
case $M in xooff) D="+define+OT_S81SL_RSTOP_MUT_XOOFF";; xoall) D="+define+OT_S81SL_RSTOP_MUT_XOALL";;
  xonoflag) D="+define+OT_S81SL_RSTOP_MUT_XONOFLAG";; tiercol) D="+define+OT_S81SL_RSTOP_MUT_TIERCOL";; none) ;; *) echo "BAD MUT"; exit 2;; esac
RTL="rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt_xo.sv"
$V --version > $O/version_$M.log
sed 's/ot_s81sl_rstop u /ot_s81sl_rstopt_xo u /' rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_sid.sv > $O/tb_s81sl_rstop_sid_txo_$M.sv
sed 's/ot_s81sl_rstop_xo u /ot_s81sl_rstopt_xo u /' rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_xo.sv > $O/tb_s81sl_rstop_xo_txo_$M.sv
[ $(grep -c "ot_s81sl_rstopt_xo u " $O/tb_s81sl_rstop_sid_txo_$M.sv) = 1 ] || { echo "BENCH_SETUP_FAILED sid tb swap"; exit 4; }
[ $(grep -c "ot_s81sl_rstopt_xo u " $O/tb_s81sl_rstop_xo_txo_$M.sv) = 2 ] || { echo "BENCH_SETUP_FAILED xo tb swap"; exit 4; }
sha256sum $RTL rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_sid.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rstop_xo.sv $0 > $O/sources_$M.sha256
for T in sid xo; do
  if [ $T = sid ]; then TOP=tb_s81sl_rstop_sid; TB=$O/tb_s81sl_rstop_sid_txo_$M.sv; else TOP=tb_s81sl_rstop_xo; TB=$O/tb_s81sl_rstop_xo_txo_$M.sv; fi
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $D --top-module $TOP -Mdir $O/obj_${T}_$M $RTL $TB \
    --build-jobs ${J:-4} > $O/build_${T}_$M.log 2>&1 || { echo "BUILD_FAILED $T"; grep -m8 "%Error" $O/build_${T}_$M.log; exit 3; }
  $O/obj_${T}_$M/V$TOP > $O/run_${T}_$M.log 2>&1
  grep -E "^MISMATCH|^EGRESS_BAD|^RSTOP_XO|^PASS|^FAIL|^E7" $O/run_${T}_$M.log | head -14
done
ps=$(grep -c '^PASS rstop_sid' $O/run_sid_$M.log); px=$(grep -c '^PASS rstop_xo' $O/run_xo_$M.log)
case $M in
  none) [ $ps = 1 ] && [ $px = 1 ] && { echo "BENCH_PASS rstopt_xo (sid + xo)"; exit 0; }; echo "BENCH_FAIL rstopt_xo sid=$ps xo=$px"; exit 1;;
  tiercol) [ $ps = 0 ] && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$M"; exit 0; };;
  *) [ $px = 0 ] && grep -q '^FAIL rstop_xo' $O/run_xo_$M.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$M"; exit 0; };;
esac
echo "NEGATIVE_CONTROL_PASSED MUT=$M (bench blind)"; exit 1
