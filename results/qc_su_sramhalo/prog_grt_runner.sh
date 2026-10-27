#!/bin/bash
set -euo pipefail
K=$1
cp -a --reflink=auto "$K/baseline_run" "$K/run"
# GRT-only structural trial; no detailed route/signoff here.
docker run --rm --name codex-prog-halo2-grt --cpus 8 --memory 16g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_1_grt' > "$K/halo2_grt.log" 2>&1
echo "HALO2_GRT_DONE $(date -Is)" > "$K/halo2_chain.txt"
