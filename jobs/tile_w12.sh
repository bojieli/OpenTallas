#!/bin/bash
# usage: jobs/tile_w12.sh <tag> <stages> [extra driver args...]
# Harden the Qwen O4 ROM tile element (rtl/hdc/ot_qwen_rom_tile_w12.sv) at the qwen3_budget clock
# 0.910216 ns with 60 ps setup uncertainty, real ROM/SRAM macro views.
set -o pipefail
TAG=$1; ST=$2; shift 2
M=physical/asap7_memory_macros
python3 tools/run_abi3_physical.py --view asap7 --top ot_qwen_rom_tile_w12 \
  --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_fp32_mul_pipe.sv --source rtl/hdc/ot_hdc_fpu.sv \
  --source rtl/proto/ot_fp32_add_rne_pipe.sv --source rtl/hdc/ot_hdc_sfu.sv --source rtl/hdc/ot_hdc_fastfp.sv \
  --source rtl/hdc/ot_hdc_matvec.sv --source rtl/hdc/ot_hdc_fp32_add_lat.sv --source rtl/hdc/ot_hdc_prefix.sv --source rtl/hdc/ot_qwen_w12_matvec.sv --source rtl/hdc/ot_qwen_w12_arith.sv --source rtl/hdc/ot_qwen_me_array_w12.sv --source rtl/hdc/ot_qwen_rom_tile_w12.sv \
  --source $M/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v \
  --source $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v \
  --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --stages $ST --corner TT --hold-corners WC,BC --keep-heavy-artifacts \
  --max-transition-ns --max-fanout 32 --macro-place-halo 4.32 2.16 \
  --macro-view ot_rom_4096x266_m8=$M/ot_rom_4096x266_m8 \
  --macro-view ot_sram_1r1w_128x256_m1_r2c2=$M/ot_sram_1r1w_128x256_m1_r2c2 \
  --nickname-tag w12_tile_$TAG --output results/physical_hdc/asap7/qwen_o4_w12/tile_$TAG/physical.json "$@"
