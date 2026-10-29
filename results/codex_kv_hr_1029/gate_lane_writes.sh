#!/bin/bash
# Smallest actual physical control mechanism, MU1 HCW39 and HCW182; all8 roles.
set -eu
R=$1
O=$2
mkdir -p "$O"
for h in 39 182; do
 for m in 0 1; do
  iverilog -g2012 -s tb -Ptb.HCW=$h -Ptb.MUTBENCH=$m -o "$O/h${h}m${m}" "$R/rtl/qwen_sys/host_integrated_20261014/qkd_host_ctrl_token_service_packet_collected.sv" "$R/rtl/qwen_sys/mu_qwen_20261018/qkd_host_ctrl_token_service_packet_collected_mu.sv" "$R/results/codex_kv_hr_1029/tb_lane_writes.sv" > "$O/build_h${h}m${m}.log" 2>&1
  vvp "$O/h${h}m${m}" | tee "$O/h${h}m${m}.log"
 done
done
