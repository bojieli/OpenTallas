#!/bin/bash
set -u
export PYTHONDONTWRITEBYTECODE=1
job=/srv/opentallas-scratch2/jobs/harvey-cp-parent-context-route-r1
retry=/srv/opentallas-scratch2/jobs/harvey-cp-parent-context-route-r1/sdc_retry_r2
cd "$retry/source" || exit 74
python3 "$job/fresh_guard.py" || exit $?
test ! -f "$retry/route.started" || exit 77
test -z "$(git status --porcelain)" || exit 76
mkdir -p "$retry/tmp"
export NUM_CORES=16 OT_ORFS_NUM_CORES=16 TMPDIR="$retry/tmp"
date -u > "$retry/route.started"
echo "$$" > "$retry/route.pid"
python3 tools/hbm_cp_parent_context_resume.py --r1-root "$job" --retry-root "$retry" --corrected-sdc "$retry/corrected_constraint.sdc" > "$retry/route.log" 2>&1
rc=$?;echo "$rc" > "$retry/route.exit"
if find "$retry/work" -name 6_final.odb -print -quit | rg -q .; then
 python3 tools/hbm_cp_parent_context.py --corner-sta "$retry/work/orfs" --output "$retry/corner_sta.json" > "$retry/corner_sta.log" 2>&1
 echo "$?" > "$retry/corner.exit"
fi
echo "$rc" > "$retry/terminal.exit"
exit "$rc"
