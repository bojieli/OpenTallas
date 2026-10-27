#!/bin/bash
# QC-SU-BTAB-R5: re-run DPL only (GPL result kept) after adding pre_dpl_r5.tcl
set -euo pipefail
K=$(cd "$(dirname "$0")" && pwd)
rc=0; docker run --rm --name btr5-dp-$$ --cpus=8 --memory=16g --memory-swap=16g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-3_5_place_dp do-3_place" > "$K/place_r5dp.log" 2>&1 || rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/run
exit $rc
