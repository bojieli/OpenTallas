#!/bin/bash
# rstop_xmid_bench.sh <outdir>  (cwd = repo root): FAM-S81-LEPE-4 XG-1 bench of the ring stop XMID face stage.
# For each variant (ot_s81sl_rstop, _rstop_xo, _rstopt, _rstopt_xo): tb_s81sl_rstop_xmid (XMID 1 == XMID 0 one edge later,
# 4 strap pairs, sparse random traffic on every port) must PASS; the XMIDSKIP mutant must FAIL.  Then the existing
# rstop_sid bench at XMID 0 and XMID 1 (+define+OT_S81SL_RSTOP_XMID1) must PASS.  Exit 0 = every expected verdict.
set -u; O=${1:?outdir}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
SL=rtl/dsrom_sys/s81_dv/slice; bad=0
for d in ot_s81sl_rstop ot_s81sl_rstop_xo ot_s81sl_rstopt ot_s81sl_rstopt_xo; do
  for m in none skip; do
    D="+define+TB_XMID_DUT=$d"; [ $m = skip ] && D="$D +define+OT_S81SL_RSTOP_MUT_XMIDSKIP"
    n=${d}_$m
    $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $D --top-module tb_s81sl_rstop_xmid -Mdir $O/obj_$n \
      rtl/lib/ot_rst_relay.sv $SL/$d.sv $SL/test/tb_s81sl_rstop_xmid.sv --build-jobs ${J:-4} > $O/build_$n.log 2>&1 \
      || { echo "BUILD_FAILED $n"; grep -m6 %Error $O/build_$n.log; bad=1; continue; }
    $O/obj_$n/Vtb_s81sl_rstop_xmid > $O/run_$n.log 2>&1; v=$(grep -m1 -E "^(PASS|FAIL) " $O/run_$n.log)
    echo "$n: $v"
    if [ $m = none ]; then echo "$v" | grep -q "^PASS" || bad=1; else echo "$v" | grep -q "^FAIL" || { echo "  $n mutant NOT detected"; bad=1; }; fi
  done
done
for x in 0 1; do
  D=""; [ $x = 1 ] && D="+define+OT_S81SL_RSTOP_XMID1"
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $D --top-module tb_s81sl_rstop_sid -Mdir $O/obj_sid$x \
    $SL/ot_s81sl_rstop.sv $SL/test/tb_s81sl_rstop_sid.sv --build-jobs ${J:-4} > $O/build_sid$x.log 2>&1 || { echo "BUILD_FAILED sid$x"; bad=1; continue; }
  $O/obj_sid$x/Vtb_s81sl_rstop_sid > $O/run_sid$x.log 2>&1; v=$(grep -m1 -E "^(PASS|FAIL) " $O/run_sid$x.log); echo "rstop_sid XMID $x: $v"
  echo "$v" | grep -q "^PASS" || bad=1
done
[ $bad = 0 ] && echo "RSTOP_XMID_GATE PASS" || echo "RSTOP_XMID_GATE FAIL"
exit $bad
