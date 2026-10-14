#!/bin/bash
set -eu
cd "$(dirname "$0")/../../.."
out=$(realpath -m "$1");mkdir -p "$out"
iverilog -g2012 -s tb_hcoll_operand_column512 -Ptb_hcoll_operand_column512.MUT="${2:-0}" -o "$out/sim" rtl/hbm_accel/tu/tb_hcoll_operand_column512.sv rtl/hbm_accel/tu/ot_hcoll_operand_column512.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
vvp "$out/sim"
