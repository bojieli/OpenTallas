#!/bin/bash
set -euo pipefail
# Run on an admitted fleet worker. SOURCE_ROOT must hold exact predecessor04b625135.
source_root=$(readlink -f "$1")
packet_root=$(cd "$(dirname "$0")" && pwd)
proposal_root=$(cd "$packet_root/../../.." && pwd)
output_dir=$(readlink -m "${2:-$packet_root/replay}")
mkdir -p "$output_dir"
for selected_case in 0 1 2 3 4 5 6; do
  iverilog -g2012 -s tb -Ptb.CASE="$selected_case" -o "$output_dir/case$selected_case.vvp" \
    "$packet_root/tb_bootage_dispatch.sv" \
    "$proposal_root/rtl/qwen_sys/kv_bootage_20261019/qkd_static_kv_boot_dispatch_age.sv" \
    "$proposal_root/rtl/qwen_sys/kv_bootage_20261019/qkd_static_kv_boot_dispatch_mu_age.sv" \
    "$source_root/rtl/qwen_sys/static_kv_20261014/qkd_static_kv_boot_dispatch.sv" \
    "$source_root/rtl/qwen_sys/static_kv_20261014/qkd_kv_die_cfg.sv" \
    "$source_root/rtl/qwen_sys/kv_bootage_20261019/qkd_kv_die_cfg_a.sv" \
    > "$output_dir/case$selected_case.build.log" 2>&1
  vvp "$output_dir/case$selected_case.vvp" > "$output_dir/case$selected_case.log" 2>&1
done
