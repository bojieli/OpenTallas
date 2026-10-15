#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh evidence directory}
mkdir "$out"
for mode in positive conflict data_mutant latency_mutant; do
 params=()
 case "$mode" in
 conflict) params=(-Ptb_qfd_su_static_copy.CONFLICT=1);;
 data_mutant) params=(-Ptb_qfd_su_static_copy.DATA_MUT=1);;
 latency_mutant) params=(-Ptb_qfd_su_static_copy.LATENCY_MUT=1);;
 esac
 iverilog -g2012 -s tb_qfd_su_static_copy "${params[@]}" -o "$out/$mode.sim" \
 "$root/rtl/qwen_split/qfd_su_vm_pack.sv" "$root/rtl/qwen_split/qfd_su_static_copy.sv" \
 "$root/rtl/test/qwen_split/tb_qfd_su_static_copy.sv"
 if vvp "$out/$mode.sim" > "$out/$mode.log" 2>&1; then rc=0; else rc=$?; fi
 echo "$rc" > "$out/$mode.exit"
 case "$mode" in
 positive|conflict) [[ "$rc" == 0 ]]; grep -q '^PASS raw4096words' "$out/$mode.log";cat "$out/$mode.log";;
 *) [[ "$rc" != 0 ]];grep -q '^FATAL:.*FAIL exact static replay' "$out/$mode.log";echo "OBSERVED $mode numerical failure rc$rc";;
 esac
 rm "$out/$mode.sim"
done
sha256sum "$root/rtl/qwen_split/qfd_su_vm_pack.sv" "$root/rtl/qwen_split/qfd_su_static_copy.sv" "$root/rtl/test/qwen_split/tb_qfd_su_static_copy.sv" > "$out/source.sha256"
