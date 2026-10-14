#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd);out=$1
P=${PREREQ_ROOT:-$root}
if [ -z "${PREREQ_ROOT:-}" ] && [ -d "$root/prereq/rtl" ];then P="$root/prereq";fi
mkdir -p "$out/tmp";export TMPDIR="$out/tmp"
S=("$root/rtl/test/qwen_host/tb_qkd_host_control_service.sv" "$root/rtl/qwen_sys/host_20261013/"*.sv)
for f in "$P/rtl/qwen_sys/host_20261013/"*.sv;do
 if [ ! -f "$root/rtl/qwen_sys/host_20261013/$(basename "$f")" ];then S+=("$f");fi
done
S+=("$P/rtl/physical/ot_qkd_host_prompt_capture_pins.sv" "$P/rtl/physical/ot_qfd_prompt_sram_capture.sv" "$P/rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv" "$P/rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram.sv" "$P/rtl/physical/ot_qwen_host_ctl.sv" "$P/rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv" "$P/rtl/qwen_sys/ot_qwen_sys_rst_seq.sv" "$P/rtl/lib/ot_reset_sync.sv" "$P/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v")
for case in 0:0:0 0:0:1 0:0:2 0:0:3 0:0:4 0:0:5 1:0:0 1:0:6 2:0:0 2:0:7 3:0:0 3:0:8 0:1:0 0:1:1;do
 IFS=: read -r fault ue mut <<< "$case"
 iverilog -g2012 -s tb_qkd_host_control_service -Ptb_qkd_host_control_service.FAULT=$fault -Ptb_qkd_host_control_service.UE=$ue -Ptb_qkd_host_control_service.MUT=$mut -o "$out/packet-$case" "${S[@]}" > "$out/build-$case.log" 2>&1
 set +e
 vvp "$out/packet-$case" > "$out/packet-$case.log" 2>&1
 rc=$?
 set -e
 if [ "$mut" = 0 ];then
  if [ "$rc" != 0 ] || ! grep -q '^PASS' "$out/packet-$case.log";then cat "$out/packet-$case.log";exit 1;fi
 else
  if [ "$rc" = 0 ] || ! grep -q FATAL "$out/packet-$case.log";then cat "$out/packet-$case.log";exit 1;fi
 fi
 cat "$out/packet-$case.log"
done
