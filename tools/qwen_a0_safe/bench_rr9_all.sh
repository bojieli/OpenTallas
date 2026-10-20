#!/bin/bash
# QW-CB16A0-2: REGROOT 9 proof + its five mutants (each must FAIL with A0_RR9_FAIL), one Verilator build.
set -uo pipefail
OUT=${1:-bench_rr9}
bash tools/qwen_a0_safe/bench_rr9.sh "$OUT" 0; rc0=$?
echo "RR9_MUT0_RC=$rc0"
for m in 60 61 62 63 64; do
  bash tools/qwen_a0_safe/bench_rr9.sh "$OUT" $m > /dev/null 2>&1; rc=$?
  if grep -q 'A0_RR9_FAIL\|RR9_VS_RR8\|ROMLEAF_PARENT_NK_MISMATCH' "$OUT/run_$m.log"; then echo "RR9_MUT${m}=KILLED rc=$rc"; else echo "RR9_MUT${m}=SURVIVED rc=$rc"; fi
done
exit $rc0
