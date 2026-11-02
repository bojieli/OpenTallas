#!/bin/bash
set -euo pipefail
exec docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 /work/prepare_config.py
for co in TT FF; do
 OT_CORNER="$co" OT_POSTCTS_GRT=1 ODB=/work/LVT_DATA_GEOMETRY_CHECKPOINT.odb openroad -exit /work/postcts_gate.tcl > /work/lvt_${co}.log 2>&1
done
' > readout.log 2>&1
