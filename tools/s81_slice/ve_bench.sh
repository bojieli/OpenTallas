#!/bin/bash
# OT_VE_DEFS (env, optional): extra Verilator defines, e.g. -DOT_S81_VE_LOADSAFE5 for the VE5 opt-in source (S81-GUVE 10-20).
# ve_bench.sh <outdir> [MUT 0|1|2] [GAP] [SEED] (cwd = repo root): S81U-MIX ot_s81sl_ve beat bench (tb_s81sl_ve) on
# tools/s81_dv/ve_golden.py fixtures (hdc_golden_v41 chunk8).  MUT 0 must print PASS; MUT 1 / 2 / 3 must be rejected.
# Every register without reset powers up RANDOM (--x-initial unique + rand+reset 2): reset-free data / pointers are exercised.
# Exit 0 = PASS only (expect=fail form for the mutants: a rejected mutant exits 1 with "MUTANT n REJECTED").
set -u; O=$1; M=${2:-0}; G=${3:-0}; SD=${4:-7}; mkdir -p $O/fx
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 tools/s81_dv/ve_golden.py $O/fx --seed $SD > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED gold"; exit 4; }
$V --binary --timing -O1 ${OT_VE_DEFS:-} --x-assign unique --x-initial unique -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GMUT=$M -GGAP=$G --top-module tb_s81sl_ve -Mdir $O/obj \
  $(cat rtl/dsrom_sys/s81_dv/eng/test/ve.f) --build-jobs ${J:-4} > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
$O/obj/Vtb_s81sl_ve +dir=$O/fx +verilator+rand+reset+2 +verilator+seed+$((SD+11)) > $O/run.log 2>&1
grep -E "^PASS|MUTANT|BAD|FAIL|fault" $O/run.log | head -8
if [ "$M" = 0 ]; then grep -q '^PASS' $O/run.log && { echo "PASS ve MUT=0 GAP=$G"; exit 0; }; echo "FAIL ve"; exit 1; fi
echo "FAIL ve MUT=$M"; exit 1
