#!/bin/bash
# Separate read-only source-stage consumer. No floorplan or clock mutation.
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
test -s /work/run/results/asap7/dp_tt_ctlm/base/1_synth.odb
test -s /work/dont_use_check.json
openroad -exit /work/producer/read_synth_inventory.tcl > /work/producer/read_synth_inventory.log 2>&1
python3 -I /work/producer/join_synth_inventory.py
