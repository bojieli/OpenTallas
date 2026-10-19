set -uo pipefail
cd ../..
ROOT=$PWD
export COUPON_MODE=strict
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
ODB=$(find output/strict/routes/canonical_cts/work/orfs/results -name 4_1_cts.odb)
SYNTH=$(find output/strict/routes/canonical_cts/work/orfs/results -name 1_synth.odb)
SDC=${ODB%/*}/4_cts.sdc
OUT=output/strict/analysis
mkdir -p $OUT/source_synth $OUT/libs
sha256sum tests/pg_canonical_coupon_cts_1019/{native_geometry.py,read_corner.tcl,read_census.py,read_conductor.py,read_signal_identity.py,render_native.py} >$OUT/analysis_source.sha256
RUN=(docker run --rm -v "$ROOT:/src" -w /src "$IMG")
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_cts_1019/native_geometry.py /src/$ODB /src/$OUT >$OUT/geometry.log 2>&1
echo "GEOMETRY actual_rc=$?"
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_1019/export_raw.py /src/$ODB /src/$OUT >$OUT/raw.log 2>&1
echo "RAW actual_rc=$?"
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_1019/export_raw.py /src/$SYNTH /src/$OUT/source_synth >$OUT/source_synth/export.log 2>&1
echo "SOURCE_SYNTH_EXPORT actual_rc=$?"
"${RUN[@]}" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_1019/native_cost.py /src/$ODB /src/$OUT/native_cost.json >$OUT/cost.log 2>&1
echo "COST actual_rc=$?"
"${RUN[@]}" bash -lc 'cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_RVT_TT_* /src/output/strict/analysis/libs/'
for corner in TT FF SS; do
 docker run --rm -v "$ROOT:/src" -w /src -e COUPON_CORNER=$corner -e COUPON_ODB=/src/$ODB -e COUPON_SDC=/src/$SDC -e COUPON_PG_JSON=/src/$OUT/pg_${corner}_complete.json "$IMG" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/tests/pg_canonical_coupon_cts_1019/read_corner.tcl >$OUT/timing_${corner}_complete.log 2>&1
 echo "CORNER $corner actual_rc=$?"
done
python3 tests/pg_canonical_coupon_cts_1019/read_census.py >$OUT/census.log 2>&1
echo "CENSUS actual_rc=$?"
python3 tests/pg_canonical_coupon_cts_1019/read_signal_identity.py >$OUT/signal_identity.log 2>&1
echo "SIGNAL_IDENTITY actual_rc=$?"
python3 tests/pg_canonical_coupon_cts_1019/read_conductor.py $OUT/native_geometry.json >$OUT/conductor.log 2>&1
echo "CONDUCTOR actual_rc=$?"
python3 tests/pg_canonical_coupon_cts_1019/render_native.py >$OUT/render_native.log 2>&1
echo "NATIVE_RENDER actual_rc=$?"
sha256sum -c $OUT/analysis_source.sha256 >$OUT/analysis_source_after.sha256
