#!/bin/bash
set -euo pipefail
# INTENTIONALLY DISABLED until complete capsule ROOT review/dispatch scope.
echo 'NOT RUN: retained-route capsule awaits ROOT review and explicit scope' >&2
exit 70
# Planned native body below, unreachable while PREP-only.
mkdir -p run/results/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base run/reports/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base
set +e
docker run --rm --cpus 4 --memory 32g --memory-swap 32g \
 -v /srv/opentallas-scratch2/claude/codex-qc-l1-lvt-route2-0015:/work:ro \
 -v "$PWD":/repair -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl
python3 /repair/input_adapter.py /OpenROAD-flow-scripts/flow/scripts
make DESIGN_CONFIG=/repair/config.mk WORK_HOME=/repair/run FLOW_VARIANT=base NUM_CORES=4 do-5_2_route
'
native_status=$?
set -e
compare_status=1
if [ -s "$PWD/actual_after_route.odb" ]; then
 set +e
 docker run --rm --cpus 2 --memory 8g --memory-swap 8g \
  -v /srv/opentallas-scratch2/claude/codex-qc-l1-lvt-route2-0015:/work:ro \
  -v "$PWD":/repair -w /repair \
  -e OT_RETAINED_A=/work/run/results/asap7/kq_qfd_qc_su_lane_w_l1_w0e61bf/base/5_2_route.odb \
  -e OT_RETAINED_B=/repair/actual_after_route.odb \
  -e OT_RETAINED_RESULT=/repair/retained_compare.json \
  openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /repair/compare_retained.py'
 compare_status=$?
 set -e
fi
if [ "$native_status" -ne 0 ]; then exit "$native_status"; fi
exit "$compare_status"
