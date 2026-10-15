#!/bin/bash
set -euo pipefail
O=${1:?output}; MUT=${2:-0}; mkdir -p "$O"
iverilog -g2012 -s tb_store141 -Ptb_store141.MUT="$MUT" -o "$O/sim" physical/hcoll_seq612_1015/tb_store141.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
vvp -n "$O/sim"
