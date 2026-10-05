#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
iverilog -g2012 -s tb_code_payload_pair -o "$out/sim" \
 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_payload_pair.sv \
 rtl/test/qwen_hbm_code_payload_leaf/tb_code_payload_pair.sv > "$out/compile.log" 2>&1
vvp "$out/sim" > "$out/run.log" 2>&1
rg -q '^PASS_CODE_PAYLOAD_PAIR ' "$out/run.log"
