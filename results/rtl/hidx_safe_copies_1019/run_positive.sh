#!/bin/bash
set -euo pipefail
root=$PWD
mkdir -p ../positive
out=$(realpath ../positive)
v=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
$v --version >"$out/tool.log"
$v --binary --timing -Wno-fatal -j 8 --top-module tb_idx_link_pipe --Mdir "$out/obj" -GSAFE_RING=1 -GSAFE_CARRY=1 -GSAFE_COPIES=1 -GEMIT_GAP=0 rtl/test/hbm_idx_static/tb_idx_link_pipe.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static_p.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v >"$out/build.log" 2>&1
"$out/obj/Vtb_idx_link_pipe" >"$out/run.log" 2>&1
cat "$out/run.log"
