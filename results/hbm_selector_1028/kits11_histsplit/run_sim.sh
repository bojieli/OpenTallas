#!/bin/bash
# HBM-CORES-KITS-11: selector hist generate-split, lockstep vs canonical for STRUCT=0 and STRUCT=1.
cd /srv/opentallas-scratch2/claude/kits11-1029/selsim
pids=()
for s in 0 1; do for c in full tie threshold fault; do
 (
  m=0;t=0
  case "$c" in tie)t=1;;threshold)m=1;t=1;;fault)m=3;;esac
  n=s${s}_$c
  iverilog -g2012 -s tb_hbm_idx_selector_sel_eq -Ptb_hbm_idx_selector_sel_eq.SMUT=$m -Ptb_hbm_idx_selector_sel_eq.TIE_ONLY=$t -Ptb_hbm_idx_selector_sel_eq.SSTRUCT=$s -o $n.vvp src/*.sv src/memory.v tb_s.sv > $n.build.log 2>&1 || { echo "$n BUILD_FAIL"; exit 1; }
  vvp $n.vvp > $n.run.log 2>&1; rc=$?
  if [ $m = 0 ]; then [ $rc = 0 ] && grep -q "TB_SEL_EQ PASS" $n.run.log && echo "$n PASS" || { echo "$n FAIL rc=$rc"; exit 1; }
  else [ $rc != 0 ] && grep -q "TB_SEL_EQ FAIL" $n.run.log && echo "$n MUTANT_CAUGHT" || { echo "$n MUTANT_MISSED rc=$rc"; exit 1; }; fi
 ) &
 pids+=($!)
done; done
rc=0; for p in "${pids[@]}"; do wait $p || rc=1; done
echo "SELSIM_DONE rc=$rc $(date)"
