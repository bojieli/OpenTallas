#!/bin/bash
# waits for build-only controller 3079170, then (D6) runs numerical on the same host dir
set -uo pipefail
A=/home/ubuntu/artifacts/hbm-r6-epoch-numeric-1019
B=/home/ubuntu/artifacts/hbm-r6-epoch-build-only-1019
R=/srv/opentallas-scratch2/claude/hbm-r6-epoch-build-only-1019
while kill -0 3079170 2>/dev/null; do sleep 60; done
echo "build controller ended $(date -u +%FT%TZ) rc=$(cat $B/controller_exit_code 2>/dev/null)" >> $A/chain.log
rc=$(cat $B/controller_exit_code 2>/dev/null || echo none)
if [ "$rc" != 0 ]; then echo BUILD_FAILED_rc=$rc > $A/chain.verdict; exit 1; fi
/home/ubuntu/bin/ot-run --mem 16 --threads 1 --disk 5 --dir $R -- bash -s < $A/run_numeric.sh > $A/ot-run.log 2>&1
nrc=$?
echo "numeric ot-run rc=$nrc $(date -u +%FT%TZ)" >> $A/chain.log
echo NUMERIC_rc=$nrc > $A/chain.verdict
