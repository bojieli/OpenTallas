#!/bin/bash
set -uo pipefail
job=/srv/opentallas-scratch2/jobs/kant-code-pair-reverse-constant-ties-20261005-r3
export TMPDIR="$job/tmp"
export OMP_NUM_THREADS=16 OT_ORFS_NUM_CORES=16
ulimit -t unlimited
ulimit -v unlimited
ulimit -f unlimited
while ! test -f "$job/supervisor.exit"; do sleep 60; done
rc=$(cat "$job/supervisor.exit")
corner_rc=not_run
if test "$rc" = 0; then
 /srv/opentallas-scratch/admit.sh 64 -- python3 "$job/collector/qwen_code_pair_banklocal_corner.py" --orfs-dir "$job/route" --source-dir "$job/source" --output "$job/corner_sta.json" > "$job/corner_collection.log" 2>&1
 corner_rc=$?
fi
export KANT_ROUTE_RC="$rc" KANT_CORNER_RC="$corner_rc"
python3 "$job/collector/write_outcome.py"
finish_rc=$?
if test "$finish_rc" != 0; then rc=$finish_rc; elif test "$corner_rc" != not_run && test "$corner_rc" != 0; then rc=$corner_rc; fi
printf '%s\n' "$rc" > "$job/collector.exit"
exit "$rc"
