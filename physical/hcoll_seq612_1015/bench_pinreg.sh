#!/bin/bash
set -euo pipefail
O=${1:?output}; MUT=${2:-0}; mkdir -p "$O"
iverilog -g2012 -s tb_pinreg_store141 -Ptb_pinreg_store141.MUT="$MUT" -o "$O/sim" physical/hcoll_seq612_1015/tb_pinreg_store141.sv rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_static_pinreg_store.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
vvp -n "$O/sim"
