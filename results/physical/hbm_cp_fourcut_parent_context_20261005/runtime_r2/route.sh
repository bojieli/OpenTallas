#!/bin/bash
set -u
export PYTHONDONTWRITEBYTECODE=1
job=/srv/opentallas-scratch2/jobs/harvey-cp-fourcut-parent-context-r1/runtime_r2
cd "$job/source" || exit 74
python3 "$job/fresh_guard.py" || exit $?
test ! -f "$job/route.started" || exit 77
test -z "$(git status --porcelain)" || exit 76
mkdir -p "$job/tmp"
export NUM_CORES=16 OT_ORFS_NUM_CORES=16 TMPDIR="$job/tmp"
date -u > "$job/route.started"
echo "$$" > "$job/route.pid"
python3 tools/hbm_cp_fourcut_route.py --job-root "$job" --resume-canonical /srv/opentallas-scratch2/jobs/harvey-cp-fourcut-parent-context-r1/runtime_r2/work/orfs/results/asap7/opentallas_ot_hbm_integrated_su_cp_context_asap7_harvey_cp_fourcut_context_r1/base/1_1_yosys_canonicalize.rtlil --canonical-sha256 a3916fe458bb8aad9315ff10c0a41e36063c33ab5e52532044acf9d5eb8ce810 > "$job/route.log" 2>&1
rc=$?
if test ! -f "$job/terminal.exit"; then
 echo "$rc" > "$job/terminal.exit"
 echo 'Physical runner failed before complete corner/IR analysis; retain raw route.log.' > "$job/loaded_ir_skipped.txt"
fi
exit "$rc"
