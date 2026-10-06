#!/bin/bash
set -u
job=/srv/opentallas-scratch2/jobs/harvey-cp-fast-frontier-parent-context-v1/runtime_r3
python3 "$job/fresh_guard.py" || exit $?
exec /srv/opentallas-scratch/admit.sh 8 -- bash "$job/route.sh"
