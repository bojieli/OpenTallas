#!/usr/bin/env bash
set -euo pipefail
out=${1:?};mkdir -p "$out"
for mut in 0 1;do
  iverilog -g2012 -s tb_native_writer_reset_pin -Ptb_native_writer_reset_pin.MUT=$mut -o "$out/m$mut.vvp" rtl/lib/ot_rst_relay.sv rtl/physical/ot_qkd_kv_static_writer_native.sv rtl/qwen_sys/static_kv_20261014/qkd_kv_static_writer.sv rtl/test/qwen_static_kv/tb_native_writer_reset_pin.sv
  rc=0;vvp "$out/m$mut.vvp" > "$out/m$mut.log" 2>&1 || rc=$?
  cat "$out/m$mut.log"
  if [[ $mut == 0 ]];then [[ $rc == 0 ]];grep -q '^RESET_PIN PASS' "$out/m$mut.log"
  else [[ $rc != 0 ]];grep -q 'RESET_PIN FAIL' "$out/m$mut.log";fi
done
