#!/bin/bash
set -u
OUT=$1; CASE=$2
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
define=""; params=""
case "$CASE" in
  exact) ;;
  meta_exact) params="-Ptb_qfd_coll_xfifo_native59.META=1 -Ptb_qfd_coll_xfifo_native59.M=512" ;;
  data_mutant) define=-DOT_NCOLL_NATIVE59_MUT ;;
  reservation_mutant) define=-DOT_NCOLL_MUT_NOREFUND_CHECK ;;


  narrow_rr_mutant) define=-DOT_NCOLL_MUT_NARROW_RR ;;
  *) exit 2 ;;
esac
iverilog -g2012 -s tb_qfd_coll_xfifo_native59 $define $params -o "$OUT/sim" \
 "$R/rtl/test/tb_qfd_coll_xfifo_native59.sv" "$R/rtl/physical/ot_qwen_coll_xfifo_native59.sv" \
 "$R/rtl/physical/ot_qwen_die_coll_xfifo.sv" "$R/rtl/physical/ot_qwen_die_cdc_ch.sv" \
 "$R/rtl/physical/ot_qwen_async_fifo_w.sv" "$R/rtl/lib/ot_async_fifo.sv" \
 "$R/rtl/lib/ot_reset_sync.sv" "$R/rtl/lib/ot_hdly.sv" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" \
 "$R/physical/asap7_memory_macros/ot_sram_1r1w2c_256x517_m1/ot_sram_1r1w2c_256x517_m1.v" \
 > "$OUT/build.log" 2>&1 || { cat "$OUT/build.log"; echo "FAIL native_coll_port build";exit 2; }
vvp -n "$OUT/sim" > "$OUT/run.log" 2>&1
line=$(grep -E '^(PASS|FAIL) native_coll_port' "$OUT/run.log" | tail -1)
echo "$line"
case "$line" in PASS*)exit 0;; FAIL*)exit 1;; *)tail -8 "$OUT/run.log";exit 2;;esac
