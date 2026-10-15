#!/usr/bin/env bash
set -euo pipefail
# Execute this script through ot-run with admitted memory. Input root contains
# masks/ and expected/ from the locked released embedding image producer.
repo=$(cd "$(dirname "$0")/../../.." && pwd)
image_root=${1:?released image root}
build=${2:?separate build directory}
mkdir -p "$build"
verilator --binary --timing -Wno-fatal --top-module tb_embedding_static_tree -j 4 \
  --Mdir "$build/obj" \
  "$repo/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v" \
  "$repo/rtl/qwen_native/ot_qwen_embedding_static_bank.sv" \
  "$repo/rtl/qwen_native/ot_qwen_embedding_static_provider.sv" \
  "$repo/rtl/qwen_native/test/tb_embedding_static_tree.sv" >"$build/build.log" 2>&1
"$build/obj/Vtb_embedding_static_tree" +OT_ROM_DIR="$image_root/masks" +EXPECTED_DIR="$image_root/expected" >"$build/pass.log" 2>&1
if "$build/obj/Vtb_embedding_static_tree" +OT_ROM_DIR="$image_root/masks" +EXPECTED_DIR="$image_root/expected" +MUT=1 >"$build/mutant.log" 2>&1; then
  echo 'FAIL: payload mutant escaped';exit 1
fi
echo 'PASS tree exact and payload mutant rejected'
