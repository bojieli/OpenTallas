#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd);out=$1
P=${PREREQ_ROOT:-$root}
if [ -z "${PREREQ_ROOT:-}" ] && [ -d "$root/prereq/rtl" ];then P="$root/prereq";fi
A=${ALLOCATOR_ROOT:-$P}
mkdir -p "$out/tmp";export TMPDIR="$out/tmp"
for mut in 0 10 12 13 14 15;do
iverilog -g2012 -s tb_qkd_host_token_transport -Ptb_qkd_host_token_transport.MUT=$mut -o "$out/token$mut" "$root/rtl/qwen_sys/host_20261013/qkd_host_ctrl_token_service_packet.sv" "$root/rtl/test/qwen_host/tb_qkd_host_token_transport.sv"
set +e
vvp "$out/token$mut" > "$out/token$mut.log" 2>&1
rc=$?
set -e
if [ "$mut" = 0 ];then
 if [ "$rc" != 0 ] || ! grep -q 'PASS token transport' "$out/token$mut.log";then cat "$out/token$mut.log";exit 1;fi
else
 if [ "$rc" = 0 ] || ! grep -q FATAL "$out/token$mut.log";then cat "$out/token$mut.log";exit 1;fi
fi
cat "$out/token$mut.log"
done
iverilog -g2012 -s tb_qkd_host_token_allocator_transport -o "$out/actual_allocator" "$A/rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_epoch_allocator.sv" "$root/rtl/qwen_sys/host_20261013/qkd_host_ctrl_token_service_packet.sv" "$root/rtl/test/qwen_host/tb_qkd_host_token_allocator_transport.sv"
vvp "$out/actual_allocator" > "$out/actual_allocator.log" 2>&1
grep -q 'PASS actual token allocator transport' "$out/actual_allocator.log"
cat "$out/actual_allocator.log"
for mut in 0 11;do
iverilog -g2012 -s tb_qkd_host_token_replay -Ptb_qkd_host_token_replay.MUT=$mut -o "$out/replay$mut" "$root/rtl/qwen_sys/host_20261013/qkd_host_ctrl_token_service_packet.sv" "$root/rtl/test/qwen_host/tb_qkd_host_token_replay.sv"
set +e
vvp "$out/replay$mut" > "$out/replay$mut.log" 2>&1
rc=$?
set -e
if [ "$mut" = 0 ];then
 if [ "$rc" != 0 ] || ! grep -q 'PASS token replay' "$out/replay$mut.log";then cat "$out/replay$mut.log";exit 1;fi
else
 if [ "$rc" = 0 ] || ! grep -q FATAL "$out/replay$mut.log";then cat "$out/replay$mut.log";exit 1;fi
fi
cat "$out/replay$mut.log"
done
iverilog -g2012 -s tb_qkd_host_ctrl_token_legacy -o "$out/legacy" "$root/rtl/qwen_sys/host_20261013/qkd_host_ctrl_token_service_packet.sv" "$root/rtl/test/qwen_host/tb_qkd_host_ctrl_token_legacy.sv"
vvp "$out/legacy" > "$out/legacy.log" 2>&1
grep -q 'PASS CTRL8_PACKET' "$out/legacy.log"
cat "$out/legacy.log"
