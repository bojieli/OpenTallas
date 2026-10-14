#!/usr/bin/env bash
set -eu
OUT=$1; MUT=${2:-0}
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
iverilog -g2012 -s tb_qkd_host_ctl -Ptb_qkd_host_ctl.MUT="$MUT" -o "$OUT/tb" "$R/rtl/test/tb_qkd_host_ctl.sv" "$R/rtl/physical/ot_qwen_host_ctl.sv" "$R/rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv" > "$OUT/build.log" 2>&1
set +e
vvp "$OUT/tb" > "$OUT/run.log" 2>&1
RC=$?
set -e
cat "$OUT/run.log"
exit "$RC"
