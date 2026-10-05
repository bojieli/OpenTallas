#!/usr/bin/env bash
# Remote only. New component lockstep; original live sources/binaries untouched.
set -uo pipefail
out=$1
mkdir "$out" || exit 3
git rev-parse HEAD > "$out/source_commit.txt"
verilator --binary --timing -Wno-fatal -O3 -j 16 \
  --top-module tb_qwen_kv_land_merge_preplaced \
  --Mdir "$out/obj" \
  rtl/hdc/kv/ot_qwen_kv_land_merge.sv \
  rtl/hdc/kv/ot_qwen_kv_land_merge_preplaced.sv \
  rtl/test/qwen_rom_runtime/realmem/tb_qwen_kv_land_merge_preplaced.sv \
  > "$out/build.log" 2>&1
rc=$?; echo "$rc" > "$out/build.exit"
if [ "$rc" != 0 ]; then exit "$rc"; fi
for seed in 1 2 3 4; do
  "$out/obj/Vtb_qwen_kv_land_merge_preplaced" +verilator+seed+$seed > "$out/seed_$seed.log" 2>&1
  rc=$?; echo "$rc" > "$out/seed_$seed.exit"
  if [ "$rc" != 0 ] || ! grep -q 'LAND_MERGE_LOCKSTEP PASS.*mismatches=0' "$out/seed_$seed.log" || grep -qE 'MISMATCH|FAIL|Error' "$out/seed_$seed.log"; then exit 86; fi
done
