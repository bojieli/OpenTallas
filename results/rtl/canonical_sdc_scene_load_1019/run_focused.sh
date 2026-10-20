#!/bin/bash
set -uo pipefail
export PYTHONPATH=/srv/opentallas-scratch/claude/canonical-sdc-scene-load-fix-1019/pylib
cd /srv/opentallas-scratch/claude/canonical-sdc-scene-load-fix-1019/cohort/candidate
python3 -m pytest -q -p no:cacheprovider tools/closure_loop/test_mm_scene_load_lifecycle.py tools/closure_loop/test_mm_link_period.py tools/closure_loop/test_rc_ioref_order.py tools/closure_loop/test_route_ff_ioref.py tools/closure_loop/test_helper_overlay.py > focused.log 2>&1
rc=$?
echo "$rc" > focused.rc
cat focused.log
exit "$rc"
