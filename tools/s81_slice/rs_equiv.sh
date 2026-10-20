#!/bin/bash
# rs_equiv.sh <outdir> [mut] (cwd = repo root): S81-XG4 (10-20) cycle equivalence of ot_s81sl_rs (native-bounded ring
# stop leaf) against CURRENT MAIN ot_s81sl_rstop (incl. S81-SMWIRE CI_XB) + a one-edge testbench relay on every relayed
# output (rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rs_equiv.sv).  13 cases: 8 random (incl. all-random header windows
# that fault), 3 protocol-legal (fault must stay 0, every class covered), 2 in-flight reset.
# [mut] = slice | cixb | frag | vasm | gswap | tiercol builds that negative control (ot_s81sl_rs only; the reference is
# untouched) and every case must FAIL (tiercol: sids 0 / 15 decode identically and must PASS).
# Final line RS_EQUIV_BENCH PASS|FAIL.
set -u; O=$(realpath -m $1); MUT=${2:-}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version | tee $O/verilator_version.log
D=""; EXP=PASS
case "$MUT" in
  "") ;;
  slice) D="+define+OT_S81SL_RS_MUT_SLICE"; EXP=FAIL;;
  cixb) D="+define+OT_S81SL_RSTOP_MUT_CIXB"; EXP=FAIL;;
  frag) D="+define+OT_S81SL_RSTOP_MUT_FRAG"; EXP=FAIL;;
  vasm) D="+define+OT_S81SL_RSTOP_MUT_VASM"; EXP=FAIL;;
  gswap) D="+define+OT_S81SL_RSTOP_MUT_GSWAP"; EXP=FAIL;;
  tiercol) D="+define+OT_S81SL_RSTOP_MUT_TIERCOL"; EXP=FAIL;;
  *) echo "unknown mutant $MUT"; echo "RS_EQUIV_BENCH FAIL"; exit 2;;
esac
S=rtl/dsrom_sys/s81_dv/slice
# the reference is compiled from a renamed copy so a mutant define cannot reach it
mkdir -p $O/ref; sed 's/OT_S81SL_RSTOP_MUT_/OT_S81SL_RSTOP_REFNOMUT_/g' $S/ot_s81sl_rstop.sv > $O/ref/ot_s81sl_rstop.sv
$V --cc --exe --build -j ${J:-8} -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 \
  --prefix Vrseq --top-module tb_s81sl_rs_equiv --Mdir $O/obj $D $O/ref/ot_s81sl_rstop.sv $S/ot_s81sl_rs.sv \
  $S/test/tb_s81sl_rs_equiv.sv $S/test/tb_s81sl_rs_equiv.cpp -o tb > $O/build.log 2>&1 || { echo BUILD_FAILED; tail -20 $O/build.log; echo "RS_EQUIV_BENCH FAIL"; exit 3; }
ALL=1
for c in "0 1 40 0 0" "5 2 40 0 0" "7 3 80 0 0" "8 4 20 0 0" "9 5 120 0 0" "14 6 40 0 0" "15 7 60 0 0" "3 8 200 0 0" \
         "2 11 60 1 0" "13 12 100 1 0" "6 13 30 1 0" "4 14 60 0 7000" "11 15 80 1 9000"; do
  set -- $c
  $O/obj/tb +sid=$1 +seed=$2 +dens=$3 +legal=$4 +rstat=$5 +cycles=20000 > $O/case_s$1_r$2.log 2>&1
  got=FAIL; grep -q '^RS_EQUIV PASS' $O/case_s$1_r$2.log && got=PASS
  exp=$EXP; [ "$MUT" = tiercol ] && { [ $1 = 0 ] || [ $1 = 15 ]; } && exp=PASS
  ok=0; [ $got = $exp ] && ok=1; [ $ok = 1 ] || ALL=0
  echo "RS_CASE sid=$1 seed=$2 dens=$3 legal=$4 rstat=$5 $got expected=$exp ok=$ok :: $(grep -h '^RS_EQUIV sid' $O/case_s$1_r$2.log)"
  grep -h '^MISMATCH' $O/case_s$1_r$2.log | head -2
done
[ $ALL = 1 ] && { echo "RS_EQUIV_BENCH PASS"; exit 0; }; echo "RS_EQUIV_BENCH FAIL"; exit 1
