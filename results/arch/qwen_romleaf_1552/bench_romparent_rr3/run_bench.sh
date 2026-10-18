#!/bin/bash
# S-QA0: rr parent benches (NK/NL) + mutants on main RTL (b906e0fd6)
cd "$(dirname "$0")/src" || exit 9
OUT=../out; mkdir -p $OUT
for t in nk nl; do
  S=tools/qwen_romleaf/parent_bench_rr.sh; [ $t = nk ] && S=tools/qwen_romleaf/parent_nk_bench_rr.sh
  for m in 0 4 14 21 22 23 24 25 26 27; do
    bash $S $OUT/$t $m > $OUT/log_${t}rr_$m.txt 2>&1; rc=$?
    echo "BENCH ${t}rr MUT$m exit $rc $(grep -m1 -E 'ROMLEAF_PARENT(_NK)?_NATIVE_(PASS|FAIL)' $OUT/log_${t}rr_$m.txt | cut -c1-120)"
  done
done
