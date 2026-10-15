#!/usr/bin/env bash
set -euo pipefail
OUT=$1; CASE=${2:-exact}
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
DEFS=()
if [[ "$CASE" == mutant ]]; then DEFS=(-DOT_XF_MUT); fi
iverilog -g2012 -s tb_qfd_io_xfifo "${DEFS[@]}" -o "$OUT/sim" \
 "$R/rtl/test/tb_qfd_io_xfifo.sv" "$R/rtl/physical/ot_qfd_io_xfifo.sv" \
 "$R/rtl/physical/ot_qwen_xfifo_slots.sv" "$R/rtl/physical/ot_qwen_coll_xfifo_native.sv" \
 "$R/rtl/physical/ot_qwen_die_coll_xfifo.sv" "$R/rtl/physical/ot_qwen_die_cdc_ch.sv" \
 "$R/rtl/physical/ot_qwen_async_fifo_w.sv" "$R/rtl/lib/ot_async_fifo.sv" \
 "$R/rtl/lib/ot_reset_sync.sv" "$R/rtl/lib/ot_hdly.sv" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w2c_256x517_m1/ot_sram_1r1w2c_256x517_m1.v" > "$OUT/build.log" 2>&1
vvp -n "$OUT/sim" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q '^PASS qfd_io_xfifo' "$OUT/run.log"
