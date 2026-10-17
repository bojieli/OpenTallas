#!/usr/bin/env bash
# usage: OUT [M]  (M given: run only mutant M under the positive check, so a detected mutant exits non-zero)
# KVJ-C (b): embedding row transmitter behind the real static join; exact PASS, mutants 1/2/3 must FAIL.
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};only=${2:-};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src=(physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
     rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_join.sv
     rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx.sv rtl/test/qwen_static_kv/tb_qkd_embedding_row_tx.sv)
ms="0 1 2 3";[[ -n $only ]]&&ms=$only
for m in $ms;do
 "$v" --binary --timing -O2 -j 8 -Wno-fatal --top-module tb_qkd_embedding_row_tx -DOT_KVJ_ROWTX_MUT=$m --Mdir "$out/m$m-obj" "${src[@]}" > "$out/m$m-build.log" 2>&1
 "$out/m$m-obj/Vtb_qkd_embedding_row_tx" > "$out/m$m.log" 2>&1 || true
 echo "== MUT $m"; grep -E '^(PASS|FAIL|POSITIVE|NEGATIVE)' "$out/m$m.log" | head -6 || true
 if [[ $m == 0 || -n $only ]];then { grep -q '^PASS' "$out/m$m.log" && ! grep -q '^FAIL' "$out/m$m.log"; } || exit 1;else grep -q '^FAIL' "$out/m$m.log";fi
done
[[ -n $only ]]&&{ echo "PASS MUT $only run as positive";exit 0;}
echo PASS KVJC_ROW_TX_EXACT_AND_OBSERVED_MUTANTS
