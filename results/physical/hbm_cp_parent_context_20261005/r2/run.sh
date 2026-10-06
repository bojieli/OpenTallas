#!/bin/bash
set -u
job=/srv/opentallas-scratch2/jobs/harvey-cp-parent-context-route-r1
retry=/srv/opentallas-scratch2/jobs/harvey-cp-parent-context-route-r1/sdc_retry_r2
python3 "$job/fresh_guard.py" || exit $?
exec /srv/opentallas-scratch/admit.sh 8 -- bash "$retry/route.sh"
