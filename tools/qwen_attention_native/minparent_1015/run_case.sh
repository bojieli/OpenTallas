#!/bin/bash
# Invoke through ot-run; exit status is simulator status, inspect native JSON verdict.
set -euo pipefail
stage=$(cd "$(dirname "$0")" && pwd)
out=$1; vec=$2; ctx=$3; mode=$4; calendar=${5:-}
mkdir -p "$out"
binary="$stage/b5a/obj/Vtb_qwen_tp8_attention_native_service"
expected=f7a58155389c6022d34ebe1db685119bd71f59cc4632c66b55484f774492ca99
actual=$(sha256sum "$binary"); [[ ${actual%% *} == "$expected" ]]
args=("+VEC=$vec" "+CTX=$ctx" "+MODE=$mode")
if [[ -n $calendar ]]; then args+=("+CAL=$calendar"); fi
/usr/bin/time -v stdbuf -oL "$binary" "${args[@]}" > "$out/native.log" 2> "$out/native.time"
