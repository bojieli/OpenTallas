#!/bin/bash
set -uo pipefail
root=/srv/opentallas-scratch2/claude/codex-tok-hbm-1026
out=$root/su31_hold_run
test ! -e "$out" || { echo REFUSE_EXISTING_OUTPUT; exit 2; }
mkdir "$out"
bin=/srv/opentallas-scratch2/claude/codex-hbm-token-1025/full/out/obj/Vtb_hbm_slice
sha256sum "$bin" > "$out/binary.sha256"
sha256sum "$root/replay_su31_hold"/*.mem > "$out/replay.sha256"
/usr/bin/time -v -o "$out/runtime.time" "$bin" +verilator+rand+reset+0 +REPLAY="$root/replay_su31_hold" +CYCLES=6400 +SHOWVAL > "$out/run.log" 2>&1
rc=$?
grep -E '^SLICE_SUMMARY|^OTM_SUM .*fault' "$out/run.log" > "$out/summary.log"
cat "$out/summary.log"
if test "$rc" = 0 && grep -q '^SLICE_SUMMARY .*checks=1046 fails=0 ' "$out/run.log" && ! grep -q '^OTM_SUM .*fault' "$out/run.log"; then
 echo SU31_CONTROL_HOLD_PASS > "$out/done"
 echo SU31_CONTROL_HOLD_PASS
else
 echo SU31_CONTROL_HOLD_FAIL > "$out/done"
 exit 1
fi
