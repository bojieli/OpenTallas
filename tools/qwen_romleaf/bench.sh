#!/bin/bash
set -euo pipefail
OUT=$(mkdir -p "$1" && realpath "$1")
MUT=${2:-0}
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
DEFINES=()
if [[ "$MUT" == 1 ]]; then DEFINES+=(-DOT_ROMLEAF_LATENCY_MUTANT); fi
OUT="$OUT/m$MUT"
mkdir -p "$OUT"
SOURCES=(rtl/test/tb_qwen_romleaf_1552.sv rtl/physical/ot_qwen_tile_romleaf.sv rtl/hdc/ot_qwen_rom_tile_w12.sv rtl/hdc/ot_hdc_delay.sv physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v)
HASH=$(sha256sum "${SOURCES[@]}" "$0" | sha256sum | cut -d' ' -f1)
if [[ ! -f "$OUT/build.sha256" || $(cat "$OUT/build.sha256") != "$HASH" ]]; then
 "$V" --binary --timing -j 4 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_qwen_romleaf_1552 -Mdir "$OUT/obj" "${DEFINES[@]}" "${SOURCES[@]}" > "$OUT/build.log" 2>&1
 printf '%s\n' "$HASH" > "$OUT/build.sha256"
fi
"$OUT/obj/Vtb_qwen_romleaf_1552" +MUT="$MUT" | tee "$OUT/run_$MUT.log"
grep -q '^ROMLEAF_PASS ' "$OUT/run_$MUT.log"
