#!/usr/bin/env bash
# PL-SLICE (10-18): every bench of the landed S81-DV slice parent, run on the FLEET (cwd = repo root / staged copy).
#   X    tb_s81sl_slice_x: wires-only flat ot_s81sl_slice_c{1,3}x == original ot_s81sl_slice (HB 0 / 1), MUT 1 must FAIL
#   LP   lp.py lockstep benches (landed vs flat reference, MUT 1/2/4 FAIL, region audit PASS, unland FAIL), C1 and C3
#   ENG  the slice golden bench tb_s81sl_slice_eng on the LANDED C1 (wrapper): VS_MUT 0 PASS, VS_MUT 7 FAIL
# usage: [PARTS="x lp eng"] pl_slice_bench.sh OUT     exit 0 iff every selected part gives its expected verdict
set -u; O=$(realpath -m ${1:-pl_slice_out}); mkdir -p $O; rc=0; PARTS=${PARTS:-x lp eng}; has() { case " $PARTS " in *" $1 "*) return 0;; esac; return 1; }
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
export VERILATOR=$V VL_JOBS=${VL_JOBS:-4} VL_EXTRA="-Wno-WIDTH -Wno-TIMESCALEMOD -O1" SIM=verilator
SRCS=$(python3 -c "import json; s=json.load(open('tools/s81_slice/pl_slice/c1x.json')); print(' '.join(s['child_sources']))")
x_part() {   # $1 HB, $2 MUT
  local d=$O/x_hb$1_m$2; mkdir -p $d
  $V --binary -j $VL_JOBS -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -O1 +define+DSFD_PQ_STATIC_X2 -GHB=$1 -GMUT=$2 \
     --top-module tb_s81sl_slice_x -Mdir $d/obj $SRCS rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_c1x.sv \
     rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_c3x.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_slice_x.sv > $d/build.log 2>&1 \
     && $d/obj/Vtb_s81sl_slice_x > $d/run.log 2>&1
  grep -h "^SLX" $d/run.log 2>/dev/null | head -3 | sed "s/^/[x hb$1 m$2] /"
}
has x && { ( x_part 0 0; x_part 0 1; x_part 1 0; x_part 1 1 ) > $O/x.txt 2>&1 & }
has lp && { ( bash rtl/dsrom_sys/s81_dv/slice/landed/c1x/ot_s81sl_slice_c1x_lp_bench.sh $O/lp_c1x ) > $O/lp_c1x.txt 2>&1 & }
has lp && { ( bash rtl/dsrom_sys/s81_dv/slice/landed/c3x/ot_s81sl_slice_c3x_lp_bench.sh $O/lp_c3x ) > $O/lp_c3x.txt 2>&1 & }
eng() {   # $1 VS_MUT
  local d=$O/eng_m$1; mkdir -p $d
  sed 's/^module ot_s81sl_slice #(/module ot_s81sl_slice_orig #(/' rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv > $d/slice_renamed.sv
  # the golden tb probes the flat hierarchy (u_dut.lf[k].u_lf, u_dut.xe_*, leaf 0's g_* relay output): same signals in the landed slice
  sed -e 's/u_dut\.lf\[\([0-4]\)\]\.u_lf/u_dut.u_lp.u_lf\1/g' -e 's/u_dut\.xe_/u_dut.u_lp.xe_/g' \
      -e 's/u_dut\.gv_l\[0\]/u_dut.u_lp.u_lf0.g_v/g' -e 's/u_dut\.gd_l\[31:0\]/u_dut.u_lp.u_lf0.g_d/g' \
      -e 's/u_dut\.gc_l\[1:0\]/u_dut.u_lp.u_lf0.g_c/g' rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_slice_eng.sv > $d/tb_s81sl_slice_eng_lp.sv
  SLICE_SRCS="$d/slice_renamed.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_glue.sv rtl/common/landed_parent/ot_pl_land.sv \
    rtl/dsrom_sys/s81_dv/slice/landed/c1x/ot_s81sl_slice_c1x_lp.sv rtl/dsrom_sys/s81_dv/slice/landed/test/ot_s81sl_slice_lpwrap.sv" \
    SLICE_ENG_TB=$d/tb_s81sl_slice_eng_lp.sv J=$VL_JOBS bash tools/s81_slice/slice_eng_bench.sh $d $1 3 > $d/verdict.txt 2>&1; echo "[eng VS_MUT=$1] exit $? $(tail -1 $d/verdict.txt)"
}
has eng && { ( eng 0 & eng 7 & wait ) > $O/eng.txt 2>&1 & }
wait
cat $O/x.txt $O/lp_c1x.txt $O/lp_c3x.txt $O/eng.txt 2>/dev/null
! has x || { grep -q "\[x hb0 m0\] SLX PASS" $O/x.txt && grep -q "\[x hb1 m0\] SLX PASS" $O/x.txt && grep -q "\[x hb0 m1\] SLX FAIL" $O/x.txt \
  && grep -q "\[x hb1 m1\] SLX FAIL" $O/x.txt || { echo "PART X: unexpected"; rc=1; }; }
! has lp || grep -q "BENCH_EXIT 0" $O/lp_c1x.txt || { echo "PART LP C1: unexpected"; rc=1; }
! has lp || grep -q "BENCH_EXIT 0" $O/lp_c3x.txt || { echo "PART LP C3: unexpected"; rc=1; }
! has eng || { grep -q "\[eng VS_MUT=0\] exit 0 PASS" $O/eng.txt && grep -q "\[eng VS_MUT=7\] exit 0 NEGATIVE_CONTROL_FAILED_AS_EXPECTED" $O/eng.txt \
  || { echo "PART ENG: unexpected"; rc=1; }; }
echo "PL_SLICE_BENCH_EXIT $rc"; exit $rc
