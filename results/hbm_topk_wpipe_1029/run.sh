#!/bin/bash
set -euo pipefail
repo=$(realpath "${1:?repo}"); out=$(realpath -m "${2:?fresh output}")
mkdir -p "$out";cd "$out"
for spec in 0:0 2:0 2:4 2:5 2:6;do
 p=${spec%:*};m=${spec#*:};tag=p${p}m${m}
 iverilog -g2012 -s tb_idx_link_wpipe -Ptb_idx_link_wpipe.WPIPE="$p" -Ptb_idx_link_wpipe.MUT="$m" -o "$tag.vvp" \
  "$repo/rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv" "$repo/rtl/hbm_accel/index/ot_hbm_idx_compact_tree.sv" \
  "$repo/tools/hbm_b2/topk_tree/serial_reference.sv" \
  "$repo/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
  "$repo/results/hbm_topk_wpipe_1029/tb_idx_link_wpipe.sv" >"build_$tag.log" 2>&1
 set +e
 vvp "$tag.vvp" >"run_$tag.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;grep -q 'dense compaction exact/miter/timeline mismatch' "run_$tag.log";fi
 done
echo TOPK_WPIPE_STATIC_CALENDAR_PASS
