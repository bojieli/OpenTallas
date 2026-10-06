#!/bin/bash
set -u
job=/srv/opentallas-scratch2/jobs/harvey-cp-fourcut-parent-context-r1/runtime_r2
python3 "$job/fresh_guard.py" || exit $?
exec /srv/opentallas-scratch/admit.sh 8 -- bash "$job/route.sh"
