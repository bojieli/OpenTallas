#!/usr/bin/env bash
set -euo pipefail
jobdir=/srv/opentallas-scratch2/scratch/codex/hbm-collector-sr-dpl-inspect-20261009
oldwork=/srv/opentallas-scratch2/scratch/claude/closure-loop/hbm_coll_sr3-acdfa3ab1-tc/routes/hbm_coll_sr3_acdfa3ab1_tc_cal/work/orfs
docker run --rm --network none -v "$oldwork:/old:ro" -v "$jobdir:/inspect:rw" \
 -e OT_FAILED_ODB=/old/results/asap7/opentallas_hfd_coll_asap7_hv_hbm_coll_sr3_acdfa3ab1_tc_cal/base/3_5_place_dp-failed.odb \
 openroad/orfs:asap7lock /usr/bin/time -v /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /inspect/report_sr_original_placement.tcl > "$jobdir/sr-original-placement-check.log" 2>&1
