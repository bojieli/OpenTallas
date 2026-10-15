#!/bin/bash
# Q-ATTN: run a built native static attention bench over vectors/modes in parallel.
# Usage: run.sh <build dir> <out dir> <vec>:<mode> ...
set -uo pipefail
b=$(realpath "$1"); out=$(realpath -m "$2"); shift 2
V=/srv/opentallas-scratch/codex/native-service-f46073090/vectors
mkdir -p "$out"; sha256sum "$b/obj/Vtb_qwen_tp8_attention_native_service" > "$out/binary.sha256"
for c in "$@"; do v=${c%%:*}; m=${c##*:}; n="$v-$m"
 ( /usr/bin/time -v "$b/obj/Vtb_qwen_tp8_attention_native_service" +VEC="$V/$v" +MODE="$m" > "$out/$n.log" 2> "$out/$n.time"; echo $? > "$out/$n.exit" ) &
done; wait
for c in "$@"; do v=${c%%:*}; m=${c##*:}; n="$v-$m"; echo "== $n exit=$(cat $out/$n.exit)"; grep -E '^\{|FIRST_FAULT|TIMEOUT|MISMATCH' "$out/$n.log" | head -5; done
