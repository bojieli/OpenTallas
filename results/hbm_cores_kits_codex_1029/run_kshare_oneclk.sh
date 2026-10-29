#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
sha256sum ./*.sv > source.sha256
VL=$HOME/.local/opentallas-tools/bin/verilator
for c in baseline mutant; do
 (
  arg=0; [ "$c" != mutant ] || arg=1
  "$VL" --binary --timing -j 8 -O1 -Wno-fatal --top-module tb_kshare_oneclk -GMUT_CLOCK=$arg --Mdir obj_$c -o sim ./*.sv > build_$c.log 2>&1
  rc=0; ./obj_$c/sim > "$c.log" 2>&1 || rc=$?
  if [ "$c" = baseline ]; then [ "$rc" = 0 ]; grep ONECLK_PASS baseline.log
  else [ "$rc" != 0 ]; grep ONECLK_MISMATCH mutant.log; echo ONECLK_MUTANT_CAUGHT
  fi
 ) > "$c.result" 2>&1 &
done
wait
cat baseline.result mutant.result
grep -q ONECLK_PASS baseline.result && grep -q ONECLK_MUTANT_CAUGHT mutant.result
