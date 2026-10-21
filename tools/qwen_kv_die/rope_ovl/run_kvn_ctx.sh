#!/bin/bash
set -euo pipefail
SOURCE_ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
OUT=${1:-${OT_SCRATCH:-/srv/opentallas-scratch}/claude/codex-k-rope-1021/kvn-ctx}
mkdir -p "$OUT/kvn-evidence"
cd "$OUT"
RTL="$SOURCE_ROOT/rtl/qwen_sys/d2d_static_20261015/qkd_kvn_ctx_ovl_rope.sv"
BENCH="$SOURCE_ROOT/tools/qwen_kv_die/rope_ovl/tb_kvn_ctx_ovl.sv"
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
for variant in good wrong_user stale boot_phase; do
  args=()
  if [ "$variant" = boot_phase ]; then args+=(-GMUT_BOOT=1); fi
  if [ "$variant" = wrong_user ]; then args+=(-GMUT_USER=1); fi
  if [ "$variant" = stale ]; then args+=(-GMUT_STALE=1); fi
  "$V" --binary --timing -Wno-fatal --top-module tb_kvn_ctx_ovl --Mdir "obj_$variant" -j 1 "${args[@]}" "$RTL" "$BENCH" > "kvn-evidence/build_$variant.log" 2>&1
  set +e
  "obj_$variant/Vtb_kvn_ctx_ovl" > "kvn-evidence/$variant.log" 2>&1
  rc=$?
  set -e
  if [ "$variant" = good ]; then test "$rc" = 0; grep -q KVN_CTX_OVL_PASS "kvn-evidence/$variant.log";
  else test "$rc" != 0; grep -Eq 'WRONG_USER_NOT_REJECTED|OWNER_FAIL|BOOT_CONTEXT_NOT_IGNORED' "kvn-evidence/$variant.log"; fi
  echo "$variant rc=$rc expected-verdict PASS"
done
