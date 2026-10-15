#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory};mkdir "$out"
for mode in positive missing_commit stale_q final_fault early_complete_mutant; do
 p=()
 case "$mode" in
 missing_commit)p=(-Ptb_qfd_native59_static_service.MISSING_COMMIT=1);;
 final_fault)p=(-Ptb_qfd_native59_static_service.FINAL_FAULT=1);;
 stale_q)p=(-Ptb_qfd_native59_static_service.STALE_Q=1);;
 early_complete_mutant)p=(-Ptb_qfd_native59_static_service.MISSING_COMMIT=1 -Ptb_qfd_native59_static_service.MUT_EARLY_COMPLETE=1);;
 esac
 iverilog -g2012 -s tb_qfd_native59_static_service "${p[@]}" -o "$out/$mode.sim" "$root/rtl/qwen_split/qfd_native59_static_service.sv" "$root/rtl/test/qwen_split/tb_qfd_native59_static_service.sv"
 if vvp "$out/$mode.sim" > "$out/$mode.log" 2>&1;then rc=0;else rc=$?;fi
 echo "$rc" > "$out/$mode.exit"
 if [[ "$mode" == early_complete_mutant ]];then [[ "$rc" != 0 ]];grep -q '^FATAL:.*FAIL completion' "$out/$mode.log";else [[ "$rc" == 0 ]];grep -q '^PASS static59' "$out/$mode.log";fi
 cat "$out/$mode.log";rm "$out/$mode.sim"
done
for mode in positive early_slot mask_mutant;do
 p=()
 case "$mode" in early_slot)p=(-Ptb_qfd_kv_static.EARLY=1);;mask_mutant)p=(-Ptb_qfd_kv_static.MUT_MASK=1);;esac
 iverilog -g2012 -s tb_qfd_kv_static "${p[@]}" -o "$out/formatter_$mode.sim" "$root/rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv" "$root/rtl/test/qwen_split/tb_qfd_kv_static.sv" > "$out/formatter_$mode.compile.log" 2>&1
 if vvp "$out/formatter_$mode.sim" > "$out/formatter_$mode.log" 2>&1;then rc=0;else rc=$?;fi
 echo "$rc" > "$out/formatter_$mode.exit"
 if [[ "$mode" == mask_mutant ]];then [[ "$rc" != 0 ]];grep -q '^FATAL:.*FAIL static formatter' "$out/formatter_$mode.log";else [[ "$rc" == 0 ]];grep -q '^PASS static formatter' "$out/formatter_$mode.log";fi
 cat "$out/formatter_$mode.log";rm "$out/formatter_$mode.sim"
done
sha256sum "$root/rtl/qwen_split/qfd_native59_static_service.sv" "$root/rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv" "$root/rtl/test/qwen_split/tb_qfd_native59_static_service.sv" "$root/rtl/test/qwen_split/tb_qfd_kv_static.sv" > "$out/source.sha256"
