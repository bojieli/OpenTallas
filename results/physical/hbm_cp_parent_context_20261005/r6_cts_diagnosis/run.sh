#!/bin/bash
set -u
j=/srv/opentallas-scratch2/jobs/harvey-cp-parent-context-route-r1
r="$j/cts_failure_probe_r6"
python3 "$j/fresh_guard.py" || exit $?
exec /srv/opentallas-scratch/admit.sh 8 -- python3 "$r/run.py"
