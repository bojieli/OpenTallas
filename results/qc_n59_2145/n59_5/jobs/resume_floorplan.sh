#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-qc-n59-1026
K=$R/trial_flat/gen/native59
sudo docker run --rm --name codex-n59-flat-floorplan-resume --memory=32g --memory-swap=32g --cpus=16 -v "$K:/work" openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /OpenROAD-flow-scripts/flow
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 REMOVE_ABC_BUFFERS=1 -o /work/run/results/asap7/dp_native59/base/1_synth.odb floorplan
'
