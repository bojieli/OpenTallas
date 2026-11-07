#!/bin/bash
# run_wcopy.sh RTLDIR: W=1,2 PASS at D=1; controls D=0, MUT_COHERENCE, MUT_WCOPY 1,2 must FAIL
S=/srv/opentallas-scratch3/claude/hbm-form-split-14-sux; RD=$1; O=$S/wc; V=$HOME/.local/opentallas-tools/bin/verilator
H=$S/repo/physical/die_plan/hbm/over_cap_split/reform_1103/bench/lanes8_11/sram_bench_model.sv; TB=$S/repo/results/die_hbm_1106/sux/wcopy/tb_wcopy.sv
for c in "1 1 0 0" "2 1 0 0" "1 0 0 0" "2 0 0 0" "1 1 1 0" "2 1 1 0" "1 1 0 1" "2 1 0 1" "1 1 0 2" "2 1 0 2"; do
  set -- $c; T=w$1d$2c$3m$4; rm -rf $O/$T
  prlimit --as=16000000000 $V --binary -j 4 --timing -Wno-fatal -Wno-lint -Wno-style -DW=$1 -DD=$2 -DMC=$3 -DMW=$4 --top-module tb -Mdir $O/$T -o sim $TB $RD/ot_hbm_su_static_pinned_bank.sv $RD/ot_hbm_su_static_data_store.sv $H > $O/$T.build.log 2>&1 || { echo BUILD FAIL $T; tail -5 $O/$T.build.log | cut -c1-200; continue; }
  $O/$T/sim > $O/$T.log 2>&1; grep XEQ $O/$T.log || { echo NORESULT $T; tail -3 $O/$T.log | cut -c1-200; }; rm -rf $O/$T
done
