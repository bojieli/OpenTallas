#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../../.." && pwd)
OUT=$(realpath -m "$1")
mkdir -p "$OUT"
cd "$ROOT"
VL=${VERILATOR:-verilator}
MACRO=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
TB=rtl/hbm_accel/generic/adapters/static_su/lbank_native/tb_lbank_native.sv
BANK=rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv
"$VL" --binary --timing -j 1 -Wno-fatal --top-module tb_lbank_native -Mdir "$OUT/obj" "$BANK" "$MACRO" "$TB" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_lbank_native" > "$OUT/exact.log" 2>&1
set +e
"$OUT/obj/Vtb_lbank_native" +MUT_ADDR > "$OUT/address_mutant.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -q 'LBANK_NATIVE FAIL' "$OUT/address_mutant.log"; then exit 1; fi
printf '%s\n' "$rc" > "$OUT/address_mutant.exit"
"$VL" --binary --timing -j 1 -Wno-fatal --top-module tb_lbank_native -GRB=8 -Mdir "$OUT/unsupported_obj" "$BANK" "$MACRO" "$TB" > "$OUT/unsupported_build.log" 2>&1
set +e
"$OUT/unsupported_obj/Vtb_lbank_native" > "$OUT/unsupported.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -q 'unsupported MACRO=1 RB=8' "$OUT/unsupported.log"; then exit 1; fi
printf '%s\n' "$rc" > "$OUT/unsupported.exit"
printf '%s\n' 'LBANK_NATIVE SUITE PASS'
