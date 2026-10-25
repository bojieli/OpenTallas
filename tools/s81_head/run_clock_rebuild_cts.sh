#!/bin/bash
set -euo pipefail
K=$(cd "$1" && pwd)
MEM=${2:-24}
THREADS=${3:-8}
docker run --rm --name "head1309-cts-$$" --cpus="$THREADS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$THREADS do-4_1_cts" > "$K/run_cts_head.log" 2>&1
