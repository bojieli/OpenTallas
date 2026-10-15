#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel);cd "$root"
out=${1:?absolute output directory};image=${2:?source-pinned dense PW image};mkdir -p "$out"
files=(rtl/qwen_sys/program_receiver_20261014/tb_qkd_actual_program_copies.sv
physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_dyn_ttiles.sv rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv rtl/hdc/ot_hdc_prefix.sv
rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv
rtl/qwen_sys/redesign_qwen/ot_qfd_seq_su_bi.sv rtl/qwen_sys/static_schedule_20261014/ot_qwen_rom_core_ctrl_su_static.sv
rtl/qwen_sys/static_schedule_20261014/ot_qfd_seq_su_bi_static.sv rtl/qwen_sys/static_schedule_20261014/ot_qwen_rom_core_ctrl_static.sv
rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_split_static.sv rtl/physical/ot_qfd_tt_ctlm_split.sv
rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue.sv rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue_pw.sv
rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue_dense_pw.sv rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv
rtl/qwen_sys/dvm_20261014/ot_qfd_xpf_dense_pw_loader.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xpf_static_schedule.sv)
sha256sum "${files[@]}" > "$out/source.sha256"
iverilog -g2012 -Irtl/hdc -s tb_qkd_actual_program_copies -o "$out/actual.sim" "${files[@]}" > "$out/build.log" 2>&1
for mut in 0 1 2 3;do vvp "$out/actual.sim" +IMAGE="$image" +MUT="$mut" > "$out/copy_${mut}.log" 2>&1;cat "$out/copy_${mut}.log";done
