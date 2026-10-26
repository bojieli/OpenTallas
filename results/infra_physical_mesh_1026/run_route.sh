#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
OR=/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad
docker run --rm -v "$D:/work" openroad/orfs:latest "$OR" -python -exit /work/check_connected.py > "$D/connected.log" 2>&1
docker run --rm -v "$D:/work" openroad/orfs:latest "$OR" -no_init -threads 4 -exit /work/route.tcl > "$D/route.log" 2>&1
