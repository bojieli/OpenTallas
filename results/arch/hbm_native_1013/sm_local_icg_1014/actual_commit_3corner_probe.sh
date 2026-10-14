#!/bin/bash
set -euo pipefail
R=$(dirname "$(readlink -f "$0")")
C=$R/routes/gate/work/orfs
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
for corner in tt ff ss; do
 docker run --rm -e SM_CORNER="$corner" -e OT_GATE_SIGNOFF_SDC=/src/physical/ref_tile/smh_own_local_icg_eg_ref/signoff.sdc -v "$R/src:/src:ro" -v "$C:/work" -v "$R/actual_commit_3corner_probe.tcl:/probe.tcl:ro" "$image" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /probe.tcl > "actual_commit_${corner}.log" 2>&1
 cat "actual_commit_${corner}.log"
done
