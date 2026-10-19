#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
R=results/arch/kv_retire_source_1019
O=${OUT:-$R/out};mkdir -p "$O"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version | tee "$O/verilator.version"
grep -q '5.050' "$O/verilator.version"
H=rtl/qwen_sys/host_20261013
S=rtl/qwen_sys/retire_source_20261019
for profile in su mu;do
 define=();bench="$R/tb_kv_retained_export.sv"; if [ "$profile" = mu ];then define=(-DTEST_MU);bench="$R/tb_kv_retained_export_mu.sv";fi
 for m in 0 1;do
 "$V" --binary --timing -Wno-fatal -j 4 --top-module tb_kv_retained_export "${define[@]}" -GEXPORT_MUT=$m --Mdir "$O/${profile}$m" "$bench" "$S/qkd_host_ctrl_token_service_packet_collected_rh.sv" "$S/qkd_host_ctrl_token_service_packet_collected_mu_rh.sv" "$H/qkd_host_service_guard_wh.sv" "$H/qkd_host_service_guard.sv" "$H/qkd_host_guard_fifo.sv" > "$O/${profile}${m}_build.log" 2>&1
 set +e
 "$O/${profile}$m/Vtb_kv_retained_export" > "$O/${profile}$m.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then [ "$rc" = 0 ];grep -q KV_RETAINED_EXPORT_PASS "$O/${profile}$m.log";
 else [ "$rc" != 0 ];grep -q WARM_RETAINED_VETO_MISSING "$O/${profile}$m.log";fi
 done
done
printf 'KV_RETAINED_SOURCE_PASS SU+MU component only; production nested SU unchanged\n' | tee "$O/summary.log"
