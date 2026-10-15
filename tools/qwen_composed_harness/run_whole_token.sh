#!/usr/bin/env bash
# Link (no RTL rebuild) and run the whole-token driver under ot-run.
# Usage: run_whole_token.sh <stage> <plan> <out> [expected_token expected_value]
#   stage: directory holding src/ and deps/ (see README "Whole token")
#   MODE=syntax only compiles with -fsyntax-only (no LV6 archive needed).
set -euo pipefail
stage=${1:?stage}; plan=${2:-}; out=${3:?fresh output directory}
tok=${4:-50994}; val=${5:-1100755280}
d=$stage/deps; c=/srv/opentallas-scratch/codex
lv6=${LV6_OBJ:-$c/qwen-native-fullcore-lv6-1014/build/obj}
front=$d/native-services-front59-1014/v2/library/obj
sector=$d/native-services-frontend-1014/sector-library-v1/obj
pc=$d/qwen-native-hbm-pc-provider-1014/library_v2/obj
kernel=$d/qwen-composed-harness-f460-1014/kernel
# The LV6 core alone is 2.117 GB of text, so the f460 kernel (73 MB, same generated
# C++ as archive 54a3930e) is linked as a PIC shared library to keep the
# executable text under the 2 GB small-code-model limit.
kso=${KERNEL_SO_DIR:-$stage/kernel_pic}
# Opt-in during migration: fail closed when a supposedly RTL attention kernel
# still links host arithmetic. Other components are audited independently.
core_kernel_flags=()
if [[ "${ATTN_RTL_ONLY:-0}" == 1 ]]; then
 python3 "$(dirname "$0")/attention_rtl_library_check.py" "$kso"
 core_kernel_flags=(-DOT_KERNEL_HIERARCHICAL=1)
fi
helper=$d/qwen-full-layer-sequence-1014/native59_helper/obj
collector=$d/qwen-full-layer-sequence-1014/libnative59.so
probe=${PROBE_OBJ:-$d/qwen-full-layer-sequence-1014/core_instruction_probe.o}
hostc=$c/qwen-native-host-callable-1014
host=$hostc/full8bb9a6c00-compiledO1/obj; board=$hostc/boardd4a77a6c7/obj
alloc=$hostc/native-host-owner-models/allocator; cohort=$hostc/native-host-owner-models/cohort
embed=$c/qwen-host-embedding-1014/embedding
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include
[[ ! -e "$out" ]]; mkdir -p "$out"
inc=(-I"$stage/src" -I"$lv6" -I"$front" -I"$sector" -I"$pc" -I"$kso/obj" -I"$helper" -I"$host" -I"$board" -I"$alloc" -I"$cohort" -I"$embed/obj" -I"$vroot" -I"$vroot/vltstd")
if [[ "${MODE:-run}" == syntax ]]; then
 g++ -std=c++20 -fsyntax-only "${inc[@]}" "$stage/src/whole_token.cpp" > "$out/syntax.log" 2>&1 && echo PASS_SYNTAX_ONLY || { cat "$out/syntax.log" | head -40; exit 2; }
 exit 0
fi
python3 - "$lv6" <<'PY'
import json,sys
from pathlib import Path
r=json.loads((Path(sys.argv[1]).parent/'receipt.json').read_text())
assert r['exit']==0 and '-GLV=6' in r['command'] and '-GG=3072' in r['command'], r
PY
# LV6_HIER=1: hierarchical LV6 build (hier FP blocks are separate archives).
core_flags=("${core_kernel_flags[@]}")
if [[ "${LV6_HIER:-0}" == 1 ]]; then
 [[ -n "${PROBE_OBJ:-}" ]] || { echo 'hierarchical core requires a probe rebuilt against its own generated root' >&2; exit 2; }
 python3 - "$lv6" "$probe" <<'PYPROBE'
import hashlib,sys
from pathlib import Path
core,probe=map(Path,sys.argv[1:])
manifest=(probe.parent/'inputs.sha256').read_text().splitlines()
for f in (core/'Vot_hdc_core_vector_weight_native_candidate___024root.h',probe):
 h=hashlib.sha256(f.read_bytes()).hexdigest()
 assert any(line.split(maxsplit=1)==[h,str(f)] for line in manifest), f'probe provenance mismatch: {f}'
PYPROBE
 core_flags+=(-DOT_CORE_HIERARCHICAL=1)
 python3 "$stage/src/core_arithmetic_receipt.py" --core "$lv6" --output "$out/core_arithmetic.json"
 mapfile -t lv6a < <(find "$lv6" -name '*.a' ! -name libverilated.a | sort); else lv6a=("$lv6/Vot_hdc_core_vector_weight_native_candidate__ALL.a"); fi
arch=("${lv6a[@]}" "$front/Vot_qwen_tp8_native_services_frontend_native59__ALL.a"
 "$sector/Vot_qwen_tp8_kv_sector_adapter__ALL.a" "$pc/Vqwen_native_hbm_pc_provider__ALL.a"
 "$helper/Vot_qwen_native59__ALL.a" "$host/Vqkd_host_token_service__ALL.a" "$board/Vqkd_host_board_port_fixture__ALL.a"
 "$alloc/Vot_qwen_tp8_token_epoch_allocator__ALL.a" "$cohort/Vot_qwen_tp8_token_cohort__ALL.a" "$embed/obj/Vot_qwen_tp8_embedding_core__ALL.a")
sha256sum $(find "$stage/src" -maxdepth 1 -type f) "${arch[@]}" "$probe" "$collector" "$kso/libot_qwen_tp8_attention_service.so" $(ls "$kso"/generated_sources.sha256 "$kso"/source.sha256 2>/dev/null) "$kernel/sim_hdc_v41x_fastfp_dpi.o" "$kernel/sim_nhb_fp_lat_dpi.o" > "$out/inputs.sha256"
g++ -std=c++20 -O1 -pthread -rdynamic "${core_flags[@]}" "${inc[@]}" "$stage/src/whole_token.cpp" "$probe" -Wl,--start-group "${arch[@]}" -Wl,--end-group \
 "$kernel/sim_hdc_v41x_fastfp_dpi.o" "$kernel/sim_nhb_fp_lat_dpi.o" \
 "$vroot/verilated.cpp" "$vroot/verilated_threads.cpp" "$vroot/verilated_dpi.cpp" "$kso/libot_qwen_tp8_attention_service.so" -Wl,-rpath,"$kso" -ldl -o "$out/whole_token" > "$out/link.log" 2>&1
sha256sum "$out/whole_token" > "$out/binary.sha256"
[[ -n "$plan" ]] || { echo PASS_LINK_ONLY; exit 0; }
sha256sum "$plan" >> "$out/inputs.sha256"
set +e
"$out/whole_token" "$plan" "$embed/embedding_program.hex" "$embed/vectors" "$stage/head/image" "$stage/head/program" \
 "$collector" "$out/actual" "$tok" "$val" > "$out/run.log" 2>"$out/run.err"
rc=$?
set -e
echo "$rc" > "$out/executable_status.txt"
tail -5 "$out/run.err"; cat "$out/run.log"
exit "$rc"
