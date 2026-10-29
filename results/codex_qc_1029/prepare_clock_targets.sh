#!/bin/bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
trap 'chown -R 1000:1000 /out' EXIT
openroad -no_init -threads 8 -exit /out/prepare_clock.tcl > /out/prepare_clock.log 2>&1
openroad -no_init -threads 8 -exit /out/prepare_signal.tcl > /out/prepare_signal.log 2>&1
openroad -python -exit /graft.py --source /out/clock_unrouted.odb --target /out/target_signal.odb --tree /work/clock/tree.json --out /out/clock_grafted.odb --report /out/endpoints.json > /out/graft.log 2>&1
