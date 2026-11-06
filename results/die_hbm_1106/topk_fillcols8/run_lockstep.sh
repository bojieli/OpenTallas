#!/bin/bash
set -euo pipefail
repo=$(git rev-parse --show-toplevel)
iverilog -g2012 -s topk_fill_tb -o topk_fill_sim "$repo/rtl/hbm_accel/cores_split/reform_1105s/topk/ot_hbm_idx_topk_tiles.sv" "$repo/results/die_hbm_1106/topk_fillcols8/topk_fill_tb.sv"
vvp topk_fill_sim
