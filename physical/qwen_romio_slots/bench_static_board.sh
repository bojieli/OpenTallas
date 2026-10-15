#!/usr/bin/env bash
set -euo pipefail
OUT=$1; MUT=${2:-0}
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
iverilog -g2012 -DOT_MEM_NO_INIT -s tb_qfd_serdes_static -Ptb_qfd_serdes_static.MUT="$MUT" -o "$OUT/sim" \
 "$R/rtl/test/tb_qfd_serdes_static.sv" "$R/rtl/physical/ot_qfd_io_links_static.sv" \
 "$R/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv" "$R/rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv" \
 "$R/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv" \
 "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" > "$OUT/build.log" 2>&1
vvp -n "$OUT/sim" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q '^STATIC_BOARD_PASS' "$OUT/run.log"
