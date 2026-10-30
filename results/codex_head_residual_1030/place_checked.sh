#!/bin/bash
set -euo pipefail
K=$1
python3 -I "$K/kit_preflight.py" "$K" --out "$K/place_preflight.json"
docker run --rm --name codex-head-tile-place2 --cpus=8 --memory=64g --memory-swap=64g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place'
