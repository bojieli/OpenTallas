#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
for mode in exact mutant;do
 args=();[[ "$mode" == exact ]]||args=(-DOT_QKD_SLOT_MUT)
 "$v" --binary --timing -O2 -j 4 -Wno-fatal --top-module tb_qkd_embgw_splitboot "${args[@]}" --Mdir "$out/$mode-obj" rtl/qwen_sys/split_20261014/qkd_embgw_splitboot.sv rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_strip.sv rtl/test/qwen_host/tb_qkd_embgw_splitboot.sv > "$out/$mode-build.log" 2>&1
 "$out/$mode-obj/Vtb_qkd_embgw_splitboot" > "$out/$mode.log" 2>&1 || true
 grep -E '^(PASS|FAIL|MISMATCH)' "$out/$mode.log" | head -8 || true
 if [[ "$mode" == exact ]];then grep -q '^PASS' "$out/$mode.log";! grep -q '^FAIL' "$out/$mode.log";else grep -q '^FAIL' "$out/$mode.log";fi
done
echo PASS SPLITBOOT_GATEWAY_EXACT_AND_OBSERVED_MUTANT
