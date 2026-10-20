#!/bin/bash
# D6 (LEAD2-HBM): numerical run of the f3cd6b6cc observer build, granted after build+audit PASS.
set -uo pipefail
R=/srv/opentallas-scratch2/claude/hbm-r6-epoch-build-only-1019
cd "$R" || exit 90
exec 9>EPOCH_numeric.lock
flock -n 9 || exit 91
test -e EPOCH_numeric.STARTED && { echo EPOCH_ALREADY_EXISTS; exit 92; }
grep -q BUILD_ONLY_COMPLETE STATUS.json || { echo BUILD_NOT_COMPLETE; exit 94; }
test -s actual_consumption_comparison.json && grep -q '"PASS"' actual_consumption_comparison.json || { echo AUDIT_NOT_PASS; exit 95; }
date -u +%FT%TZ > EPOCH_numeric.STARTED
ulimit -c 0
cd generated_clockfix
/usr/bin/time -v -o ../EPOCH_numeric.time ../obj_epoch/Vtb > ../positive-EPOCH.log 2>&1
rc=$?
cd ..
echo "$rc" > EPOCH_numeric.exit
date -u +%FT%TZ > EPOCH_numeric.ENDED
sha256sum positive-EPOCH.log EPOCH_numeric.time EPOCH_numeric.exit obj_epoch/Vtb > EPOCH_numeric_result.sha256
exit "$rc"
