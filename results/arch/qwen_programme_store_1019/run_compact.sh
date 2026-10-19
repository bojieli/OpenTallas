#!/usr/bin/env bash
set -euo pipefail
lane_dir=$(cd .. && pwd)
src_dir=$lane_dir/src
work_dir=$PWD/compact
run_dir=$lane_dir/runs/compact
mkdir -p "$work_dir" "$run_dir"
python3 "$src_dir/tools/qwen_layerbench/emit_table_manifest.py" \
  --lowering-root /srv/opentallas-scratch/claude/qw-clayer2/src \
  --prepared /srv/opentallas-scratch/claude/tokpass-qwen-1018/fx/prep/tp4 \
  --native-images /srv/opentallas-scratch/claude/tokpass-qwen-1018/fx/realmem_tp8/stage/img \
  --checkpoint-lock "$src_dir/compiler/models/qwen3-8b/checkpoint_source.json" \
  --global-boundary-program /srv/opentallas-scratch/claude/qw-clayer2/src/results/arch/qwen_tp8_native_dispatch_1014/actual_fused_layer0/die0/program.hex \
  --compact-btab --out "$work_dir" > "$run_dir/emit.log"
python3 "$src_dir/tools/qwen_layerbench/programme_store.py" --manifest "$work_dir/table_manifest.json" --out "$work_dir/images"
python3 "$src_dir/tools/qwen_layerbench/table_rom_native_fixture.py" --manifest "$work_dir/table_manifest.json" --images "$work_dir/images" --out "$work_dir/fixture"
sha256sum "$src_dir/rtl/qwen_dv/qfd_dv_table_rom_loader.sv" "$src_dir/rtl/qwen_dv/qfd_dv_vm.sv" \
 "$src_dir/rtl/test/qwen_dv/tb_qfd_dv_table_rom_loader.sv" "$src_dir/rtl/test/qwen_dv/tb_qfd_dv_table_store_join.sv" > "$run_dir/sources.sha256"
vbin=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vbin" --version > "$run_dir/verilator.version"
for top in tb_qfd_dv_table_rom_loader tb_qfd_dv_table_store_join;do
 sources=("$src_dir/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v" \
  "$src_dir/rtl/qwen_dv/qfd_dv_table_rom_loader.sv" "$src_dir/rtl/test/qwen_dv/$top.sv")
 if test "$top" = tb_qfd_dv_table_store_join;then
  sources+=("$src_dir/rtl/qwen_dv/qfd_dv_vm.sv")
  for macro in ot_sram_1r1w_1024x256_m2_r2c2 ot_sram_1r1w_128x256_m1_r2c2 ot_sram_1r1w_256x256_m2_r2c2;do
   sources+=("$src_dir/physical/asap7_memory_macros/$macro/$macro.v")
  done
 fi
 "$vbin" --binary --timing -Wno-fatal -j 8 --top-module "$top" -GBTAB_COMPACT=1 \
  -Mdir "$run_dir/obj_$top" "${sources[@]}" > "$run_dir/build_$top.log" 2>&1
 bench=$run_dir/obj_$top/V$top
 for sid in $(seq 0 11);do
  "$bench" "+OT_ROM_DIR=$work_dir/fixture/s$sid" "+EXPECTED=$work_dir/fixture/s$sid/expected.hex" \
   > "$run_dir/${top}_s$sid.log" 2>&1
  grep PASS "$run_dir/${top}_s$sid.log"
 done
 if test "$top" = tb_qfd_dv_table_rom_loader;then
  for mut in 1 2 3 4;do
   set +e
   "$bench" "+OT_ROM_DIR=$work_dir/fixture/s0" "+EXPECTED=$work_dir/fixture/s0/expected.hex" "+MUT=$mut" > "$run_dir/mut$mut.log" 2>&1
   witness_rc=$?
   set -e
   test "$witness_rc" != 0
   grep TABLE_ROM_MISMATCH "$run_dir/mut$mut.log"
  done
  for fault_case in 1 2;do
   "$bench" "+OT_ROM_DIR=$work_dir/fixture/s0" "+EXPECTED=$work_dir/fixture/s0/expected.hex" "+FAULT_CASE=$fault_case" > "$run_dir/fault$fault_case.log" 2>&1
   grep REJECT_PASS "$run_dir/fault$fault_case.log"
  done
 fi
done
echo COMPACT_BTABLE488_OF512_ALL36_ALL12_ALL4_PASS
