#!/bin/bash
set -euo pipefail
out="$PWD/out/outland"
for mut in 0 31 26; do
 if bash tools/qwen_a0_safe/bench_outland.sh "$out" "$mut"; then
  test "$mut" = 0 || { echo "A0_MUTANT_INEFFECTIVE $mut"; exit 1; }
 else
  test "$mut" != 0 || exit 1
  grep -Eq 'ROMLEAF_PARENT_NK_NATIVE_FAIL|ROMLEAF_PARENT_NK_MISMATCH' "$out/run_${mut}.log"
 fi
done
echo A0_OUTLAND_PROOF_PASS
