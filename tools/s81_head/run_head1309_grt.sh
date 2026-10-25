#!/bin/bash
set -euo pipefail
K=$(cd "$1" && pwd)
cp -p "$K/run/results/asap7/hd_elemB_rb/base/4_1_cts.odb" "$K/run/results/asap7/hd_elemB_rb/base/4_cts.odb"
docker run --rm --name "head1309-grt-$$" --memory=24g --memory-swap=24g --cpus=8 -v "$K:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 SKIP_INCREMENTAL_REPAIR=1 do-5_1_grt' > "$K/run_grt_head.log" 2>&1
