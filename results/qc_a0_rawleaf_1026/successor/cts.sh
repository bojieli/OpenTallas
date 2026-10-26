#!/bin/bash
set -euo pipefail
K=$(pwd)
docker run --rm --cpus=8 --memory=40g --memory-swap=40g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run NUM_CORES=8 cts SKIP_CTS_REPAIR_TIMING=1
for c in TT FF; do
 CORNER=$c OT_PS_OUT=/work/pair_$c.tsv openroad -exit /work/cts_probe.tcl > /work/cts_$c.log 2>&1
done
' > "$K/cts.log" 2>&1
