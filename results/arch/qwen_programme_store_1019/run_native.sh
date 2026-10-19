#!/usr/bin/env bash
set -euo pipefail
# Run through ot-run from this lane's native_all36 directory. No host pin.
lane_dir=$(cd .. && pwd)
src_dir=$lane_dir/src
python3 "$src_dir/tools/qwen_layerbench/programme_store.py" --manifest table_manifest.json --out images
python3 "$src_dir/tools/qwen_layerbench/table_rom_native_fixture.py" --manifest table_manifest.json --images images --out fixture
vbin=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vbin" --version > "$lane_dir/runs/verilator.version"
"$vbin" --binary --timing -Wno-fatal -j 8 --top-module tb_qfd_dv_table_rom_loader \
    -Mdir "$lane_dir/runs/native_obj" \
    "$src_dir/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v" \
    "$src_dir/rtl/qwen_dv/qfd_dv_table_rom_loader.sv" \
    "$src_dir/rtl/test/qwen_dv/tb_qfd_dv_table_rom_loader.sv" > "$lane_dir/runs/native_build.log" 2>&1
bench=$lane_dir/runs/native_obj/Vtb_qfd_dv_table_rom_loader
for sid in $(seq 0 11); do
    "$bench" "+OT_ROM_DIR=$PWD/fixture/s$sid" "+EXPECTED=$PWD/fixture/s$sid/expected.hex" +MUT=0 > "$lane_dir/runs/native_s$sid.log" 2>&1
    grep TABLE_ROM_NATIVE_PASS "$lane_dir/runs/native_s$sid.log"
done
for fault_case in 1 2; do
    "$bench" "+OT_ROM_DIR=$PWD/fixture/s0" "+EXPECTED=$PWD/fixture/s0/expected.hex" +MUT=0 "+FAULT_CASE=$fault_case" > "$lane_dir/runs/fault$fault_case.log" 2>&1
    grep REJECT_PASS "$lane_dir/runs/fault$fault_case.log"
done
for mut in 1 2 3 4; do
    set +e
    "$bench" "+OT_ROM_DIR=$PWD/fixture/s0" "+EXPECTED=$PWD/fixture/s0/expected.hex" "+MUT=$mut" > "$lane_dir/runs/mut$mut.log" 2>&1
    witness_rc=$?
    set -e
    if test "$witness_rc" = 0;then echo "MUTANT_UNEXPECTED_PASS $mut";exit 1;fi
    grep TABLE_ROM_MISMATCH "$lane_dir/runs/mut$mut.log"
done
echo ALL36_ALL12_ALL4_ROM_LOADER_PASS
