#!/bin/bash
set -eu
mkdir output
odb=/srv/opentallas-scratch/claude/closure-loop/qfd_sys_face_mu_dhuser-k3-46980a0f6/routes/qfd_sys_face_mu_dhuser_k3_46980a0f6/work/orfs/results/asap7/opentallas_qfd_sys_face_mu_dhuser_asap7_ref_qfd_sys_face_mu_dhuser_k3_46980a0f6/base/6_final.odb
sha256sum "$odb" > output/odb_before.sha256
image=$(docker image inspect --format '{{.Id}}' openroad/orfs:asap7lock)
docker image inspect "$image" > output/image_inspect.json
docker run --rm --entrypoint sha256sum "$image" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad > output/binary.sha256
/usr/bin/time -v docker run --rm --entrypoint /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -v "$odb:/input/final.odb:ro" -v "$PWD:/collector:ro" -v "$PWD/output:/output" "$image" -exit /collector/all_rows.tcl > output/native.log 2>output/time.log
sha256sum "$odb" > output/odb_after.sha256
