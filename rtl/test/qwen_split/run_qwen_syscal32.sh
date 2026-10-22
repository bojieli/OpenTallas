#!/bin/bash
set -eu
O=$1; M=${2:-0}; R=$(cd "$(dirname "$0")/../../.." && pwd)
mkdir -p "$O"
V=${VERILATOR:-verilator}
"$V" --version > "$O/tool.txt"
grep -q 'Verilator 5.050' "$O/tool.txt" || { cat "$O/tool.txt"; exit 2; }
S=("$R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv"
 "$R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_sysface32.sv"
 "$R/rtl/test/qwen_split/tb_qwen_syscal32.sv")
sha256sum "${S[@]}" > "$O/source.sha256"
"$V" --binary --timing -j 4 -Wno-fatal --top-module tb_qwen_syscal32 -GMUT="$M" --Mdir "$O/obj" "${S[@]}" > "$O/build.log" 2>&1
set +e
"$O/obj/Vtb_qwen_syscal32" > "$O/run.log" 2>&1
RC=$?
set -e
cat "$O/run.log"
if [ "$M" = 0 ]; then grep -q '^SYSCAL32_PASS' "$O/run.log"; else
 test "$RC" != 0;grep -q 'SYSCAL32_MISMATCH' "$O/run.log"
fi
