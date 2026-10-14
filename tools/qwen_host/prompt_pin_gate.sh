#!/usr/bin/env bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:?out};HOST=${2:?host integration source tree};mkdir -p "$OUT";OUT=$(cd "$OUT"&&pwd);export TMPDIR="$OUT"
P=("$R/rtl/qwen_sys/host_20261013/qkd_host_prompt_pins.sv" "$R/rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram.sv" "$R/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v")
H=("$HOST/rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv" "$R/rtl/physical/ot_qwen_host_ctl.sv" "$R/rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv" "$R/rtl/qwen_sys/ot_qwen_sys_rst_seq.sv" "$R/rtl/lib/ot_reset_sync.sv")
for SRC in "$HOST/rtl/qwen_sys/host_20261013/"*.sv; do
 [[ $(basename "$SRC") == qkd_host_prompt_pins.sv ]] || H+=("$SRC")
done
TOPS=(tb_qkd_host_prompt_pins tb_qkd_host_prompt_packet)
if [[ $# -gt 2 ]];then TOPS=("${@:3}");fi
for TOP in "${TOPS[@]}"; do
 for MUT in 0 1 2 3; do
  S=("$R/rtl/test/qwen_host/$TOP.sv" "${P[@]}");if [[ $TOP != tb_qkd_host_prompt_pins ]];then S+=("${H[@]}");fi
  iverilog -g2012 -s "$TOP" -P"$TOP.MUT=$MUT" -o "$OUT/$TOP-$MUT" "${S[@]}" > "$OUT/$TOP-build-$MUT.log" 2>&1
  set +e
  vvp "$OUT/$TOP-$MUT" > "$OUT/$TOP-run-$MUT.log" 2>&1
  RC=$?
  set -e
  if [[ $MUT == 0 ]];then
   if [[ $RC != 0 ]] || ! grep -q '^PASS' "$OUT/$TOP-run-$MUT.log";then cat "$OUT/$TOP-run-$MUT.log";exit 1;fi
  else
   if [[ $RC == 0 ]] || ! grep -q 'FATAL' "$OUT/$TOP-run-$MUT.log";then cat "$OUT/$TOP-run-$MUT.log";exit 1;fi
  fi
  cat "$OUT/$TOP-run-$MUT.log";rm "$OUT/$TOP-$MUT"
 done
done
