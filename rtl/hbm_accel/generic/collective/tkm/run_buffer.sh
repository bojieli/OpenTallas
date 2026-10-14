#!/bin/bash
set -eu
cd "$(dirname "$0")/../../../../.."
out=$(realpath -m "$1");mkdir -p "$out"
iverilog -g2012 -s tb_hgi_coll_tkm_buffer -Ptb_hgi_coll_tkm_buffer.MUT="${2:-0}" -o "$out/sim" rtl/hbm_accel/generic/collective/tkm/tb_hgi_coll_tkm_buffer.sv rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_buffer.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
vvp "$out/sim"
