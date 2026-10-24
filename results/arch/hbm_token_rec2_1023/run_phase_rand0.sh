#!/usr/bin/env bash
set -uo pipefail
TASK=/srv/opentallas-scratch/claude/codex-hbm-token-0936-1023
SOURCE=/srv/opentallas-scratch/claude/tokd-hbm2/r18h5_src
BIN=$SOURCE/out/obj/Vtb_hbm_slice
[ -x "$BIN" ] || exit 2
mkdir -p "$TASK/phase_rand0"
sha256sum "$BIN" > "$TASK/phase_rand0/binary.sha256"
printf '%s\n' 'DIAGNOSTIC/TRUNCATED: expected acceptance failures, never functional PASS; existing binary, unchanged450-edge drive prefix/preload.' > "$TASK/phase_rand0/run.log"
/usr/bin/time -v -o "$TASK/phase_rand0/run.time" "$BIN" +verilator+rand+reset+0 +REPLAY="$TASK/replay" +CYCLES=450 +SHOWVAL >> "$TASK/phase_rand0/run.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$TASK/phase_rand0/exit.rc"
exit "$rc"
