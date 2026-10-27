#!/bin/bash
set -euo pipefail
K=$1
docker run --rm --name codex-btab-r10-ctsgrt --cpus 8 --memory 20g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-cts && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_1_grt' > "$K/r10_cts_grt.log" 2>&1
echo "BTAB_R10_GRT_DONE $(date -Is)" > "$K/r10_chain.txt"
