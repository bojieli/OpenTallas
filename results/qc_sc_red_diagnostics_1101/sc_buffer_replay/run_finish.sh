#!/bin/bash
set -euo pipefail
r=0
docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/finish_observers.tcl' > observer_recovery.log 2>&1 || r=$?
printf '%s\n' "$r" > observer_recovery.rc
if [ "$r" -ne 0 ]; then exit "$r"; fi
python3 check_native_clock.py > native_clock_check.log
bash run_readout.sh
