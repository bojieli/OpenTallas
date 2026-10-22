#!/bin/bash
set -eu
out=$1; m=${2:-0}
mkdir -p "$out"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -Wno-fatal --top-module tb -GMUT="$m" --Mdir "$out/build" -j 4 results/rtl/kv_hroot_safe32_1020/tb.sv results/rtl/kv_hroot_safe32_1020/reference.sv rtl/qwen_sys/static_kv_die_20261017/qkd_kv_hroot_safe32.sv >"$out/build.log" 2>&1
set +e
"$out/build/Vtb" >"$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
exit "$rc"
