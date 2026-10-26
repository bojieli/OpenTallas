#!/usr/bin/env bash
set -euo pipefail
out=${1:?out};mut=${2:-0};rows=${3:-1024};mkdir -p "$out"
iverilog -g2012 -s tb_hbm_host_static_ready_pin -Ptb_hbm_host_static_ready_pin.ROWS="$rows" -Ptb_hbm_host_static_ready_pin.READY_MUT="$mut" -o "$out/sim" rtl/hbm_accel/host_static_20261015/{ot_hbm_host_static_ingress,ot_hbm_program_block_ready,ot_hbm_program_block_ready_pin,tb_hbm_host_static_ready_pin}.sv rtl/hbm_accel/generic/vm/static/{ot_static_program_target,ot_vms_calendar_static}.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$out/build.log" 2>&1
vvp "$out/sim"
