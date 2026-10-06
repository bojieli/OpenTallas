#!/bin/bash
set -u
export PYTHONDONTWRITEBYTECODE=1
job=/srv/opentallas-scratch2/jobs/harvey-cp-fast-frontier-parent-context-v3/runtime_r2
cd "$job/source" || exit 74
python3 "$job/fresh_guard.py" || exit $?
test ! -f "$job/route.started" || exit 77
test -z "$(git status --porcelain)" || exit 76
mkdir -p "$job/tmp" "$job/work/orfs/tmp"
export NUM_CORES=16 OT_ORFS_NUM_CORES=16 TMPDIR="$job/tmp"
date -u > "$job/route.started"
echo "$$" > "$job/route.pid"
python3 tools/hbm_cp_fourcut_route.py --fast-owner --variant 3 --job-root "$job" --resume-io-sha256 4b957460786fe4ef4e1d351b84268b5df5028c5044848c19e4087d45f56af612 > "$job/route.log" 2>&1
rc=$?
if test ! -f "$job/terminal.exit"; then
 echo "$rc" > "$job/terminal.exit"
 echo 'Runner exited; retain actual route.log and all saved objects.' > "$job/loaded_ir_skipped.txt"
fi
exit "$rc"
