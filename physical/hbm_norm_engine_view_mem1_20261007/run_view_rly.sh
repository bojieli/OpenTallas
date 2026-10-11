#!/bin/bash
# run_view_rly.sh <outdir> [skew]  (cwd = repo root): view RLY=1 XST=1 vs the pinned view (RLY=0 XST=0), lagged lockstep
# on the DS1M golden row + 3 overlapped rows (tb_norm_view_rly_lockstep).  skew: OT_NEV_MUT_SKEW negative control
# (gain data skips the XST stage) must print FAIL at line start.
set -u; O=$1; M=${2:-}; mkdir -p $O; V=physical/hbm_norm_engine_view_mem1_20261007; G=results/rtl/hbm_norm_engine_view_20261006/gold
DEF=""; [ "$M" = skew ] && DEF=+define+OT_NEV_MUT_SKEW
srcs=$(cat $V/sources.f | tr '\n' ' ')
MACV=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF --top-module tb_norm_view_rly_lockstep -Mdir $O/obj $srcs $MACV \
  rtl/test/tb_norm_view_rly_lockstep.sv --build-jobs 16 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo BUILD_FAILED; tail -n 5 $O/build.log; exit 3; }
mkdir -p $O/run; cp $G/*.mem $O/run/; (cd $O/run && ../obj/Vtb_norm_view_rly_lockstep > ../run.log 2>&1); grep -E "^LOCKSTEP|^MISMATCH|^PASS|^FAIL" $O/run.log
grep -q '^PASS' $O/run.log
