#!/bin/bash
# QW-CLUSTER3/A0 REGROOT 6: full 64-MAC / ten-ROM native numerical bench (positive) + missing-copy mutants 40/41/42 and
# the REGROOT 5 output-landing mutant 31.  Every mutant must FAIL with a mismatch / native-fail marker.
set -uo pipefail
out="$PWD/out/rr6"
for mut in 0 40 41 42 31; do
 if bash tools/qwen_a0_safe/bench_rr6.sh "$out" "$mut"; then
  test "$mut" = 0 || { echo "A0_RR6_MUTANT_INEFFECTIVE $mut"; exit 1; }
 else
  test "$mut" != 0 || { echo "A0_RR6_POSITIVE_FAIL"; exit 1; }
  grep -Eq 'ROMLEAF_PARENT_NK_NATIVE_FAIL|ROMLEAF_PARENT_NK_MISMATCH' "$out/run_${mut}.log" || { echo "A0_RR6_MUTANT_NO_MARKER $mut"; exit 1; }
 fi
done
echo A0_RR6_PROOF_PASS
