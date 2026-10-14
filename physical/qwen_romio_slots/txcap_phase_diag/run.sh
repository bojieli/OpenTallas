#!/usr/bin/env bash
set -eu
sha256sum -c source.sha256 > source_verify.log
docker image inspect openroad/orfs:latest --format '{{.Id}}' > loaded_image.txt
docker run --rm -v "$PWD/macro:/mv0:ro" openroad/orfs:latest bash -c 'sha256sum /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*lib* /mv0/*lib' > loaded_lib_hashes.txt
for phase_corner in tt ff ss;do
 docker run --rm -v "$PWD:/diag:ro" -v "$PWD/macro:/mv0:ro" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /diag/phase_${phase_corner}.tcl > phase_${phase_corner}.log 2>&1
 grep '^OT_' phase_${phase_corner}.log
done
