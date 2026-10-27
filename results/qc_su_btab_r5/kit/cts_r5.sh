#!/bin/bash
# QC-SU-BTAB-R5: CTS (plan-built H-tree from OT_MSCTS_SPEC, TritonCTS off, ITERS 0 report only) + GRT; no DRT.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd)
rc=0; docker run --rm --name btr5-cts-$(basename $K)-$$ --cpus=8 --memory=28g --memory-swap=28g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-cts && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-5_1_grt' > "$K/cts_grt.log" 2>&1 || rc=$?
docker run --rm -v "$K":/work openroad/orfs:asap7lock chown -R $(id -u):$(id -g) /work/run
python3 "$K/../collect_native.py" "$K" || true
exit $rc
