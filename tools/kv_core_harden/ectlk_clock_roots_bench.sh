#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
OUT=$(mkdir -p "$1" && cd "$1" && pwd)
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
for c in nominal mutant;do
 mkdir -p "$OUT/$c/obj";d=();[ "$c" = mutant ] && d=(-DKVG3_ECTLK_CKMUT)
 verilator --binary -j 8 --timing -Wno-fatal -Wno-lint -Wno-style --top-module tb_ectlk_clock_roots "${d[@]}" \
  -Mdir "$OUT/$c/obj" -o Vtb "$R/rtl/test/kv_core_harden/tb_ectlk_clock_roots.sv" > "$OUT/$c/build.log" 2>&1
 "$OUT/$c/obj/Vtb" > "$OUT/$c/run.log" 2>&1
 grep -E '^(PASS|FAIL)' "$OUT/$c/run.log"
done
grep -q '^PASS ectlk_clock_roots' "$OUT/nominal/run.log"
grep -q '^FAIL ectlk_clock_roots' "$OUT/mutant/run.log"
