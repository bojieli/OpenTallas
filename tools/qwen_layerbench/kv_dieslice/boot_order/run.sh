#!/bin/bash
set -euo pipefail
O=$1;H=$(cd "$(dirname "$0")"&&pwd);R=$(cd "$H/../../../.."&&pwd)
D=$R/rtl/qwen_sys/d2d_static_20261015
mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing -j 4 -Wno-fatal -I"$D" --top-module tb_boot_order --Mdir "$O/obj" "$D/ot_qwen_d2d_cal_seq_bc4.sv" "$D/qkd_d2d_cal_seq_bc4.sv" "$R/rtl/qwen_sys/kv_host_obs_20261019/qkd_d2d_boot_event_bridge.sv" "$H/tb_boot_order.sv" > "$O/build.log" 2>&1
for m in 0 1 2 3 4 5;do "$O/obj/Vtb_boot_order" +MODE=$m > "$O/mode$m.log" 2>&1;head -1 "$O/mode$m.log";done
