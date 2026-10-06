#!/bin/bash
set -u
export PYTHONDONTWRITEBYTECODE=1
job=/srv/opentallas-scratch2/jobs/harvey-cp-parent-context-route-r1
src=/srv/opentallas-scratch2/jobs/harvey-cp-parent-context-source-r1
python3 "$job/fresh_guard.py" || exit $?
exec /srv/opentallas-scratch/admit.sh 8 -- bash "$job/route.sh"
