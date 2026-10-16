#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory};mkdir -p "$out"
iverilog -g2012 -s tb_s81_hc_bank128 -o "$out/mut.vvp" \
 rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ccf_bankpipe.sv \
 rtl/dsrom_sys/s81_suhc/static/ot_s81_hc_ccf_bankpipe128.sv \
 rtl/link/ot_fifo_sram_fwft.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
 rtl/dsrom_sys/s81_suhc/test/tb_s81_hc_bank128.sv
exec vvp "$out/mut.vvp" +STOP=1
