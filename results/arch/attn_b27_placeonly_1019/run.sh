#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p out
docker image inspect openroad/orfs:asap7lock --format '{{.Id}}' > out/image.txt
docker run --rm --network none -v "$PWD/input:/input:ro" -v "$PWD/out:/out" openroad/orfs:asap7lock bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /input/export_old.tcl' > out/export_old.log 2>&1
docker run --rm --network none -v "$PWD/input:/input:ro" -v "$PWD/out:/out" openroad/orfs:asap7lock python3 /input/clean_def.py
docker run --rm --network none -e OMP_NUM_THREADS=8 -v "$PWD/input:/input:ro" -v "$PWD/out:/out" openroad/orfs:asap7lock bash -lc '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /input/place.tcl' > out/place.log 2>&1
