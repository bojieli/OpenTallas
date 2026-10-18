#!/usr/bin/env bash
# usage: OUT [M]  (M given: run only mutant M under the positive check, so a detected mutant exits non-zero)
# KVJ-C (c): per-PC es merge child vs qkd_embedding_static_pc (exact), mutants 1/2/3 must FAIL; the pc_path successor
# parent elaborates (lint) with every pc_path source.
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};only=${2:-};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
E=rtl/qwen_sys/static_embedding_20261014
src=($E/qkd_embedding_static_map.sv $E/qkd_embedding_static_pc.sv $E/qkd_static_kv_pc_es_merge.sv
     rtl/test/qwen_static_kv/tb_qkd_static_kv_pc_es_merge.sv)
ms="0 1 2 3";[[ -n $only ]]&&ms=$only
for m in $ms;do
 "$v" --binary --timing -O2 -j 8 -Wno-fatal --top-module tb_qkd_static_kv_pc_es_merge -DOT_KVJ_ESM_MUT=$m --Mdir "$out/m$m-obj" "${src[@]}" > "$out/m$m-build.log" 2>&1
 "$out/m$m-obj/Vtb_qkd_static_kv_pc_es_merge" > "$out/m$m.log" 2>&1 || true
 echo "== MUT $m"; grep -E '^(PASS|FAIL)' "$out/m$m.log" | head -5 || true
 if [[ $m == 0 || -n $only ]];then { grep -q '^PASS' "$out/m$m.log" && ! grep -q '^FAIL' "$out/m$m.log"; } || exit 1;else grep -q '^FAIL' "$out/m$m.log";fi
done
[[ -n $only ]]&&{ echo "PASS MUT $only run as positive";exit 0;}
pcs=$(python3 -c "import sys;sys.path.insert(0,'tools/qwen_kv_die');from static_pc_path_sources import SOURCES;print(' '.join(SOURCES))")
"$v" --lint-only -Wno-fatal -Wno-lint -Wno-style --top-module qkd_static_kv_pc_path_emb $pcs $E/qkd_embedding_static_map.sv \
  $E/qkd_static_kv_pc_es_merge.sv $E/qkd_static_kv_pc_path_emb.sv > "$out/parent-lint.log" 2>&1 || { tail -20 "$out/parent-lint.log"; exit 1; }
! grep -E '%Error|PINMISSING|PINNOTFOUND|WIDTH.*es_merged' "$out/parent-lint.log"
echo PASS KVJC_ES_MERGE_EXACT_OBSERVED_MUTANTS_PARENT_ELABORATES
