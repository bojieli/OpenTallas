#!/bin/bash
# run_lockstep.sh <outdir> [addr|late]  (cwd = repo root): MEM=1 vs MEM=0 lockstep on the DS1M golden row + 3 overlapped rows.
# addr: x write address off by one (OT_SUN_MEM_MUT_ADDR); late: macro read not issued ahead (OT_SUN_MEM_MUT_LATE).
# Both negative controls must print FAIL at line start (closure-loop fail_regex (?m)^FAIL).
set -u; O=$1; M=${2:-}; mkdir -p $O; V=physical/hbm_norm_engine_view_mem1_20261007; G=results/rtl/hbm_norm_engine_view_20261006/gold
DEF=""; [ "$M" = addr ] && DEF=+define+OT_SUN_MEM_MUT_ADDR; [ "$M" = late ] && DEF=+define+OT_SUN_MEM_MUT_LATE
srcs=$(grep -v norm_engine_view $V/sources.f | tr '\n' ' ')
MACV=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF --top-module tb_su_norm_mem_lockstep -Mdir $O/obj $srcs $MACV \
  rtl/test/tb_su_norm_mem_lockstep.sv --build-jobs 16 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo BUILD_FAILED; tail -n 5 $O/build.log; exit 3; }
mkdir -p $O/run; cp $G/*.mem $O/run/; (cd $O/run && ../obj/Vtb_su_norm_mem_lockstep > ../run.log 2>&1); grep -E "^LOCKSTEP|^MISMATCH|^PASS|^FAIL" $O/run.log
grep -q '^PASS' $O/run.log
