#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../../.." && pwd)
OUT=$(realpath -m "$1")
mkdir -p "$OUT"
cd "$ROOT"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -j 2 --top-module tb_bfqg --Mdir "$OUT/obj" \
  rtl/lib/ot_rst_relay.sv rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_bfqg.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  rtl/hbm_accel/generic/adapters/tb/bfqg/reference.sv \
  rtl/hbm_accel/generic/adapters/tb/bfqg/tb_bfqg.sv > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_bfqg" > "$OUT/positive.log" 2>&1
grep 'BFQG_PASS' "$OUT/positive.log"
for mutant in {0..9}; do
  if "$OUT/obj/Vtb_bfqg" +MUT="$mutant" > "$OUT/mutant-$mutant.log" 2>&1; then
    echo "BFQG_MUTANT_SURVIVED $mutant";exit 1
  fi
  grep 'BFQG_FAIL' "$OUT/mutant-$mutant.log"
done
echo 'BFQG_SUITE_PASS positive=1 rejected_mutants=10'
