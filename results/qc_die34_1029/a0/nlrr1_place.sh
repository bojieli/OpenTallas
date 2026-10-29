#!/bin/bash
set -euo pipefail
k=/srv/opentallas-scratch2/claude/die-qc34-a0/kits/qfd_tile_nl_a0c_a0nl14icg2rr1
sudo docker run --rm --name dqc34-a0-nlrr1-place --cpus=8 --memory=32g --memory-swap=32g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -euo pipefail
top=$(sed -n "s/^export DESIGN_NAME = //p" /work/config.mk)
netlist=$(ls /work/run/results/asap7/*/base/1_synth.v)
python3 -I /work/face_guard_core.py "$netlist" "$top" "$(cat /work/face_guard_skip.txt)" /work/pins.json /work/face_guard.json
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place
' > "$k/place.log" 2>&1
