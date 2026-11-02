#!/bin/bash
set -euo pipefail
exec docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /work -e OT_GEOM_OUT=/work/lvt_place_geom.tsv openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/load_lvt.tcl' > lvt_place.log 2>&1
