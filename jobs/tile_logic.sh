#!/bin/bash
# usage: jobs/tile_logic.sh <tag> <stages> [extra driver args...]  -- the tile's logic without macros (host synth/sta)
set -o pipefail
TAG=$1; ST=$2; shift 2
python3 tools/run_abi3_physical.py --view asap7 --top ot_qwen_rom_tile_logic \
  --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_fp32_mul_pipe.sv --source rtl/hdc/ot_hdc_fpu.sv \
  --source rtl/proto/ot_fp32_add_rne_pipe.sv --source rtl/hdc/ot_hdc_sfu.sv --source rtl/hdc/ot_hdc_fastfp.sv \
  --source rtl/hdc/ot_hdc_matvec.sv --source rtl/hdc/ot_qwen_me_array.sv --source rtl/hdc/ot_qwen_rom_tile.sv \
  --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --stages $ST --corner TT \
  --nickname-tag w12_tlogic_$TAG --output results/physical_hdc/asap7/qwen_o4_w12/tile_logic_$TAG/physical.json "$@"
