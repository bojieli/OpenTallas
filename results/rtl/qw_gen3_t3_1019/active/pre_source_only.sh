#!/bin/bash
set -u
S=/srv/opentallas-scratch/claude/mu-die-qw/dv2f19g3c1
cd "$S"
/usr/bin/time -v bash "$S/gen.sh" > "$S/PRE_SOURCE_ONLY.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$S/PRE_SOURCE_ONLY.rc"
exit "$rc"
