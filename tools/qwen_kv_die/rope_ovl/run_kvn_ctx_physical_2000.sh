#!/bin/bash
# Exact existing de062 testbench and compile options; one actual variant, raw exit preserved.
set -euo pipefail
SOURCE_ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=$1; variant=$2
case "$variant" in good) args=();; wrong_user) args=(-GMUT_USER=1);; stale) args=(-GMUT_STALE=1);; *) exit 2;; esac
mkdir -p "$OUT"; OUT=$(cd "$OUT" && pwd)
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
RTL="$SOURCE_ROOT/rtl/qwen_sys/d2d_static_20261015/qkd_kvn_ctx_ovl_rope.sv"
TB="$SOURCE_ROOT/tools/qwen_kv_die/rope_ovl/tb_kvn_ctx_physical_2000.sv"
sha256sum "$RTL" "$TB" > "$OUT/source.sha256"
"$V" --binary --timing -DOT_FO_CHECK -Wno-fatal --top-module tb_kvn_ctx_ovl --Mdir "$OUT/obj" -j 1 "${args[@]}" "$RTL" "$TB" "$SOURCE_ROOT/tools/qwen_kv_die/rope_ovl/reference/qkd_kvn_ctx_de062_ref.sv" "$SOURCE_ROOT/tools/qwen_kv_die/rope_ovl/tb_kvn_ctx_copy_equiv.sv" > "$OUT/build.log" 2>&1
set +e
"$OUT/obj/Vtb_kvn_ctx_ovl" > "$OUT/run.log" 2>&1
rc=$?
set -e
cat "$OUT/run.log"
exit "$rc"
