#!/bin/bash
# Invoke through ot-run; exit status is simulator status, inspect native JSON verdict.
set -euo pipefail
stage=$(cd "$(dirname "$0")" && pwd)
out=$1; vec=$2; ctx=$3; mode=$4; calendar=${5:-}
mkdir -p "$out"
binary="$stage/b5b/obj/Vtb_qwen_tp8_attention_native_service"
expected=a1b4a4dc824fca1ae3a3716dcfd93f7cec501b46b4ad4401edb3017228f7e6d2
actual=$(sha256sum "$binary"); [[ ${actual%% *} == "$expected" ]]
args=("+VEC=$vec" "+CTX=$ctx" "+MODE=$mode")
if [[ -n $calendar ]]; then args+=("+CAL=$calendar"); fi
/usr/bin/time -v stdbuf -oL "$binary" "${args[@]}" > "$out/native.log" 2> "$out/native.time"
