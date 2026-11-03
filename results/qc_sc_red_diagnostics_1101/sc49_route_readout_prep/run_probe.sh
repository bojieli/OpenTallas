#!/bin/bash
set -euo pipefail
r=0
docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/probe.tcl' > probe.log 2>&1 || r=$?
if [ "$r" -eq 0 ]; then python3 check_native_clock.py > native_clock_check.log 2>&1 || r=$?; fi
printf '%s\n' "$r" > probe.rc
exit "$r"
