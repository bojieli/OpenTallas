#!/bin/bash
# QW-A0-RC4: REGROOT 8 proof + its six mutants (each must FAIL with A0_RR8_FAIL), one Verilator build.
set -uo pipefail
OUT=${1:-bench_rr8}
bash tools/qwen_a0_safe/bench_rr8.sh "$OUT" 0; rc0=$?
echo "RR8_MUT0_RC=$rc0"
for m in 50 51 52 53 54 55; do
  bash tools/qwen_a0_safe/bench_rr8.sh "$OUT" $m > /dev/null 2>&1; rc=$?
  if grep -q 'A0_RR8_FAIL\|RR8_VS_RR7\|ROMLEAF_PARENT_NK_MISMATCH' "$OUT/run_$m.log"; then echo "RR8_MUT${m}=KILLED rc=$rc"; else echo "RR8_MUT${m}=SURVIVED rc=$rc"; fi
done
exit $rc0
