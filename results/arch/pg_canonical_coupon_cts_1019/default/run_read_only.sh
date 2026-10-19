#!/bin/bash
set -uo pipefail
cd ../..
ROOT=$PWD
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
ODB=$(find output/default/routes/canonical_cts/work/orfs/results -name 4_1_cts.odb)
SDC=${ODB%/*}/4_cts.sdc
mkdir -p output/default/analysis
RUN=(docker run --rm -v "$ROOT:/src" -w /src "$IMG")
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_cts_1019/native_geometry.py /src/$ODB /src/output/default/analysis > output/default/analysis/geometry.log 2>&1
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_1019/export_raw.py /src/$ODB /src/output/default/analysis > output/default/analysis/raw.log 2>&1
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_1019/native_cost.py /src/$ODB /src/output/default/analysis/native_cost.json > output/default/analysis/cost.log 2>&1
for corner in TT FF SS; do
 docker run --rm -v "$ROOT:/src" -w /src -e COUPON_CORNER=$corner -e COUPON_ODB=/src/$ODB -e COUPON_SDC=/src/$SDC -e COUPON_PG_JSON=/src/output/default/analysis/pg_$corner.json "$IMG" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/tests/pg_canonical_coupon_cts_1019/read_corner.tcl >output/default/analysis/timing_$corner.log 2>&1
done
mkdir -p output/default/analysis/libs
docker run --rm -v "$ROOT:/src" "$IMG" bash -lc 'cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_* /src/output/default/analysis/libs/'
python3 tests/pg_canonical_coupon_cts_1019/read_census.py >output/default/analysis/census.log 2>&1
