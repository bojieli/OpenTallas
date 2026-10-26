#!/usr/bin/env bash
# ot_hgi_dma_back_static exact bench (production + guards + calendar wrap), or one RTL mutant
# (MUT=1 wrong destination sector, MUT=2 premature source retire) -- HBM-V15-HARDEN 10-15
set -euo pipefail
out=${1:?out}; mut=${2:-0}; mkdir -p "$out"
d=rtl/hbm_accel/generic/peers/static
mr=physical/asap7_memory_macros
iverilog -g2012 -s tb_dma_back_static -Ptb_dma_back_static.MUT="$mut" -o "$out/back.vvp" $d/ot_hgi_dma_back_static.sv $d/ot_hgi_b2_swap_disp_static.sv $d/ot_hgi_b2_swap_grp_static.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv $mr/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v $mr/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $d/tb_dma_back_static.sv
vvp "$out/back.vvp" > "$out/back.log" 2>&1 || { cat "$out/back.log"; exit 1; }
cat "$out/back.log"
if [ "$mut" = 0 ]; then
  iverilog -g2012 -s tb_dma_back_static_guards -o "$out/guards.vvp" $d/ot_hgi_dma_back_static.sv $mr/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $d/tb_dma_back_static_guards.sv
  vvp "$out/guards.vvp" | tee "$out/guards.log"
  iverilog -g2012 -s tb_dma_calendar_wrap -o "$out/wrap.vvp" $d/ot_hgi_dma_back_static.sv $mr/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $d/tb_dma_calendar_wrap.sv
  vvp "$out/wrap.vvp" | tee "$out/wrap.log"
  ! grep -qi 'fatal\|error\|FAIL' "$out/guards.log" "$out/wrap.log"
fi
echo "DMA_BACK_STATIC_BENCH_DONE mut=$mut"
