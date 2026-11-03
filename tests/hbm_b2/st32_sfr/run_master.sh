#!/bin/bash
# DIE-HBM-61/RTL-ST32 master lockstep + mutants (epyc2, memory-capped scopes)
set -u
W=/home/ubuntu/scratch-root/claude/dhbm61-st32-work; cd $W; export PATH=$HOME/.local/opentallas-tools/bin:$PATH
mkdir -p mt && python3 -I mk_variants.py old_master.sv sfr1e/master/ot_hbm_hc_subtree32_core.sv mt > mt/variants.log 2>&1 || { echo variants FAIL; cat mt/variants.log; exit 1; }
one() { v=$1; exp=$2; d=mt/b_$v; mkdir -p $d
  systemd-run --user --scope -q -p MemoryMax=24G verilator --binary --timing -j 12 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb -Mdir $d/obj -o tb tb_master.sv mt/old.v mt/$v.v > $d/build.log 2>&1 || { echo "$v expect=$exp BUILD_FAIL"; return; }
  $d/obj/tb > $d/run.log 2>&1; rc=$?; echo "$v expect=$exp rc=$rc: $(grep ST32_LOCKSTEP $d/run.log)"; }
for v in new:pass mut_nf_balance:fail mut_nf_nodelay:fail mut_fi_bypass:fail mut_word_swap:fail mut_nf_order:fail; do one ${v%%:*} ${v##*:} & done; wait
