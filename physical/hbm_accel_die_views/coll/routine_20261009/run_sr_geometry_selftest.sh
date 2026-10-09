#!/usr/bin/env bash
set -euo pipefail
jobdir=/srv/opentallas-scratch2/scratch/codex/hbm-collector-sr-dpl-inspect-20261009
oldwork=/srv/opentallas-scratch2/scratch/claude/closure-loop/hbm_coll_sr3-acdfa3ab1-tc/routes/hbm_coll_sr3_acdfa3ab1_tc_cal/work/orfs
odb=/old/results/asap7/opentallas_hfd_coll_asap7_hv_hbm_coll_sr3_acdfa3ab1_tc_cal/base/3_5_place_dp-failed.odb
run_case() {
 docker run --rm --network none -v "$oldwork:/old:ro" -v "$jobdir:/probe:rw" \
  -e OT_FAILED_ODB="$odb" -e OT_SR_CHECK_ONLY_ODB="$odb" -e OT_SR_GEOMETRY_SELFTEST=1 "$@" \
  openroad/orfs:asap7lock /usr/bin/time -v /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /probe/probe_sr_bounded_release181.tcl
}
run_case > "$jobdir/sr-geometry-selftest-positive.log" 2>&1
grep -q SR_GEOMETRY_SELFTEST_PASS_NOT_LEGALITY "$jobdir/sr-geometry-selftest-positive.log"
if run_case -e OT_SR_WRONG_MOVEMENT=1 > "$jobdir/sr-geometry-selftest-wrongmovement.log" 2>&1; then
 echo 'SR wrong movement unexpectedly passed';exit 1
fi
grep -q SR_RELEASED_ANCHOR_OUTSIDE_BUDGET "$jobdir/sr-geometry-selftest-wrongmovement.log"
echo 'SR_GEOMETRY_SELFTEST_GATE_PASS_NOT_LEGALITY'
