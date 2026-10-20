#!/bin/bash
# rs_equiv.sh <outdir> [mut] (cwd = repo root): S81-XG3 (10-19) cycle equivalence of ot_s81sl_rs (bit-sliced ring stop
# leaf) against ot_s81sl_rstop #(.RELAY(1)): random protocol-shaped stimulus on every input, every output compared every
# edge (rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_rs_equiv.sv).  Runs 8 (sid, seed, density) cases.  With 'mut' the
# OT_S81SL_RS_MUT_SLICE negative control is built and every case must FAIL.  Final line RS_EQUIV_BENCH PASS|FAIL.
set -u; O=$(realpath -m $1); MUT=${2:-}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version | tee $O/verilator_version.log
VROOT=$($V -V | sed -n 's/^ *VERILATOR_ROOT *= *//p' | head -1)
D=""; EXP=PASS; [ "$MUT" = mut ] && { D="+define+OT_S81SL_RS_MUT_SLICE"; EXP=FAIL; }
S=rtl/dsrom_sys/s81_dv/slice
$V --cc --exe --build -j ${J:-8} -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --x-assign 0 --x-initial 0 \
  --prefix Vrseq --top-module tb_s81sl_rs_equiv --Mdir $O/obj $D rtl/lib/ot_rst_relay.sv $S/ot_s81sl_rstop.sv $S/ot_s81sl_rs.sv \
  $S/test/tb_s81sl_rs_equiv.sv $S/test/tb_s81sl_rs_equiv.cpp -o tb > $O/build.log 2>&1 || { echo BUILD_FAILED; tail -20 $O/build.log; echo "RS_EQUIV_BENCH FAIL"; exit 3; }
ALL=1
for c in "0 1 40" "5 2 40" "7 3 80" "8 4 20" "9 5 120" "14 6 40" "15 7 60" "3 8 200"; do
  set -- $c
  $O/obj/tb +sid=$1 +seed=$2 +dens=$3 +cycles=20000 > $O/case_s$1_r$2.log 2>&1
  got=FAIL; grep -q '^RS_EQUIV PASS' $O/case_s$1_r$2.log && got=PASS
  ok=0; [ $got = $EXP ] && ok=1; [ $ok = 1 ] || ALL=0
  echo "RS_CASE sid=$1 seed=$2 dens=$3 $got expected=$EXP ok=$ok :: $(grep -h '^RS_EQUIV sid' $O/case_s$1_r$2.log)"
  grep -h '^MISMATCH' $O/case_s$1_r$2.log | head -2
done
[ $ALL = 1 ] && { echo "RS_EQUIV_BENCH PASS"; exit 0; }; echo "RS_EQUIV_BENCH FAIL"; exit 1
