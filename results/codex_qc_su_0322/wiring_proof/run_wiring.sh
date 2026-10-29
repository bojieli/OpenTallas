#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-qc-su-0322/wiring_current0
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
for v in positive mutant; do
 set +e
 yosys -Q -T -p "read_verilog -sv $D/miter.sv; hierarchy -check -top top_$v; proc; flatten; opt_clean; sat -verify -prove ok 1 -show-ports" > "$D/$v.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "$D/$v.rc";tail -10 "$D/$v.log"
done
test "$(cat "$D/positive.rc")" = 0
test "$(cat "$D/mutant.rc")" != 0
grep -q 'model found: FAIL' "$D/mutant.log"
echo WIRING_POSITIVE_PASS_MUTANT_CAUGHT
