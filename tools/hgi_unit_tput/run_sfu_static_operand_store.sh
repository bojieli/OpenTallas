#!/bin/bash
set -euo pipefail
mkdir -p "$OUT"
M=physical/asap7_memory_macros
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O1 -j 4 -CFLAGS -O0 -Wno-fatal --top-module tb_hgi_sfu_static_operand_store --Mdir "$OUT/obj" \
 rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_operand_store.sv rtl/test/hbm_accel/generic/tb_hgi_sfu_static_operand_store.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv \
 "$M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" \
 "$M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v" \
 "$M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" > "$OUT/build.log" 2>&1
"$OUT/obj/Vtb_hgi_sfu_static_operand_store" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
set +e
"$OUT/obj/Vtb_hgi_sfu_static_operand_store" +MUT_ADDR > "$OUT/mutant.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -q STORE_WORD "$OUT/mutant.log";then cat "$OUT/mutant.log";exit 1;fi
printf 'PASS actual bank-address mutant rc=%s\n' "$rc"

set +e
"$OUT/obj/Vtb_hgi_sfu_static_operand_store" +MUT_SCALAR_ADDR > "$OUT/scalar_mutant.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -q SCALAR_IDENTITY "$OUT/scalar_mutant.log";then cat "$OUT/scalar_mutant.log";exit 1;fi
printf 'PASS actual scalar-address identity mutant rc=%s\n' "$rc"

set +e
"$OUT/obj/Vtb_hgi_sfu_static_operand_store" +MUT_RANGE > "$OUT/range_mutant.log" 2>&1
rc=$?
set -e
if [ "$rc" = 0 ] || ! grep -q STORE_FAULT "$OUT/range_mutant.log";then cat "$OUT/range_mutant.log";exit 1;fi
printf 'PASS actual high-address alias refusal mutant rc=%s\n' "$rc"
