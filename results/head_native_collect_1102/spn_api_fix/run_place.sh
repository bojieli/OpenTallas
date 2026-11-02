#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")" && pwd)
docker run --rm --cpus 8 --memory 16g --memory-swap 16g -v "$R/kit":/work -v "$R":/out openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /out/shift_band.tcl' > "$R/place.log" 2>&1
bash "$R/tools/geom_check.sh" "$R/geom" > "$R/geom.log" 2>&1
