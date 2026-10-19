set -euo pipefail
cd ../..
ROOT=$PWD
ODB=$(find output/default/routes/canonical_cts/work/orfs/results -name 1_synth.odb)
mkdir -p output/default/analysis/load_mode_probe
docker run --rm -v "$ROOT:/src" -w /src -e COUPON_ODB=/src/$ODB -e COUPON_OUT=/src/output/default/analysis/load_mode_probe openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/tests/pg_canonical_coupon_cts_1019/load_mode_probe.tcl >output/default/analysis/load_mode_probe/native.log 2>&1
