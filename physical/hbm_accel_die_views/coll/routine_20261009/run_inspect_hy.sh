#!/usr/bin/env bash
set -euo pipefail
jobdir=/srv/opentallas-scratch/codex/hbm-collector-dpl-inspect-20261009
oldwork=/srv/opentallas-scratch/claude/closure-loop/hbm_coll_hy-6f2cc51ae-tc/routes/hbm_coll_hy_6f2cc51ae_tc_cal/work/orfs
docker run --rm --network none \
 -v "$oldwork:/old:ro" -v "$jobdir:/inspect:ro" \
 -e OT_FAILED_ODB=/old/results/asap7/opentallas_hfd_coll_asap7_hv_hbm_coll_hy_6f2cc51ae_tc_cal/base/3_5_place_dp-failed.odb \
 openroad/orfs:asap7lock /usr/bin/time -v /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /inspect/inspect.tcl
