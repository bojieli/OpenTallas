#!/bin/bash
# norm16_bench.sh <outdir> [base|mutbase|mutleaf] [slice|xfin]  (cwd = repo root): S81-DV norm exchange benches on the
# DS1M golden hc_pre + RMSNorm row under Verilator 5.
#   slice: tb_s81dv_norm16 -- 16 x ot_s81dv_norm_slice (16 real G64 groups) on the slice ring
#   xfin : tb_s81dv_xfin16 -- the minimum vehicle: one real G64 group (all 80 beats) + 16 real ot_s81dv_xfin leaves
# base must print PASS; mutbase (slice 3 tags its partials as slice 4's) / mutleaf (finish leaves 0/1 swapped) are
# negative controls that must FAIL.  Exit 0 = the expected verdict.
set -u; O=$1; M=${2:-base}; V=${3:-xfin}; mkdir -p $O/run
G0=results/rtl/hbm_norm_engine_view_20261006/gold
MACV=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
ls $G0/x.mem $G0/ey.mem > /dev/null 2>&1 || { echo "BENCH_SETUP_FAILED: golden memories missing under $G0"; exit 4; }
TOP=tb_s81dv_xfin16; TAG=dvxfin16; [ "$V" = slice ] && { TOP=tb_s81dv_norm16; TAG=dvnorm16; }
DEF=""; [ "$M" = mutbase ] && DEF="+define+OT_S81DV_MUT_BASE"; [ "$M" = mutleaf ] && DEF="+define+OT_S81DV_MUT_LEAF"
srcs="$(cat physical/hbm_norm_split_20261008/sources.f | tr '\n' ' ') $MACV rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv rtl/dsrom_sys/s81_dv/test/$TOP.sv"
verilator --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF --top-module $TOP -Mdir $O/obj $srcs \
  --build-jobs ${J:-1} --output-split 5000 --output-split-cfuncs 500 -MAKEFLAGS "OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 5 $O/build.log; exit 3; }
cp $G0/x.mem $G0/w.mem $G0/cfg.mem $G0/ey.mem $O/run/ && (cd $O/run && ../obj/V$TOP > ../run.log 2>&1)
grep -E "^DV|MISMATCH" $O/run.log | head -9
if [ "$M" = base ]; then grep -q '^PASS' $O/run.log && { echo "PASS $TAG"; exit 0; }; echo "FAIL $TAG"; exit 1; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
