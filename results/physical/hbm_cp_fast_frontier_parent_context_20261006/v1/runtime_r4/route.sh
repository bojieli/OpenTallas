#!/bin/bash
set -u
export PYTHONDONTWRITEBYTECODE=1
job=/srv/opentallas-scratch2/jobs/harvey-cp-fast-frontier-parent-context-v1/runtime_r4
cd "$job/source" || exit 74
python3 "$job/fresh_guard.py" || exit $?
test ! -f "$job/route.started" || exit 77
test -z "$(git status --porcelain)" || exit 76
mkdir -p "$job/tmp" "$job/work/orfs/tmp"
export NUM_CORES=16 OT_ORFS_NUM_CORES=16 TMPDIR="$job/tmp"
date -u > "$job/route.started"
echo "$$" > "$job/route.pid"
python3 tools/hbm_cp_fourcut_route.py --fast-owner --variant 1 --job-root "$job" --resume-cts-sha256 dae1eee390d7f6c6cda59ec7c383709f54acf692e12504fa653c4bc24d392ae0 > "$job/route.log" 2>&1
rc=$?
if test ! -f "$job/terminal.exit"; then
 echo "$rc" > "$job/terminal.exit"
 echo 'Runner exited; retain actual route.log and all saved objects.' > "$job/loaded_ir_skipped.txt"
fi
exit "$rc"
