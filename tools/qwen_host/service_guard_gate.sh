#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$1
mkdir -p "$out/tmp";export TMPDIR="$out/tmp"
for mut in 0 1 2 3 4; do
  iverilog -g2012 -s tb_qkd_host_service_guard -Ptb_qkd_host_service_guard.MUT=$mut -o "$out/g$mut" "$root/rtl/qwen_sys/host_20261013/qkd_host_guard_fifo.sv" "$root/rtl/qwen_sys/host_20261013/qkd_host_service_guard.sv" "$root/rtl/test/qwen_host/tb_qkd_host_service_guard.sv"
  set +e
  vvp "$out/g$mut" > "$out/mut$mut.log" 2>&1
  rc=$?
  set -e
  if [ "$mut" = 0 ]; then
    if [ "$rc" != 0 ] || ! grep -q 'PASS service guard' "$out/mut$mut.log";then cat "$out/mut$mut.log";exit 1;fi
  else
    if [ "$rc" = 0 ] || ! grep -q FATAL "$out/mut$mut.log";then cat "$out/mut$mut.log";exit 1;fi
  fi
  cat "$out/mut$mut.log"
done
