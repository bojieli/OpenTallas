#!/bin/bash
set -euo pipefail
K=$1
cp -a --reflink=auto "$K/baseline_run" "$K/run"
python3 - "$K" <<'PY'
from pathlib import Path
import sys
k=Path(sys.argv[1]);r=k/'run'
# Baseline stays immutable. In the fresh run retain only synthesis checkpoints; regenerate floorplan/place.
for p in r.glob('results/asap7/*/base/*'):
 if p.is_file() and p.name[:1] in '23456':p.unlink()
for p in r.glob('logs/asap7/*/base/*'):
 if p.is_file() and p.name[:1] in '23456':p.unlink()
PY
docker run --rm --name codex-btab-r9-place --cpus 8 --memory 24g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 OT_MSCTS_SPEC=/work/mscts_place.tcl floorplan && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 OT_MSCTS_SPEC=/work/mscts_place.tcl place' > "$K/place_r9.log" 2>&1
echo "BTAB_R9_PLACE_DONE $(date -Is)"
