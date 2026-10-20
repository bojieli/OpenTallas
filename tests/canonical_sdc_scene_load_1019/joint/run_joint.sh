#!/bin/bash
set -euo pipefail
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
mkdir -p joint_output
sha256sum inputs/*.odb tools/orfs_hold_mm.tcl physical/common_flow/native_pg*.tcl tests/canonical_sdc_scene_load_1019/coupon.sdc tests/canonical_sdc_scene_load_1019/joint/* > joint_output/source_before.sha256
docker image inspect "$IMG" --format '{{.Id}} {{json .RepoDigests}}' >joint_output/image.txt
docker run --rm "$IMG" bash -lc 'sha256sum /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad /OpenROAD-flow-scripts/flow/scripts/final_{connect,report}.tcl; find /OpenROAD-flow-scripts/flow/platforms/asap7 -name "*.lef" -exec sha256sum {} +; find /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -name "*_RVT_*" -exec sha256sum {} +' >joint_output/tool_libs.sha256
for case in default unbound allbound; do
 odb=checkpoint.odb
 if [ "$case" = allbound ]; then odb=allbound_fixture.odb; fi
 mkdir -p joint_output/$case
 docker run --rm -v "$PWD:/src" -w /src -e TEST_CASE="$case" -e TEST_ODB="/src/inputs/$odb" -e TEST_OUT="/src/joint_output/$case" -e TEST_BOOTSTRAP=/src/physical/common_flow/native_pg_bootstrap.tcl "$IMG" "$OR" -no_init -exit /src/tests/canonical_sdc_scene_load_1019/joint/compose.tcl >joint_output/$case/run.log 2>&1
done
sha256sum -c joint_output/source_before.sha256 > joint_output/source_after.txt
printf 'JOINT_NATIVE_SUITE_PASS\n'
