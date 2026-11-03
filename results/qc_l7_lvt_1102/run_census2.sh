#!/bin/bash
set -euo pipefail
exec docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow -e OT_CORNER=TT -e OT_POSTCTS_GRT=1 -e ODB=/work/final_5_1_grt.odb openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/census2.tcl' > census.log 2>&1
