#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mut=${1:-0}
mkdir -p work
iverilog -g2012 -Ptb_fence_pinret.MUT="$mut" -Ptb_fence_pinret.SEED=7 -Ptb_fence_pinret.INPIN=1 -Ptb_fence_pinret.HOLDBUF=2 -o "work/fence_${mut}.vvp" -s tb_fence_pinret tb_fence_pinret.sv ot_gpu_rf_visibility_fence_p2.sv ot_fence_pin_return.sv ot_sc_pfifo.sv ot_gpu_rf_visibility_fence.sv ot_s81_head_min_delay.sv ot_hdc_delay.sv min_delay_cells_model.sv
vvp -n "work/fence_${mut}.vvp" > "fence_${mut}.log" 2>&1
cat "fence_${mut}.log"

grep -q "^FENCE_P PASS .*bad=0$" "fence_${mut}.log"
