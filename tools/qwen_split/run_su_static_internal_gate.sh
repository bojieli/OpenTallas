#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
program=${1:?actual production25word source program};out=${2:?fresh output directory};mkdir "$out"
d=$root/rtl/qwen_sys/static_schedule_20261014
for mode in actual unavailable badpc_mutant;do
 p=();case "$mode" in unavailable)p=(-Ptb_qfd_su_static_internal.BAD_AVAILABLE=1);;badpc_mutant)p=(-Ptb_qfd_su_static_internal.BAD_PC=1);;esac
 iverilog -g2012 -I"$root/rtl/hdc" -s tb_qfd_su_static_internal "${p[@]}" -o "$out/$mode.sim" \
 "$root/rtl/hdc/ot_hdc_dyn_ttiles.sv" "$root/rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv" \
 "$d/ot_qwen_rom_core_ctrl_su_static.sv" "$d/ot_qwen_fixed_issue.sv" "$d/ot_qwen_fixed_issue_pw.sv" \
 "$root/rtl/test/qwen_split/tb_qfd_su_static_internal.sv" > "$out/$mode.compile.log" 2>&1
 if vvp "$out/$mode.sim" +PROGRAM="$program" > "$out/$mode.log" 2>&1;then rc=0;else rc=$?;fi
 echo "$rc" > "$out/$mode.exit"
 if [[ "$mode" == badpc_mutant ]];then [[ "$rc" != 0 ]];grep -q '^FATAL:.*fixed slot missed actual SU internal issue' "$out/$mode.log";else [[ "$rc" == 0 ]];grep -q '^PASS actual25word' "$out/$mode.log";fi
 cat "$out/$mode.log";rm "$out/$mode.sim"
done
sha256sum "$program" "$d/ot_qwen_rom_core_ctrl_su_static.sv" "$d/ot_qwen_fixed_issue.sv" "$d/ot_qwen_fixed_issue_pw.sv" "$root/rtl/test/qwen_split/tb_qfd_su_static_internal.sv" > "$out/source.sha256"
