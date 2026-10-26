#!/bin/bash
# ve_spmiter.sh <outdir> [MUT 0..3] [SEED] [GAP]  (cwd = repo root): S81/RTLSPLIT miter bench tb_s81sl_ve_spmiter --
# the two-core split ot_s81sl_ve_sp (ve_m + ve_s, reduce stream +2 edges) against the unsplit r5 ot_s81sl_ve and the
# hdc_golden_v41 beat fixture; -DSYNTHESIS, every unreset register powered up random, 8 in-flight resets.
# OT_VE_DEFS (env): extra defines, e.g. -DOT_S81_VE_LOADSAFE5 (the kit's), -DOT_S81SL_SPMUT_MV (split mutant).
# MUT 0 (no SPMUT) must print "PASS MITER"; MUT 1..3 / SPMUT must print "MUTANT n REJECTED" (or fail the golden phase).  Exit 0 = PASS only.
set -u; O=$1; M=${2:-0}; SD=${3:-7}; G=${4:-0}; mkdir -p $O/fx
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 tools/s81_dv/ve_golden.py $O/fx --seed $SD > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED gold"; exit 4; }
E=rtl/dsrom_sys/s81_dv/eng/test
$V --binary --timing -O1 ${OT_VE_DEFS:-} -DSYNTHESIS --x-assign unique --x-initial unique -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GMUT=$M -GGAP=$G \
  --top-module tb_s81sl_ve_spmiter -Mdir $O/obj $(grep -v tb_ $E/ve.f) $E/tb_s81sl_ve_spmiter.sv \
  --build-jobs ${J:-4} > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
$O/obj/Vtb_s81sl_ve_spmiter +dir=$O/fx +verilator+rand+reset+2 +verilator+seed+$((SD+31)) > $O/run.log 2>&1
grep -E "^PASS|MUTANT|MITER|BAD|FAIL|fault" $O/run.log | head -10
if [ "$M" = 0 ] && ! echo "${OT_VE_DEFS:-}" | grep -q SPMUT; then
  grep -q '^PASS MITER' $O/run.log && grep -q '^PASS golden' $O/run.log && { echo "PASS ve spmiter MUT=0 SEED=$SD"; exit 0; }; echo "FAIL ve spmiter"; exit 1; fi
echo "FAIL ve spmiter MUT=$M ${OT_VE_DEFS:-}"; exit 1
