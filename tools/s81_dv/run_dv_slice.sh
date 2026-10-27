#!/bin/bash
# run_dv_slice.sh <kit dir> <out dir> [plusargs...] : LAYERBENCH-S81 (10-18) build + run of a cut S81-DV slice replay bench.
#   kit dir = tools/s81_dv/dv_rtl_kit.py output for the slice top (kit.f, src/), plus tb/tb_<top>.sv from dv_slice_tb.py.
#   Records build wall / RSS (build.time), run wall / RSS (run.time), DV_SLICE_T0/T1 -> simulated cycles per wall second.
#   Env: VL (default the closure daemon's pinned Verilator 5.050), J (build jobs, 32), TOP (slice_top), VFLAGS (extra),
#   OBJ=<dir> (default <out>/obj): a prebuilt obj dir is reused (no build) when OBJ/sim exists.  Exit status = 0 only on TB_DV_SLICE PASS.
set -u
K=$(realpath $1); OUT=$(realpath -m $2); shift 2
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; J=${J:-32}; TOP=${TOP:-slice_top}
mkdir -p $OUT; cd $K
$VL --version > $OUT/verilator.version 2>&1
( sha256sum $(grep -v '^+' kit.f) tb/tb_$TOP.sv ) > $OUT/sources.sha256
OBJ=${OBJ:-$OUT/obj}
if [ ! -x $OBJ/sim ]; then
  /usr/bin/time -v -o $OUT/build.time $VL --binary --timing -j $J -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN \
    -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE --unroll-count 4 -fno-dfg -CFLAGS -O1 ${VFLAGS:-} \
    --top-module tb_$TOP -f kit.f tb/tb_$TOP.sv --Mdir $OBJ -o sim > $OUT/build.log 2>&1
  echo "build rc $?" > $OUT/status
else echo "build reused $OBJ" > $OUT/status; fi
[ -x $OBJ/sim ] || { grep -m8 "%Error" $OUT/build.log; cat $OUT/status; exit 3; }
/usr/bin/time -v -o $OUT/run.time $OBJ/sim "$@" > $OUT/run.log 2>&1; echo "run rc $?" >> $OUT/status
t0=$(grep -h DV_SLICE_T0 $OUT/run.log | cut -d= -f2); t1=$(grep -h DV_SLICE_T1 $OUT/run.log | cut -d= -f2)
n=$(grep -ho "DV_SLICE cycles=[0-9]*" $OUT/run.log | cut -d= -f2)
[ -n "$t0" ] && [ -n "$t1" ] && [ -n "$n" ] && echo "rate $(python3 -c "print(round($n/($t1-$t0),1))") cyc/s" >> $OUT/status
grep -h "Elapsed\|Maximum resident" $OUT/build.time $OUT/run.time >> $OUT/status 2>/dev/null
grep -h "TB_DV_SLICE\|DV_SLICE cycles" $OUT/run.log >> $OUT/status 2>/dev/null
cat $OUT/status
grep -q "TB_DV_SLICE PASS" $OUT/run.log
