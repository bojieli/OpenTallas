#!/bin/bash
set -eu
cd "$(dirname "$0")/../../.."
out=$(realpath -m "$1");mkdir -p "$out"
iverilog -g2012 -s tb_hcoll_operand_column512 -Ptb_hcoll_operand_column512.MUT="${2:-0}" -o "$out/sim" rtl/hbm_accel/tu/tb_hcoll_operand_column512.sv rtl/hbm_accel/tu/ot_hcoll_operand_column512.sv rtl/lib/ot_rst_relay.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv
vvp "$out/sim"
