#!/bin/bash
set -eu
b=/srv/opentallas-scratch2/claude/codex-qca0/icg-bench
for m in 0 12 2; do
  set +e
  "$b/Vtb_a0_icg" +OT_ROM_DIR="$b/rom" +ICG_MUT=$m > "$b/m$m.log" 2>&1
  rc=$?
  set -e
  if [ "$m" = 0 ]; then test "$rc" = 0; grep -q A0ICG_PASS "$b/m$m.log"; else test "$rc" != 0; grep -q A0ICG_FAIL "$b/m$m.log"; fi
done
