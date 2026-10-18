#!/bin/bash
# run_eg_bench.sh <outdir> [MUT] [GAP] [SEED]  (cwd = repo root): tb_s81sl_eg vs tools/s81_dv/eg_golden.py under Verilator 5.
# MUT 0 must print PASS (exit 0); MUT 1..3 must print FAIL MUTANT (exit 0 = expected verdict for the negative control).
set -u; O=$1; M=${2:-0}; G=${3:-3}; S=${4:-1}; mkdir -p $O
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
python3 tools/s81_dv/eg_golden.py $O/fx --seed $S --ncase 32 > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED"; cat $O/gold.log; exit 4; }
$V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GMUT=$M -GGAP=$G --top-module tb_s81sl_eg -Mdir $O/obj \
  $(cat rtl/dsrom_sys/s81_dv/eng/test/eg.f) rtl/dsrom_sys/s81_dv/eng/test/tb_s81sl_eg.sv --build-jobs ${J:-4} > $O/build.log 2>&1 \
  || { echo "BUILD_FAILED"; tail -n 12 $O/build.log; exit 3; }
grep -E "PINMISSING|PINCONNECTEMPTY" $O/build.log | grep -i s81sl_eg | head -5
$O/obj/Vtb_s81sl_eg +dir=$O/fx > $O/run.log 2>&1
cat $O/gold.log; grep -E "^PASS|^FAIL|^BAD|MUTANT|TIMEOUT|fault|Error|fatal" $O/run.log | head -12
if [ "$M" = 0 ]; then grep -q '^PASS' $O/run.log && exit 0; exit 1; fi
grep -q '^FAIL MUTANT' $O/run.log && exit 0; exit 1
