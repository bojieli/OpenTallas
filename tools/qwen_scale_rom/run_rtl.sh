#!/usr/bin/env bash
# Must run under ot-run; reuse the same immutable generated simulator for8ranks.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?output directory};images=${2:?native image directory};rank=${3:-0}
mkdir -p "$out"
files=("$root/tools/qwen_scale_rom/tb_scale_masks.sv" "$root/rtl/physical/ot_qwen_slab_port_group.sv" "$root/physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v")
sha256sum "${files[@]}" > "$out/source.sha256"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$v" --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
 --top-module tb_scale_masks --Mdir "$out/obj" "${files[@]}" > "$out/build.log" 2>&1
"$out/obj/Vtb_scale_masks" +OT_ROM_DIR="$images/rank$rank/masks" +EXPECTED="$images/rank$rank/expected_scale_words.hex" > "$out/rank$rank.log" 2>&1
cat "$out/rank$rank.log"
grep -q '^PASS released_scale_masks' "$out/rank$rank.log"
