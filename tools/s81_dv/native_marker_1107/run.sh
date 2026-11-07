#!/bin/bash
set -u
cd "$(dirname "$0")"
export CCACHE_DISABLE=1
V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --binary --timing --assert -Wno-fatal --top-module tb -j 2 -CFLAGS '-O1 -fno-var-tracking' -Mdir obj tb.sv ot_dsdv_walk_issue.sv > build.log 2>&1
rc=$?; echo "$rc" > build.rc
[ "$rc" -eq 0 ] || exit "$rc"
obj/Vtb > positive.log 2>&1
rc=$?; echo "$rc" > positive.rc
[ "$rc" -eq 0 ] || exit "$rc"
obj/Vtb +OLDTAG=1 > oldtag.log 2>&1
rc=$?; echo "$rc" > oldtag.rc
[ "$rc" -ne 0 ] || exit 92
# A stale tag can set both missing-tag and unsolicited-completion flags;
# the issuer gives unsolicited completion (6) priority over bad tag (8).
grep -Eq 'runtime page.*code(6|8)' oldtag.log || exit 93
echo 'COMPONENT_PASS actual8 pages, stale-row-tag control caught'
