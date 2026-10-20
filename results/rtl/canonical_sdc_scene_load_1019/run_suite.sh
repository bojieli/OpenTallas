#!/bin/bash
set -uo pipefail
export PYTHONPATH=/srv/opentallas-scratch/claude/canonical-sdc-scene-load-fix-1019/pylib
cd /srv/opentallas-scratch/claude/canonical-sdc-scene-load-fix-1019/cohort
for kind in baseline candidate; do
 cd "$kind"
 python3 -m pytest -q -p no:cacheprovider tools/ref_tile tools/closure_loop > current_full.log 2>&1
 rc=$?
 echo "$rc" > current_full.rc
 tail -3 current_full.log
 cd ..
done
