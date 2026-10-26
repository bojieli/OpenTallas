#!/bin/bash
set -euo pipefail
stage=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$stage/discovery"
/usr/bin/time -v "$stage/b5a/obj/Vtb_qwen_tp8_attention_native_service" +VEC="$stage/vectors/full8192" +CTX=8192 +MODE=steady > "$stage/discovery/full8192.log" 2> "$stage/discovery/full8192.time"
