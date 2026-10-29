#!/bin/bash
set -euo pipefail
repo=$(realpath "${1:?repository}")
out=$(realpath -m "${2:?fresh output}")
mkdir -p "$out"
cd "$out"
for m in 0 1 2 3;do
  iverilog -g2012 -s tb_idx_link_tree -Ptb_idx_link_tree.MUT="$m" -o "m$m.vvp" \
    "$repo/rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv" \
    "$repo/tools/hbm_b2/topk_tree/serial_reference.sv" \
    "$repo/rtl/hbm_accel/index/ot_hbm_idx_compact_tree.sv" \
    "$repo/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
    "$repo/tools/hbm_b2/tb_idx_link_tree.sv" >"build$m.log" 2>&1
  set +e
  vvp "m$m.vvp" >"run$m.log" 2>&1
  rc=$?
  set -e
  if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;fi
 done
yosys -Q -T -p "read_verilog -sv $repo/rtl/hbm_accel/index/ot_hbm_idx_compact_tree.sv $repo/tools/hbm_b2/topk_tree/proof.sv; hierarchy -check -top proof; proc; flatten; opt; sat -verify -prove bad 0 -show-inputs" > proof.log 2>&1
for m in 0 1;do
 set +e
 yosys -Q -T -p "read_verilog -sv $repo/rtl/hbm_accel/index/ot_hbm_idx_compact_tree.sv $repo/tools/hbm_b2/topk_tree/carry_proof.sv; chparam -set MUT $m carry_proof; hierarchy -check -top carry_proof; proc; flatten; opt; sat -verify -tempinduct -seq 2 -set-init-zero -set rst_n 1 -set-at 1 rst_n 0 -prove bad 0 -show-inputs" > "carry$m.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;grep -q 'proof did fail' "carry$m.log";fi
 done
for m in 0 1;do
 set +e
 yosys -Q -T -p "read_verilog -sv $repo/tools/hbm_b2/topk_tree/header_proof.sv; chparam -set MUT $m header_proof; hierarchy -check -top header_proof; proc; flatten; opt; sat -verify -prove bad 0 -show-inputs" > "header$m.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;grep -q 'proof did fail' "header$m.log";fi
 done
echo TOPK_CURRENT_EXACT_GATE_PASS
