#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?output directory};mkdir -p "$out"
files=("$root/tools/qwen_code_rom/tb_code_pair.sv" "$root/rtl/physical/ot_qwen_tile_rpair.sv" "$root/rtl/hdc/ot_qwen_rom_tile_w12.sv" "$root/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v")
sha256sum "${files[@]}" > "$out/source.sha256"
"${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}" --binary --timing -O1 -j 4 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_code_pair --Mdir "$out/obj" "${files[@]}" > "$out/build.log" 2>&1
echo PASS_actual_hardened_code_pair_build
