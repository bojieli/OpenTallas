set -uo pipefail
cd ../..
ROOT=$PWD
ODB=$(find output/default/routes/canonical_cts/work/orfs/results -name 1_synth.odb)
mkdir -p output/default/analysis/source_synth
cp output/default/analysis/signal_identity.log output/default/analysis/signal_identity_stage_a_names_mismatch.log
docker run --rm -v "$ROOT:/src" -w /src openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tests/pg_canonical_coupon_1019/export_raw.py /src/$ODB /src/output/default/analysis/source_synth >output/default/analysis/source_synth/export.log 2>&1
echo "SOURCE_EXPORT actual_rc=$?"
python3 tests/pg_canonical_coupon_cts_1019/read_signal_identity.py >output/default/analysis/signal_identity_actual_source.log 2>&1
echo "SIGNAL_IDENTITY actual_rc=$?"
python3 tests/pg_canonical_coupon_cts_1019/render_native.py >output/default/analysis/render_native.log 2>&1
echo "NATIVE_RENDER actual_rc=$?"
