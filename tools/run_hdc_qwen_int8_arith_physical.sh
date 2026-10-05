#!/usr/bin/env bash
# Source-pinned reduced Qwen O4 INT8 arithmetic gate. PNR requires ORFS Docker.
set -euo pipefail
cd "$(dirname "$0")/.."
stage="${OT_PHYSICAL_STAGES:-synth,sta}"
python3 tools/run_abi3_physical.py \
  --view asap7 --top ot_hdc_qwen_int8_arith \
  --source rtl/hdc/ot_hdc_delay.sv \
  --source rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
  --source rtl/hdc/ot_hdc_fpu.sv \
  --source rtl/hdc/ot_hdc_qwen_int8_arith.sv \
  --clock-period-ns 0.92 --stages "$stage" --corner TT \
  --max-transition-ns --slew-margin-percent 45 \
  --core-utilization 25 --place-density 0.55 \
  --nickname-tag hdc_qwen_o4_int8_arith \
  --output results/physical_hdc/asap7/qwen_o4_int8_arith/physical.json "$@"
