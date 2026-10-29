#!/bin/bash
set -euo pipefail
K=$1
TAG=$2
HM=$3
docker run --rm --name "codex-coupled-grt-$TAG-$$" --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm_coupled.log 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 grt HOLD_SLACK_MARGIN=$HM" > "$K/run_coupled_grt.log" 2>&1
