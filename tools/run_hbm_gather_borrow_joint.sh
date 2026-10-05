#!/usr/bin/env bash
# Run remotely under the owner's admission policy. No full array or token build.
set -uo pipefail
repo_root=$(cd "$(dirname "$0")/.." && pwd)
output_dir=$(realpath -m "${1:?usage: run_hbm_gather_borrow_joint.sh OUTPUT_DIR}")
mkdir -p "$output_dir"
cd "$repo_root"
iverilog -g2012 -s tb_hbm_gather_borrow_joint -o "$output_dir/joint.vvp" \
 rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv \
 rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_sm0_borrow.sv \
 rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_gather_bridge.sv \
 rtl/test/hbm_accel/tb_hbm_gather_borrow_joint.sv > "$output_dir/compile.log" 2>&1
result=$?
printf '%s\n' "$result" > "$output_dir/compile.exit"
if (( result != 0 )); then exit "$result"; fi
vvp "$output_dir/joint.vvp" > "$output_dir/runtime.log" 2>&1
result=$?
printf '%s\n' "$result" > "$output_dir/runtime.exit"
exit "$result"
