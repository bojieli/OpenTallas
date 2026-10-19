set -uo pipefail
cd ../..
ROOT=$PWD
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
ODB=$(find output/default/routes/canonical_cts/work/orfs/results -name 4_1_cts.odb)
SDC=${ODB%/*}/4_cts.sdc
for corner in TT FF SS; do
 docker run --rm -v "$ROOT:/src" -w /src -e COUPON_CORNER=$corner -e COUPON_ODB=/src/$ODB -e COUPON_SDC=/src/$SDC -e COUPON_PG_JSON=/src/output/default/analysis/pg_${corner}_complete.json "$IMG" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/tests/pg_canonical_coupon_cts_1019/read_corner.tcl >output/default/analysis/timing_${corner}_complete.log 2>&1
 echo "CORNER $corner actual_rc=$?"
done
python3 tests/pg_canonical_coupon_cts_1019/read_census.py >output/default/analysis/census_complete.log 2>&1
echo "CENSUS actual_rc=$?"
