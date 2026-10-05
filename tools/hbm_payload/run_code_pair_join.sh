#!/usr/bin/env bash
set -euo pipefail
out=$1
payload=$2
top=${3:-tb_hbm_qwen_code_pair_join}
mkdir -p "$out"
iverilog -g2012 -s "$top" -o "$out/sim" \
 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv \
 rtl/model_ready_hbm_r14/ot_hbm_r14_fifo2.sv rtl/hbm_accel/service/ot_hbm_accel_owned_crossing.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_payload_pair.sv \
 rtl/hbm_accel/integration/ot_hbm_qwen_code_leaf_map.sv \
 rtl/hbm_accel/integration/ot_hbm_qwen_code_span_read.sv \
 rtl/hbm_accel/integration/ot_hbm_qwen_code_pair_join.sv \
 rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_read_align.sv \
 rtl/test/hbm_accel/integration/tb_hbm_qwen_code_pair_join.sv \
 rtl/test/hbm_accel/integration/tb_hbm_qwen_code_tile_ports.sv > "$out/compile.log" 2>&1
vvp "$out/sim" +payload="$payload" > "$out/run.log" 2>&1
