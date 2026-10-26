#!/bin/bash
set -eu
D=$(cd "$(dirname "$0")" && pwd)
for f in build build_target; do docker run --rm -v "$D:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -no_init /work/$f.tcl > "$D/$f.log" 2>&1; done
