set -euo pipefail
cd ../..
ROOT=$PWD
ODB=$(find output/default/routes/canonical_cts/work/orfs/results -name 4_1_cts.odb)
printf 'read_db /src/%s\nsource /src/tools/ref_tile/layout_dump.tcl\nexit\n' "$ODB" >output/default/analysis/dump_layout.tcl
docker run --rm -v "$ROOT:/src" -w /src -e OT_LAYOUT_OUT=/src/output/default/analysis/layout_dump.json -e OT_LAYOUT_CLOCKS=clk -e OT_LAYOUT_TOP=ot_pg_canonical_xor16_1019 openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/output/default/analysis/dump_layout.tcl >output/default/analysis/layout_dump.log 2>&1
python3 tools/ref_tile/layout_png.py output/default/analysis/layout_dump.json output/default/analysis/layout --title 'Canonical PG default actual CTS; DIAG HOLD'
