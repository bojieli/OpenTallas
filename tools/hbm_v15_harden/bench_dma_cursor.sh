#!/usr/bin/env bash
set -euo pipefail
out=${1:?output};mut=${2:-0};mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
cp "$d/ot_hgi_dma_back_static_cursor.sv" "$out/cursor.sv"
if [ "$mut" = 1 ];then sed -i "s/drain_row_hbm+37'(hbm_stride)/drain_row_hbm+37'(hbm_stride)+37'd256/g" "$out/cursor.sv";! cmp -s "$out/cursor.sv" "$d/ot_hgi_dma_back_static_cursor.sv";fi
iverilog -g2012 -s tb_dma_back_cursor_equiv -o "$out/eq.vvp" "$m" "$d/ot_hgi_dma_back_static.sv" "$out/cursor.sv" "$d/tb_dma_back_cursor_equiv.sv"
vvp "$out/eq.vvp" > "$out/eq.log" 2>&1 || { cat "$out/eq.log";exit 1; };cat "$out/eq.log";grep -q 'DMA_CURSOR_EQUIV PASS' "$out/eq.log"
# Run the unchanged actual four-quadrant VM/SRAM production bench against the cursor implementation.
sed 's/module ot_hgi_dma_back_static_cursor/module ot_hgi_dma_back_static/' "$out/cursor.sv" > "$out/as_back.sv"
mr=physical/asap7_memory_macros
iverilog -g2012 -s tb_dma_back_static -o "$out/production.vvp" "$out/as_back.sv" "$d/ot_hgi_b2_swap_disp_static.sv" "$d/ot_hgi_b2_swap_grp_static.sv" rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv "$mr/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v" "$mr/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" "$d/tb_dma_back_static.sv"
vvp "$out/production.vvp" > "$out/production.log" 2>&1 || { cat "$out/production.log";exit 1; };cat "$out/production.log";grep -q 'PASS DMA static actual production' "$out/production.log"
echo DMA_CURSOR_BENCH_PASS
