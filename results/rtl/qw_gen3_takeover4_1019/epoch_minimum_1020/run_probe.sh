#!/bin/bash
set -u
T=/srv/opentallas-scratch/claude/codex-qw-dieclk3-recover-1020
for c in tt ff; do
 bash "$T/dietop_run.sh" "$T/reset_probe_$c" probe.tcl 8 128 > "$T/reset_probe_$c/client_stage.log" 2>&1
 rc=$?; echo "$rc" > "$T/reset_probe_$c/probe.rc"
 [ "$rc" = 0 ] || exit "$rc"
done
