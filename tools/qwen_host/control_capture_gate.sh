#!/usr/bin/env bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.."&&pwd)
OUT=${1:?out};mkdir -p "$OUT"
S=("$R/rtl/test/qwen_host/tb_qkd_host_control_capture.sv" "$R/rtl/qwen_sys/host_20261013/"*.sv "$R/rtl/physical/ot_qkd_host_prompt_capture_pins.sv" "$R/rtl/physical/ot_qfd_prompt_sram_capture.sv" "$R/rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv" "$R/rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram.sv" "$R/rtl/physical/ot_qwen_host_ctl.sv" "$R/rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv" "$R/rtl/qwen_sys/ot_qwen_sys_rst_seq.sv" "$R/rtl/lib/ot_reset_sync.sv" "$R/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v")
for CASE in 0:0 0:1 0:2 0:3 0:4 0:5 1:0 1:1;do
 UE=${CASE%:*};MUT=${CASE#*:}
 iverilog -g2012 -s tb_qkd_host_control_capture -Ptb_qkd_host_control_capture.UE="$UE" -Ptb_qkd_host_control_capture.MUT="$MUT" -o "$OUT/tb-$UE-$MUT" "${S[@]}" > "$OUT/build-$UE-$MUT.log" 2>&1
 set +e
 vvp "$OUT/tb-$UE-$MUT" > "$OUT/run-$UE-$MUT.log" 2>&1
 RC=$?
 set -e
 if [[ $MUT == 0 ]];then
  if [[ $RC != 0 ]] || ! grep -q '^PASS' "$OUT/run-$UE-$MUT.log";then cat "$OUT/run-$UE-$MUT.log";exit 1;fi
 else
  if [[ $RC == 0 ]] || ! grep -q FATAL "$OUT/run-$UE-$MUT.log";then cat "$OUT/run-$UE-$MUT.log";exit 1;fi
 fi
 cat "$OUT/run-$UE-$MUT.log";rm "$OUT/tb-$UE-$MUT"
done
