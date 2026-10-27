#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
docker run --rm -v "$D:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/build.tcl > "$D/build.log" 2>&1
