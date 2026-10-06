#!/bin/bash
set -u
export PYTHONDONTWRITEBYTECODE=1
job=/srv/opentallas-scratch2/jobs/harvey-cp-fast-frontier-parent-context-v1/runtime_r2
cd "$job/source" || exit 74
python3 "$job/fresh_guard.py" || exit $?
test ! -f "$job/route.started" || exit 77
test -z "$(git status --porcelain)" || exit 76
mkdir -p "$job/tmp" "$job/work/orfs/tmp"
export NUM_CORES=16 OT_ORFS_NUM_CORES=16 TMPDIR="$job/tmp"
date -u > "$job/route.started"
echo "$$" > "$job/route.pid"
python3 tools/hbm_cp_fourcut_route.py --fast-owner --variant 1 --job-root "$job" --resume-io-sha256 a7c7c6b2bee15e13e578d7b8d70328cfe4c2466e7cc6c22fbbb4d9e0645e3cdf > "$job/route.log" 2>&1
rc=$?
if test ! -f "$job/terminal.exit"; then
 echo "$rc" > "$job/terminal.exit"
 echo 'Runner exited; retain actual route.log and all saved objects.' > "$job/loaded_ir_skipped.txt"
fi
exit "$rc"
