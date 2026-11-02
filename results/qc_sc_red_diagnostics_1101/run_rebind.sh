#!/bin/bash
set -euo pipefail
r=0
docker run --rm --cpus 1 --memory 8g --memory-swap 8g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/rebind.tcl' > rebind.log 2>&1 || r=$?
printf '%s\n' "$r" > rebind.rc
exit "$r"
