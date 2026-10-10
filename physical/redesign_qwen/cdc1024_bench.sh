#!/bin/bash
# redesign-qwen 2026-10-10: one 1,024-b CDC tile (ot_qwen_die_cdc_ch) on tb_qwen_die_cdc_ch (random sends, slow / fast reader).
#   cdc1024_bench.sh pos|neg OUT [iverilog -P overrides...]  pos -> CDC1024_PASS ; neg (NEG 1: credit violation) -> CDC1024_NEG_DETECTED (rc 1)
set -u
m=$1; o=$2; shift 2; mkdir -p "$o"
S=(rtl/test/tb_qwen_die_cdc_ch.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/physical/ot_qwen_async_fifo_w.sv rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv)
n=$([ $m = neg ] && echo 1 || echo 0)
iverilog -g2012 -o "$o/t.vvp" -Ptb_qwen_die_cdc_ch.W=1024 -Ptb_qwen_die_cdc_ch.NEG=$n "$@" "${S[@]}" > "$o/build.log" 2>&1 || { echo BUILD_FAIL; exit 2; }
vvp -n "$o/t.vvp" > "$o/run.log" 2>&1
if [ $m = pos ]; then grep -q '^PASS cdc_ch' "$o/run.log" && { echo CDC1024_PASS; exit 0; }; echo CDC1024_FAIL; exit 1; fi
grep -q '^PASS cdc_ch' "$o/run.log" && { echo CDC1024_NEG_MISSED; exit 0; }; echo CDC1024_NEG_DETECTED; exit 1
