#!/bin/bash
set -u
r=/home/ubuntu/artifacts/hbm-int8-cts-granted-run-1019
/home/ubuntu/bin/ot-run --mem 24 --threads 8 --dir /srv/opentallas-scratch/claude/hbm-int8-cts-granted-run-1019 -- env INT8_CTS_WORK=/srv/opentallas-scratch/claude/hbm-int8-cts-granted-run-1019 INT8_CTS_ROOT_APPROVAL=/srv/opentallas-scratch/claude/hbm-int8-cts-granted-run-1019/ROOT_APPROVAL.json bash /srv/opentallas-scratch/claude/hbm-int8-cts-granted-run-1019/kit/run.sh > "$r/ot-run.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$r/exit_status"
exit "$rc"
