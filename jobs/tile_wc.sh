#!/bin/bash
# usage: jobs/tile_wc.sh <tag> <stages> [extra driver args...]
# The Qwen O4 ROM tile element (rtl/hdc/ot_qwen_rom_tile.sv) for 1.2 GHz sign-off (AGENTS.md, 2026-09-30):
# 0.833 ns, 60 ps setup / 25 ps hold, synthesised and optimised at ORFS CORNER=WC (SS) with the Kogge-Stone
# adder map (ADDER_MAP_FILE empty) and the keep-prefix ot_hdc_ksa, hold repaired at WC and BC; the matrix
# engine's FP32 adds at LAT 7 (ACC_LAT, TREE_LAT: root 2026-09-30, +54 cycles an ME op).
set -o pipefail
TAG=$1; ST=$2; shift 2
M=physical/asap7_memory_macros
python3 tools/run_abi3_physical.py --view asap7 --top ot_qwen_rom_tile \
  --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_fp32_mul_pipe.sv --source rtl/hdc/ot_hdc_fpu.sv \
  --source rtl/proto/ot_fp32_add_rne_pipe.sv --source rtl/hdc/ot_hdc_sfu.sv --source rtl/hdc/ot_hdc_fastfp.sv \
  --source rtl/hdc/ot_hdc_fp32_add_lat.sv \
  --source rtl/hdc/ot_hdc_matvec.sv --source rtl/hdc/ot_qwen_me_array.sv --source rtl/hdc/ot_qwen_rom_tile.sv \
  --source $M/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v \
  --source $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v \
  --param ACC_LAT=7 --param TREE_LAT=7 --param FAST_ISSUE=1 --param KV_PREP=3 --param MUL_LAT=6 \
  --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --stages $ST \
  --corner TT --orfs-corner WC --hold-corners WC,BC --keep-heavy-artifacts \
  --max-transition-ns --max-fanout 32 --macro-place-halo 4.32 2.16 \
  --macro-view ot_rom_4096x266_m8=$M/ot_rom_4096x266_m8 \
  --macro-view ot_sram_1r1w_128x256_m1_r2c2=$M/ot_sram_1r1w_128x256_m1_r2c2 \
  --nickname-tag w12_tile_$TAG --output results/physical_hdc/asap7/qwen_o4_w12/tile_$TAG/physical.json "$@"
