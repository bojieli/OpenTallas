#!/usr/bin/env bash
# Run only inside an admitted ot-run unit. Transport/control proof; not arithmetic or throughput qualification.
set -euo pipefail
repo_root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$repo_root"
run_dir=${KV_SEQ_RUN_DIR:-/tmp/kv-seq-heads}
mkdir -p "$run_dir"
for profile in 1_1_0_0 2_0_0_0 1_1_0_1 2_0_0_1 1_1_2_0 1_1_4_0 1_1_0_2; do
 IFS=_ read -r heads precision mutant cluster <<< "$profile"
 native_define=(); if [[ "$cluster" == 2 ]]; then native_define=(-DNATIVE_MASTER); fi
 iverilog "${native_define[@]}" -g2012 -s tb_kv_seq_heads \
  -Ptb_kv_seq_heads.HEADS="$heads" -Ptb_kv_seq_heads.Q_FP32="$precision" \
  -Ptb_kv_seq_heads.MUT="$mutant" -Ptb_kv_seq_heads.CLUSTER="$cluster" \
  -o "$run_dir/sim_$profile" \
  rtl/test/qwen_kv_die/tb_kv_seq_heads.sv \
  rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv \
  rtl/qwen_sys/kv_die_20261009/ot_qkvd_fifo.sv \
  rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_desc.sv \
  rtl/qwen_sys/system_20261008/ot_qfd_dctl.sv \
  rtl/physical/ot_qwen_kv_centre_slots.sv rtl/physical/ot_qwen_kv_seq_tp8.sv rtl/lib/ot_rst_relay.sv \
  > "$run_dir/compile_$profile.log" 2>&1
 vvp "$run_dir/sim_$profile" > "$run_dir/run_$profile.log"
 if [[ "$mutant" == 0 ]]; then
  grep -Eq '^EXACT_PASS ' "$run_dir/run_$profile.log"
  ! grep -Eq 'EXACT_FAIL|EXACT_TIMEOUT|ERROR:' "$run_dir/run_$profile.log"
 else
  grep -Eq '^EXACT_FAIL ' "$run_dir/run_$profile.log"
  ! grep -Eq 'EXACT_PASS|EXACT_TIMEOUT|ERROR:' "$run_dir/run_$profile.log"
 fi
 cat "$run_dir/run_$profile.log"
done
printf 'TRANSPORT_CONTROL_GATE_PASS\n'
