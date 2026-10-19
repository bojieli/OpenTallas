#!/bin/bash
set -euo pipefail
for mut in 0 28 29 26; do
  if bash tools/qwen_a0_safe/bench_copies.sh "$PWD/out/copies" "$mut"; then
    test "$mut" = 0 || { echo "A0_MUTANT_INEFFECTIVE $mut"; exit 1; }
  else
    test "$mut" != 0 || exit 1
    grep -Eq 'ROMLEAF_PARENT_NK_NATIVE_FAIL|ROMLEAF_PARENT_NK_MISMATCH' "out/copies/run_${mut}.log"
  fi
done
echo A0_COPIES_PROOF_PASS
