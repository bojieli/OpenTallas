#!/bin/bash
set -u
J=/srv/opentallas/jobs-overflow/einstein-hbm-su-parent-owner-a6e322f55-r1
export NUM_CORES=16 TMPDIR=$J/tmp
mkdir -p "$TMPDIR"
/srv/opentallas-scratch/admit.sh 2 -- python3 "$J/gate.py" > "$J/run.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$J/terminal.rc"
exit "$rc"
