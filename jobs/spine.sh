#!/bin/bash
# usage: jobs/spine.sh <tag> <stages> [extra driver args...]  -- the Qwen ROM spine engine top (ot_qwen_me_spine)
set -o pipefail
TAG=$1; ST=$2; shift 2
python3 tools/run_abi3_physical.py --view asap7 --top ot_qwen_me_spine \
  --source rtl/hdc/ot_hdc_delay.sv --source rtl/hdc/ot_hdc_fp32_mul_pipe.sv --source rtl/hdc/ot_hdc_fpu.sv \
  --source rtl/proto/ot_fp32_add_rne_pipe.sv --source rtl/hdc/ot_hdc_sfu.sv --source rtl/hdc/ot_hdc_fastfp.sv \
  --source rtl/hdc/ot_hdc_matvec.sv --source rtl/hdc/ot_qwen_me_array.sv \
  --param GT=6144 --param SMIN=7 --param TCUT=7 --param SMAX=11 --param NW=18 \
  --param BD=24 --param XVM=1 --param NWS=3 --param TWS=22 --param ORD=4 --param MEM_EXTRA=1 --param SCALE_LOCAL=1 \
  --clock-period-ns 0.833333 --clock-uncertainty-ns 0.060 --clock-uncertainty-hold-ns 0.025 --stages $ST --corner TT \
  --nickname-tag w12_spine_$TAG --output results/physical_hdc/asap7/qwen_o4_w12/spine_$TAG/physical.json "$@"
