#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd);out=$1
P=${PREREQ_ROOT:-$root}
if [ -z "${PREREQ_ROOT:-}" ] && [ -d "$root/prereq/rtl" ];then P="$root/prereq";fi
mkdir -p "$out/tmp";export TMPDIR="$out/tmp"
for mut in 0 1;do
iverilog -g2012 -s tb_qkd_host_service_csr -Ptb_qkd_host_service_csr.MUT=$mut -o "$out/csr$mut" "$root/rtl/qwen_sys/host_20261013/qkd_host_guard_fifo.sv" "$root/rtl/qwen_sys/host_20261013/qkd_host_service_guard.sv" "$root/rtl/qwen_sys/host_20261013/qkd_host_sys_csr_service.sv" "$root/rtl/qwen_sys/host_20261013/qkd_host_csr_service_pins.sv" "$P/rtl/qwen_sys/host_20261013/qkd_host_pin_channel.sv" "$root/rtl/test/qwen_host/tb_qkd_host_service_csr.sv"
set +e
vvp "$out/csr$mut" > "$out/csr$mut.log" 2>&1
rc=$?
set -e
if [ "$mut" = 0 ];then
 if [ "$rc" != 0 ] || ! grep -q 'PASS service CSR' "$out/csr$mut.log";then cat "$out/csr$mut.log";exit 1;fi
else
 if [ "$rc" = 0 ] || ! grep -q FATAL "$out/csr$mut.log";then cat "$out/csr$mut.log";exit 1;fi
fi
cat "$out/csr$mut.log"
done
