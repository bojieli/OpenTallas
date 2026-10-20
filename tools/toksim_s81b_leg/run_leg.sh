#!/bin/bash
# TOKSIM-S81B/LEG (10-19): build + run tb_leg_s81 on the fleet; cwd = the staged root (stage.sh).
#   bash tools/toksim_s81b_leg/run_leg.sh <out> [verilator +define+ args]   (golden/ = gen_leg.py output, staged)
# Verilator = the closure daemon's 5.050.  Prints BUILD_OK / BENCH_PASS / BENCH_FAIL.
set -u
O=$1; shift
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
[ -x $V ] || { echo "NO_VERILATOR_5050"; exit 4; }
SRCS="rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv rtl/dsrom_sys/s81_glue/ot_s81_rly.sv
 rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvh.sv
 rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv rtl/dsrom_sys/s81_dv/land/dsfd_dvland.sv
 rtl/test/toksim_s81b_leg/leg.vlt rtl/test/toksim_s81b_leg/leg_chain_gen.sv rtl/test/toksim_s81b_leg/tb_leg_s81.sv"
for f in $SRCS; do [ -f $f ] || { echo "BUILD_FAILED missing $f"; exit 3; }; done
mkdir -p $O
$V --version > $O/verilator_version.txt; cat $O/verilator_version.txt
sha256sum $SRCS > $O/sources.sha256
/usr/bin/time -v -o $O/time_build.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
  -Wno-lint -Wno-style "$@" --top-module tb_leg_s81 -Mdir $O/obj $SRCS --build-jobs ${J:-8} \
  -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
  || { echo "BUILD_FAILED"; grep -m12 -E "%Error" $O/build.log; exit 3; }
echo BUILD_OK
cp golden/stim.hex $O/stim.hex
NS=$(cat golden/NS)
( cd $O && /usr/bin/time -v -o time_run.log ./obj/Vtb_leg_s81 +NS=$NS > run.log 2>&1 )
grep -E "^LEG_CFG|^LEG_STATS|^PASS|^FAIL|^MISMATCH" $O/run.log | head -12
gzip -kf $O/run.log
grep -q "^PASS leg_s81" $O/run.log && { echo BENCH_PASS; exit 0; }; echo BENCH_FAIL; exit 1
