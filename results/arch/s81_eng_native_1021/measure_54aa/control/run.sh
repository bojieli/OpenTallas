#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")/.." && pwd)
docker run --rm -e LEC_CHECK=0 -e OT_CTS_MACRO_CLUSTER -v "$D/source:/src:ro" -v "$D/work:/work" -v "$D/baseline:/baseline:ro" -v "$D/control:/control:ro" -w /OpenROAD-flow-scripts/flow sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts
python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 /work/results/asap7/opentallas_dsfd_engram_lkp_ra640_asap7_ref_gate/base/1_2_yosys.v
python3 /control/native.py
' > "$D/run.log" 2>&1
