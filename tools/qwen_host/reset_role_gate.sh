#!/usr/bin/env bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.."&&pwd)
OUT=$1;mkdir -p "$OUT"
for NL in 6 2;do for MUT in 0 1 2;do
 iverilog -g2012 -s tb_qkd_host_rst_role -Ptb_qkd_host_rst_role.MUT="$MUT" -Ptb_qkd_host_rst_role.NL="$NL" -o "$OUT/tb-$MUT" "$R/rtl/test/qwen_host/tb_qkd_host_rst_role.sv" "$R/rtl/qwen_sys/host_20261013/qkd_host_rst_role_pins.sv" "$R/rtl/qwen_sys/ot_qwen_sys_rst_seq.sv" "$R/rtl/lib/ot_reset_sync.sv" > "$OUT/build-$MUT.log" 2>&1
 set +e
 vvp "$OUT/tb-$MUT" > "$OUT/run-$MUT.log" 2>&1
 RC=$?
 set -e
 if [[ $MUT == 0 ]];then
  if [[ $RC != 0 ]] || ! grep -q '^PASS' "$OUT/run-$MUT.log";then cat "$OUT/run-$MUT.log";exit 1;fi
 else
  if [[ $RC == 0 ]] || ! grep -q FATAL "$OUT/run-$MUT.log";then cat "$OUT/run-$MUT.log";exit 1;fi
 fi
 cat "$OUT/run-$MUT.log";rm "$OUT/tb-$MUT"
done;done
