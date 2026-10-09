#!/usr/bin/env bash
set -euo pipefail
jobdir=/srv/opentallas-scratch2/scratch/codex/hbm-collector-sr-dpl-inspect-20261009
oldwork=/srv/opentallas-scratch2/scratch/claude/closure-loop/hbm_coll_sr3-acdfa3ab1-tc/routes/hbm_coll_sr3_acdfa3ab1_tc_cal/work/orfs
run_case() {
 docker run --rm --network none -v "$oldwork:/old:ro" -v "$jobdir:/inspect:ro" \
  -e OT_FAILED_ODB=/old/results/asap7/opentallas_hfd_coll_asap7_hv_hbm_coll_sr3_acdfa3ab1_tc_cal/base/3_5_place_dp-failed.odb \
  -e "OT_RX_EXPECTED_MASTER=$2" openroad/orfs:asap7lock \
  /usr/bin/time -v /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /inspect/check_rx_blockages.tcl > "$jobdir/$1.log" 2>&1
}
run_case halo-positive ot_sram_1r1w_128x256_m1_r2c2
grep -q 'RX_BLOCKAGE_POSITIVE_PASS' "$jobdir/halo-positive.log"
if run_case halo-wrongmaster negative_wrong_master; then
 echo 'wrong-master mutation unexpectedly passed'; exit 1
fi
grep -q 'RX_BLOCKAGE_REJECTED RX blockage wrong macro master' "$jobdir/halo-wrongmaster.log"
echo 'RX_BLOCKAGE_GATE_PASS full48 positive, wrongmaster rejected'
