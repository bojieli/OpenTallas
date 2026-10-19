#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
for ne in 64 32 16; do
 mkdir -p "synth$ne"
 yosys -Q -p "read_verilog -sv -lib physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1_bb.v; read_verilog -sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_sram.sv; hierarchy -top ot_qwen_d2d_cal_sram -chparam NE $ne; synth -top ot_qwen_d2d_cal_sram -noabc; write_json synth$ne/netlist.json; stat" > "synth$ne/yosys.log" 2>&1
 tail -25 "synth$ne/yosys.log"
done
