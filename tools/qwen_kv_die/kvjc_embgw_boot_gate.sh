#!/usr/bin/env bash
# KVJ-C (a): boot-only embedding gateway == qkd_embgw_splitboot with r_ea idle (exact), mutants 5 and 6 must FAIL.
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src=(rtl/qwen_sys/static_embedding_20261014/qkd_embgw_boot.sv rtl/qwen_sys/split_20261014/qkd_embgw_splitboot.sv
     rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_strip.sv rtl/test/qwen_host/tb_qkd_embgw_splitboot.sv
     rtl/test/qwen_static_kv/tb_qkd_embgw_boot_equiv.sv)
for m in 0 5 6;do
 "$v" --binary --timing -O2 -j 8 -Wno-fatal --top-module tb_qkd_embgw_boot_equiv -DOT_KVJ_EMBGW_MUT=$m --Mdir "$out/m$m-obj" "${src[@]}" > "$out/m$m-build.log" 2>&1
 "$out/m$m-obj/Vtb_qkd_embgw_boot_equiv" > "$out/m$m.log" 2>&1 || true
 echo "== MUT $m"; grep -E '^(PASS|FAIL|PHASE|BOOT)' "$out/m$m.log" | head -6 || true
 if [[ $m == 0 ]];then grep -q '^PASS' "$out/m$m.log";! grep -q '^FAIL' "$out/m$m.log";else grep -q '^FAIL' "$out/m$m.log";fi
done
echo PASS KVJC_EMBGW_BOOT_EQUIV_AND_OBSERVED_MUTANTS
