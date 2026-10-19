#!/usr/bin/env bash
set -euo pipefail
lane_dir=$(cd .. && pwd)
src_dir=$lane_dir/src
python3 - <<'PY'
import json
old=json.load(open('table_manifest.json'))
new=json.load(open('final_manifest/table_manifest.json'))
assert old['stages']==new['stages'], 'Payload changed since native fixture generation'
print('FINAL_MANIFEST_PAYLOAD_IDENTICAL')
PY
sha256sum "$src_dir/rtl/qwen_dv/qfd_dv_table_rom_loader.sv" "$src_dir/rtl/qwen_dv/qfd_dv_vm.sv" \
    "$src_dir/rtl/test/qwen_dv/tb_qfd_dv_table_store_join.sv" > "$lane_dir/runs/native_join.sources"
vbin=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vbin" --binary --timing -Wno-fatal -j 8 --top-module tb_qfd_dv_table_store_join \
    -Mdir "$lane_dir/runs/native_join_obj" \
    "$src_dir/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v" \
    "$src_dir/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" \
    "$src_dir/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" \
    "$src_dir/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v" \
    "$src_dir/rtl/qwen_dv/qfd_dv_vm.sv" "$src_dir/rtl/qwen_dv/qfd_dv_table_rom_loader.sv" \
    "$src_dir/rtl/test/qwen_dv/tb_qfd_dv_table_store_join.sv" > "$lane_dir/runs/native_join_build.log" 2>&1
bench=$lane_dir/runs/native_join_obj/Vtb_qfd_dv_table_store_join
for sid in $(seq 0 11); do
    "$bench" "+OT_ROM_DIR=$PWD/fixture/s$sid" "+EXPECTED=$PWD/fixture/s$sid/expected.hex" > "$lane_dir/runs/join_s$sid.log" 2>&1
    grep TABLE_STORE_NATIVE_JOIN_PASS "$lane_dir/runs/join_s$sid.log"
done
echo ALL36_ALL12_ALL4_MUTABLE_TABLE_RETENTION_PASS
