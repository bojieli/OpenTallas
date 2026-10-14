#!/usr/bin/env bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.."&&pwd)
OUT=${1:?out};HOST=${2:?host integration tree};mkdir -p "$OUT"
S=("$R/rtl/test/qwen_host/tb_qkd_host_prompt_ue.sv" "$HOST/rtl/qwen_sys/host_20261013/"*.sv "$HOST/rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv" "$R/rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram.sv" "$R/rtl/physical/ot_qwen_host_ctl.sv" "$R/rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv" "$R/rtl/qwen_sys/ot_qwen_sys_rst_seq.sv" "$R/rtl/lib/ot_reset_sync.sv" "$R/physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v")
for MUT in 0 1;do
 iverilog -g2012 -s tb_qkd_host_prompt_ue -Ptb_qkd_host_prompt_ue.MUT="$MUT" -o "$OUT/tb-$MUT" "${S[@]}" > "$OUT/build-$MUT.log" 2>&1
 set +e
 vvp "$OUT/tb-$MUT" > "$OUT/run-$MUT.log" 2>&1
 RC=$?
 set -e
 if [[ $MUT == 0 ]];then [[ $RC == 0 ]]&&grep -q '^PASS' "$OUT/run-$MUT.log";else [[ $RC != 0 ]]&&grep -q 'UE corrupted prompt launched controller' "$OUT/run-$MUT.log";fi
 cat "$OUT/run-$MUT.log";rm "$OUT/tb-$MUT"
done
