#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory};mkdir "$out"
d=$root/rtl/qwen_sys/static_schedule_20261014
iverilog -g2012 -DOT_QFD_SEQ_SU_NOWROM -I"$root/rtl/hdc" -s qfd_seq_su_static -o "$out/parent.sim" \
 "$root/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v" \
 "$root/rtl/hdc/ot_hdc_delay.sv" "$root/rtl/hdc/ot_hdc_dyn_ttiles.sv" "$root/rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv" \
 "$root/rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv" "$root/rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv" \
 "$root/rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv" "$d/ot_qwen_rom_core_ctrl_su_static.sv" "$d/ot_qfd_seq_su_bi_static.sv" \
 "$d/ot_qwen_tp_seq_calendar.sv" "$d/ot_qwen_fixed_issue.sv" "$d/ot_qwen_fixed_issue_pw.sv" "$d/ot_qwen_fixed_issue_dense_pw.sv" \
 "$root/rtl/qwen_split/qfd_seq_su_collective_calendar.sv" "$root/rtl/rom/ot_coll_cmd_issue.sv" "$root/rtl/qwen_split/qfd_seq_su_static.sv" "$root/rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv" > "$out/compile.log" 2>&1
echo PASS_ACTUAL_STATIC_SU_PARENT_ELABORATED_NOT_EXECUTED_LAYER
