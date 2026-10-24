#!/bin/bash
# OT_VE_DEFS (env, optional): extra Verilator defines, e.g. -DOT_S81_VE_LOADSAFE5 for the VE5 opt-in source (S81-GUVE 10-20).
# ve_mixmiter.sh (CORE-S81 10-23: reference = the die S81U-MIX ve 5074ac6aa, test/ref_mix) -- from ve_miter.sh <outdir> [MUT] [SEED] [GAP] (cwd = repo root): S81-VE4 miter bench tb_s81sl_ve_miter -- ot_s81sl_ve (r4, DUT)
# against the r3 RTL (test/ref_r3, renamed) and the hdc_golden_v41 beat fixture, Verilator 5.050, -DSYNTHESIS (no
# simulation initial values), every unreset register of both designs powered up independently random, 8 in-flight resets.
# MUT 0 must print "PASS MITER"; MUT 1..3 (DUT only) must print "MUTANT n REJECTED".  Exit 0 = PASS only.
set -u; O=$1; M=${2:-0}; SD=${3:-7}; G=${4:-0}; mkdir -p $O/fx
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 tools/s81_dv/ve_golden.py $O/fx --seed $SD > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED gold"; exit 4; }
E=rtl/dsrom_sys/s81_dv/eng/test
$V --binary --timing -O1 ${OT_VE_DEFS:-} -DSYNTHESIS --x-assign unique --x-initial unique -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GMUT=$M -GGAP=$G \
  --top-module tb_s81sl_ve_mixmiter -Mdir $O/obj $(grep -v tb_ $E/ve.f) $E/ref_mix/mixref_ot_s81sl_ve.sv $E/tb_s81sl_ve_mixmiter.sv \
  --build-jobs ${J:-4} > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
$O/obj/Vtb_s81sl_ve_mixmiter +dir=$O/fx +verilator+rand+reset+2 +verilator+seed+$((SD+31)) > $O/run.log 2>&1
grep -E "^PASS|MUTANT|MITER|BAD|FAIL|fault" $O/run.log | head -10
if [ "$M" = 0 ]; then grep -q '^PASS MITER' $O/run.log && grep -q '^PASS golden' $O/run.log && { echo "PASS ve miter MUT=0 SEED=$SD"; exit 0; }; echo "FAIL ve miter"; exit 1; fi
echo "FAIL ve miter MUT=$M"; exit 1
