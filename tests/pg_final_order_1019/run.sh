#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
mkdir -p output
sha256sum inputs/checkpoint.odb physical/common_flow/native_pg* tests/pg_final_order_1019/* >output/source.sha256
docker image inspect "$IMG" --format '{{.Id}} {{json .RepoDigests}}' >output/image.txt
docker run --rm "$IMG" bash -lc 'sha256sum /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad /OpenROAD-flow-scripts/flow/scripts/final_{connect,report}.tcl; find /OpenROAD-flow-scripts/flow/platforms/asap7 -name "*.lef" -exec sha256sum {} +; find /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -name "*_RVT_TT_*" -exec sha256sum {} +' >output/tool_libs.sha256
run() {
 local case=$1 odb=$2 boot=$3
 mkdir -p output/$case
 docker run --rm -v "$ROOT:/src" -w /src -e TEST_CASE="$case" -e TEST_ODB="/src/$odb" -e TEST_OUT="/src/output/$case" -e TEST_BOOTSTRAP="/src/$boot" "$IMG" "$OR" -no_init -exit /src/tests/pg_final_order_1019/compose.tcl >output/$case/run.log 2>&1
}
run baseline inputs/checkpoint.odb tests/pg_final_order_1019/baseline_bootstrap.tcl
run unbound inputs/checkpoint.odb physical/common_flow/native_pg_bootstrap.tcl
run protected inputs/checkpoint.odb physical/common_flow/native_pg_bootstrap.tcl
run default inputs/checkpoint.odb physical/common_flow/native_pg_bootstrap.tcl
docker run --rm -v "$ROOT:/src" -e TEST_ODB=/src/inputs/checkpoint.odb -e TEST_FIXTURE=/src/output/allbound_fixture.odb "$IMG" "$OR" -no_init -exit /src/tests/pg_final_order_1019/fixture.tcl >output/fixture.log 2>&1
run allbound output/allbound_fixture.odb physical/common_flow/native_pg_bootstrap.tcl
run dirty output/allbound_fixture.odb physical/common_flow/native_pg_bootstrap.tcl
run wrongrole output/allbound_fixture.odb physical/common_flow/native_pg_bootstrap.tcl
run ambiguous output/allbound_fixture.odb physical/common_flow/native_pg_bootstrap.tcl
sha256sum -c output/source.sha256 >output/source_after.txt
printf 'COMPOSE_NATIVE_SUITE_PASS\n'
