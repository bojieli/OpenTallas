#!/bin/bash
set -euo pipefail
k=$1
name=codex-cp1-$(basename "$k")-$$
docker run --rm --name "$name" --cpus=8 --memory=64g --memory-swap=64g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 do-route do-finish
'
python3 "$k/signoff.py" run --run-dir "$k/run" --kit "$k" --name "$(basename "$k")" --out "$k/signoff_eco" --corners tt,ff
