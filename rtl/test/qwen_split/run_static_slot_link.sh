#!/bin/bash
set -eu
OUT=$1;shift
W=$(cd "$(dirname "$0")/../.." && pwd)
P=$(cd "$W/.." && pwd)
mkdir -p "$OUT"
SRC=("$W/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv" "$W/test/qwen_split/tb_qwen_static_slot_link.sv" "$W/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv" "$W/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" "$P/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v")
sha256sum "${SRC[@]}" > "$OUT/source.sha256"
iverilog -g2012 -DOT_MEM_NO_INIT -s tb_qwen_static_slot_link "$@" -o "$OUT/tb.vvp" "${SRC[@]}" > "$OUT/build.log" 2>&1 || { head -30 "$OUT/build.log";exit 2; }
vvp -n "$OUT/tb.vvp" > "$OUT/run.log" 2>&1
grep 'STATIC_SLOT_' "$OUT/run.log"
