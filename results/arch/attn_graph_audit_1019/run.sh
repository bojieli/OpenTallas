#!/bin/bash
set -euo pipefail
mkdir -p audit
sha256sum out/placed.odb input/physical.v input/candidate.v out/placed.v input/verify_import.tcl > audit/input_sha256.txt
docker image inspect openroad/orfs:asap7lock --format '{{.Id}}' > audit/image.txt
docker run --rm --network none -e OMP_NUM_THREADS=2 -v "$PWD/input:/input:ro" -v "$PWD/out:/placed:ro" -v "$PWD/audit:/audit" openroad/orfs:asap7lock bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /audit/export.tcl' > audit/export.log 2>&1
