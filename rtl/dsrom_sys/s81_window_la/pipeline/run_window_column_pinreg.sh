#!/bin/bash
# REDESIGN-S81 2026-10-08: WINDOW column PINREG cycle-exactness bench (iverilog): seeds 1..3 gold + NOBYPASS mutant (must FAIL)
set -u
O=$(readlink -f ${1:-.}); mkdir -p $O; D=$(cd $(dirname $0) && pwd)
S="$D/tb_window_column_pinreg.sv $D/ot_dsrom_window_stage_pipeline.sv"
iverilog -g2012 -s tb_window_column_pinreg -o $O/g.vvp $S > $O/build_g.log 2>&1; echo "build g rc=$?"
iverilog -g2012 -DOT_WCOL_MUT_NOBYPASS -s tb_window_column_pinreg -o $O/m.vvp $S > $O/build_m.log 2>&1; echo "build m rc=$?"
for s in 1 2 3; do vvp -n $O/g.vvp +SEED=$s > $O/run_g_$s.log 2>&1; done
vvp -n $O/m.vvp +SEED=1 > $O/run_m1.log 2>&1
for f in $O/run_*.log; do echo "$(basename $f): $(grep -h SUMMARY $f) $(grep -h RESULT $f)"; done > $O/summary.txt
cat $O/summary.txt
