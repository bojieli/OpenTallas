#!/bin/bash
set -u
export PYTHONDONTWRITEBYTECODE=1
job=/srv/opentallas-scratch2/jobs/harvey-cp-fourcut-parent-context-r1/runtime_r3
cd "$job/source" || exit 74
python3 "$job/fresh_guard.py" || exit $?
test ! -f "$job/route.started" || exit 77
test -z "$(git status --porcelain)" || exit 76
mkdir -p "$job/tmp"
export NUM_CORES=16 OT_ORFS_NUM_CORES=16 TMPDIR="$job/tmp"
date -u > "$job/route.started"
echo "$$" > "$job/route.pid"
python3 tools/hbm_cp_fourcut_route.py --job-root "$job" --resume-resized-sha256 689a1f8802da8fe0f6a2320523745d5231b6c5d5fad436db98f2365f784b5400 > "$job/route.log" 2>&1
rc=$?
if test ! -f "$job/terminal.exit"; then
 echo "$rc" > "$job/terminal.exit"
 echo 'Physical runner failed before complete corner/IR analysis; retain raw route.log.' > "$job/loaded_ir_skipped.txt"
fi
exit "$rc"
