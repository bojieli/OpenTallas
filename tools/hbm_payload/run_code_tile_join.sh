#!/usr/bin/env bash
set -euo pipefail
out=$1
payload=$2
extra=${3:-0}
mkdir -p "$out"
source ~/.opentallas-env
verilator --binary --timing -j 16 -Wno-fatal --top-module tb_hbm_qwen_code_tile_join \
 -GEXTRA="$extra" --Mdir "$out/obj" -Irtl/hdc -Irtl/isa \
 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv \
 rtl/model_ready_hbm_r14/ot_hbm_r14_fifo2.sv rtl/hbm_accel/service/ot_hbm_accel_owned_crossing.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_payload_pair.sv \
 rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_read_pipeline.sv \
 rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_read_align.sv \
 rtl/hbm_accel/integration/ot_hbm_qwen_code_leaf_map.sv \
 rtl/hbm_accel/integration/ot_hbm_qwen_code_span_read.sv \
 rtl/hbm_accel/integration/ot_hbm_qwen_code_pair_join.sv \
 rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fastfp.sv \
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_matvec.sv \
 rtl/hdc/ot_qwen_me_array_w12.sv rtl/hdc/ot_qwen_rom_tile_w12.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 rtl/hdc/ot_qwen_w12_matvec.sv rtl/hdc/ot_qwen_w12_arith.sv \
 rtl/proto/ot_fp32_add_rne_pipe.sv \
 rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_tile_logic_w12.sv \
 rtl/test/hbm_accel/integration/tb_hbm_qwen_code_tile_join.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_hbm_qwen_code_tile_join" +payload="$payload" > "$out/run.log" 2>&1
