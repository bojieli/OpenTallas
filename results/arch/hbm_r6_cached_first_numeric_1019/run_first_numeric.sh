#!/bin/bash
set -uo pipefail
cd /srv/opentallas-scratch/claude/hbm-record6-implement-1019
exec 9>FIRST_numeric.lock
flock -n 9 || exit 91
if test -e FIRST_numeric.STARTED || test -e positive.log || test -e positive-FIRST.log; then echo FIRST_ALREADY_EXISTS; exit 92; fi
if pgrep -x Vtb >/dev/null; then echo OTHER_VTB_PRESENT; exit 93; fi
printf '%s\n' "$(date -u +%FT%TZ)" > FIRST_numeric.STARTED
ulimit -c 0
cd generated_clockfix
/usr/bin/time -v -o ../FIRST_numeric.time ../obj_r6/Vtb > ../positive-FIRST.log 2>&1
rc=$?
cd ..
printf '%s\n' "$rc" > FIRST_numeric.exit
printf '%s\n' "$(date -u +%FT%TZ)" > FIRST_numeric.ENDED
sha256sum positive-FIRST.log FIRST_numeric.time FIRST_numeric.exit FIRST_numeric.STARTED FIRST_numeric.ENDED > FIRST_numeric_result.sha256
exit "$rc"
