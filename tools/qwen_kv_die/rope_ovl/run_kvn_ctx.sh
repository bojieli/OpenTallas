#!/bin/bash
set -euo pipefail
mkdir -p kvn-evidence
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
for variant in good wrong_user stale; do
  args=()
  if [ "$variant" = wrong_user ]; then args+=(-GMUT_USER=1); fi
  if [ "$variant" = stale ]; then args+=(-GMUT_STALE=1); fi
  "$V" --binary --timing -Wno-fatal --top-module tb_kvn_ctx_ovl --Mdir "obj_$variant" -j 1 "${args[@]}" qkd_kvn_ctx_ovl_rope.sv tb_kvn_ctx_ovl.sv > "kvn-evidence/build_$variant.log" 2>&1
  set +e
  "obj_$variant/Vtb_kvn_ctx_ovl" > "kvn-evidence/$variant.log" 2>&1
  rc=$?
  set -e
  if [ "$variant" = good ]; then test "$rc" = 0; grep -q KVN_CTX_OVL_PASS "kvn-evidence/$variant.log";
  else test "$rc" != 0; grep -Eq 'WRONG_USER_NOT_REJECTED|OWNER_FAIL' "kvn-evidence/$variant.log"; fi
  echo "$variant rc=$rc expected-verdict PASS"
done
