#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?output};mkdir -p "$out";out=$(cd "$out"&&pwd)
export TMPDIR="$out"
for mut in 0 4 5 6;do
 iverilog -g2012 -s tb_qkd_host_native_token_endpoint_cancel -Ptb_qkd_host_native_token_endpoint_cancel.MUT="$mut" -o "$out/m$mut" rtl/qwen_sys/host_20261013/qkd_host_native_token_endpoint.sv rtl/qwen_sys/host_integrated_20261014/qkd_host_native_token_endpoint_cancel.sv rtl/test/qwen_host/tb_qkd_host_native_token_endpoint_cancel.sv > "$out/build-$mut.log" 2>&1
 if [[ $mut == 0 ]];then
  vvp "$out/m$mut" | tee "$out/positive.log"
  grep -q '^PASS HOST_NATIVE_CANCEL' "$out/positive.log"
 else
  if vvp "$out/m$mut" > "$out/mutant-$mut.log" 2>&1;then echo "FAIL undetected cancel mutant $mut";exit 1;fi
  grep -q '^FATAL:' "$out/mutant-$mut.log";cat "$out/mutant-$mut.log"
 fi
 rm "$out/m$mut"
done
