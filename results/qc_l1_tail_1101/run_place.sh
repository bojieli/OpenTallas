#!/bin/bash
set -euo pipefail
for f in core.json boundary_guard_context.json sdc_lint.json; do test -s "$f" || { echo "MISSING_EXACT_CLOCK_CONTEXT $f"; exit 2; }; done
exec docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /work -e OT_GEOM_OUT=/work/tail_place_geom.tsv openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/load_tail.tcl' > tail_place.log 2>&1
