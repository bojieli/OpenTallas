#!/bin/bash
set -euo pipefail
out="${A0_COPY_OUT:-$PWD/out/copies_r2}"
for mut in 0 28 29 26 30; do
  if bash tools/qwen_a0_safe/bench_copies.sh "$out" "$mut"; then
    test "$mut" = 0 || { echo "A0_MUTANT_INEFFECTIVE $mut"; exit 1; }
  else
    test "$mut" != 0 || exit 1
    grep -Eq 'ROMLEAF_PARENT_NK_NATIVE_FAIL|ROMLEAF_PARENT_NK_MISMATCH' "$out/run_${mut}.log"
  fi
done
echo A0_COPIES_PROOF_PASS
