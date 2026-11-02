#!/bin/bash
set -euo pipefail
r=0
docker run --rm --cpus 1 --memory 8g --memory-swap 8g -e SC_CLASSIFICATION_ONLY=1 -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/probe.tcl' > preflight.log 2>&1 || r=$?
printf '%s\n' "$r" > preflight.rc
exit "$r"
