#!/bin/bash
# usage: qwen_tile_r5_node_bench.sh OUTDIR BMUT   (q13 spec r5 leaf 2 boundary bench; prints the bench's PASS/FAIL line)
set -u; OUT=$1; BM=${2:-0}; R=$(cd "$(dirname "$0")/.." && pwd)
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; command -v "$V" >/dev/null || V=verilator
mkdir -p "$OUT"
"$V" --binary --timing -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -CFLAGS -O1 --x-assign fast --x-initial fast \
  --top-module tb_qwen_tile_r5_node -GBMUT=$BM --Mdir "$OUT/obj" \
  $R/rtl/test/tb_qwen_tile_r5_node.sv $R/rtl/hdc/ot_qwen_rom_tile_w12.sv $R/rtl/physical/ot_qwen_tile_node.sv \
  $R/rtl/physical/ot_qwen_tile_lsl.sv $R/rtl/hdc/ot_qwen_me_array_w12.sv $R/rtl/hdc/ot_hdc_fpu.sv \
  $R/rtl/hdc/ot_hdc_fp32_mul_pipe.sv $R/rtl/hdc/ot_hdc_fastfp.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/hdc/ot_hdc_sfu.sv \
  $R/rtl/hdc/ot_hdc_matvec.sv $R/rtl/hdc/ot_hdc_fp32_add_lat.sv $R/rtl/hdc/ot_hdc_fp32_mul_lat.sv $R/rtl/hdc/ot_hdc_prefix.sv \
  $R/rtl/hdc/ot_qwen_w12_matvec.sv $R/rtl/hdc/ot_qwen_w12_arith.sv $R/rtl/proto/ot_fp32_add_rne_pipe.sv \
  $R/rtl/hdc/ot_hdc_fp32_add_lat_nr.sv $R/rtl/lib/ot_rst_relay.sv > "$OUT/build.log" 2>&1 || { echo "FAIL tile_r5_node build"; tail -5 "$OUT/build.log"; exit 2; }
"$OUT/obj/Vtb_qwen_tile_r5_node" > "$OUT/sim.log" 2>&1
grep -E '^(PASS|FAIL)' "$OUT/sim.log" | tail -3
grep -q '^PASS tile_r5_node' "$OUT/sim.log"
