#!/bin/bash
# ELEM-GAPS/HBMB 10-18: die-master bench of ot_hbm_idx_qctl_static. Usage: run_qctl_static.sh OUT MUT (0 pass; 1,2,3 fail)
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-qctl}");m=${2:-0}
mkdir -p "$out"
iverilog -g2012 -s tb_idx_qctl_static -Ptb_idx_qctl_static.MUT="$m" -o "$out/q$m.vvp" \
 rtl/hbm_accel/index/quad_1017/ot_hbm_idx_qctl_static.sv rtl/hbm_accel/index/ot_hbm_idx_calendar_static.sv rtl/lib/ot_rst_relay.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v rtl/test/hbm_idx_static/tb_idx_qctl_static.sv
vvp "$out/q$m.vvp" | tee "$out/q$m.log"
grep -q IDX_QCTL_STATIC_PASS "$out/q$m.log"
