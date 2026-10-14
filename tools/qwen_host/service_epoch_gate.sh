#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd);out=$1
mkdir -p "$out/tmp";export TMPDIR="$out/tmp"
for mut in 0 3 5 6;do
iverilog -g2012 -s tb_qkd_host_service_epoch -Ptb_qkd_host_service_epoch.MUT=$mut -o "$out/epoch$mut" "$root/rtl/qwen_sys/host_20261013/qkd_host_guard_fifo.sv" "$root/rtl/qwen_sys/host_20261013/qkd_host_service_guard.sv" "$root/rtl/qwen_sys/host_20261013/qkd_host_ctrl_service_packet.sv" "$root/rtl/test/qwen_host/tb_qkd_host_service_epoch.sv"
set +e
vvp "$out/epoch$mut" > "$out/epoch$mut.log" 2>&1
rc=$?
set -e
if [ "$mut" = 0 ];then
 if [ "$rc" != 0 ] || ! grep -q 'PASS service epoch' "$out/epoch$mut.log";then cat "$out/epoch$mut.log";exit 1;fi
else
 if [ "$rc" = 0 ] || ! grep -q FATAL "$out/epoch$mut.log";then cat "$out/epoch$mut.log";exit 1;fi
fi
cat "$out/epoch$mut.log"
done
iverilog -g2012 -s tb_qkd_host_ctrl_service_legacy -o "$out/legacy" "$root/rtl/qwen_sys/host_20261013/qkd_host_ctrl_service_packet.sv" "$root/rtl/test/qwen_host/tb_qkd_host_ctrl_service_legacy.sv"
vvp "$out/legacy" > "$out/legacy.log" 2>&1
grep -q 'PASS CTRL8_PACKET' "$out/legacy.log"
cat "$out/legacy.log"
