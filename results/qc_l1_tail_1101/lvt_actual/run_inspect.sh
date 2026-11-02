#!/bin/bash
set -euo pipefail
exec docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$PWD":/work -w /work -e OT_GEOM_OUT=/work/geom.tsv openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/inspect_grt.tcl' > inspect.log 2>&1
