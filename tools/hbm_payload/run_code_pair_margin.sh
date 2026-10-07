#!/usr/bin/env bash
# Exact gate: margin CODE pair vs unchanged context (Verilator; the original
# read pipeline does not elaborate in Icarus).
# Usage: run_code_pair_margin.sh OUT [-DMUTANT ...] -- [+NEG_UE|+NEG_DMR|+seed=N ...]
set -euo pipefail
out=$1; shift
defs=(); args=()
while [ $# -gt 0 ]; do if [ "$1" = "--" ]; then shift; args=("$@"); break; fi; defs+=("$1"); shift; done
mkdir -p "$out"
[ -f ~/.opentallas-env ] && source ~/.opentallas-env
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style ${defs[@]+"${defs[@]}"} \
 ${M2:+-GM2=$M2} --top-module tb_code_pair_margin --Mdir "$out/obj" \
 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_payload_pair_banklocal.sv \
 rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_read_pipeline.sv \
 physical/qwen_code_pair/ot_qwen_hbm_code_pair_context.sv \
 rtl/hbm_accel/qwen/payload/ot_qwen_hbm_code_pair_margin.sv \
 rtl/test/qwen_hbm_code_payload_leaf/tb_code_pair_margin.sv > "$out/compile.log" 2>&1
"$out/obj/Vtb_code_pair_margin" ${args[@]+"${args[@]}"} > "$out/run.log" 2>&1
