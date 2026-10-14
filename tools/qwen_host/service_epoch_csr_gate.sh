#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd);out=$1
P=${PREREQ_ROOT:-$root}
if [ -z "${PREREQ_ROOT:-}" ] && [ -d "$root/prereq/rtl" ];then P="$root/prereq";fi
mkdir -p "$out/tmp";export TMPDIR="$out/tmp"
for mut in 0 3;do
iverilog -g2012 -s tb_qkd_host_service_epoch_csr -Ptb_qkd_host_service_epoch_csr.MUT=$mut -o "$out/retained$mut" "$root/rtl/qwen_sys/host_20261013/qkd_host_guard_fifo.sv" "$root/rtl/qwen_sys/host_20261013/qkd_host_service_guard.sv" "$root/rtl/qwen_sys/host_20261013/qkd_host_ctrl_service_packet.sv" "$root/rtl/qwen_sys/host_20261013/qkd_host_sys_csr_service.sv" "$root/rtl/qwen_sys/host_20261013/qkd_host_csr_service_pins.sv" "$P/rtl/qwen_sys/host_20261013/qkd_host_pin_channel.sv" "$root/rtl/test/qwen_host/tb_qkd_host_service_epoch_csr.sv" > "$out/retained-build$mut.log" 2>&1
set +e
vvp "$out/retained$mut" > "$out/retained$mut.log" 2>&1
rc=$?
set -e
if [ "$mut" = 0 ];then
 if [ "$rc" != 0 ] || ! grep -q 'PASS service retained epoch' "$out/retained$mut.log";then cat "$out/retained$mut.log";exit 1;fi
else
 if [ "$rc" = 0 ] || ! grep -q FATAL "$out/retained$mut.log";then cat "$out/retained$mut.log";exit 1;fi
fi
cat "$out/retained$mut.log"
done
