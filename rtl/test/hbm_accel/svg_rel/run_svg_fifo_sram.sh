#!/usr/bin/env bash
set -eu
out=$1;mut=${2:-0};wp=${3:-512};rp=${4:-417};phase=${5:-17};mkdir -p "$out"
iverilog -g2012 -s tb_svg_fifo_sram -Ptb_svg_fifo_sram.MUT="$mut" -Ptb_svg_fifo_sram.WP="$wp" -Ptb_svg_fifo_sram.RP="$rp" -Ptb_svg_fifo_sram.PHASE="$phase" -o "$out/tb.vvp" \
 rtl/lib/ot_reset_sync.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo.sv \
 rtl/hbm_accel/loader/service_native/ot_hbm_svc_async_fifo_sram285.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_8x285_m1/ot_sram_1r1w2c_8x285_m1.v \
 rtl/test/hbm_accel/svg_rel/tb_svg_fifo_sram.sv
vvp "$out/tb.vvp"
