#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
docker run --rm --name codex-ctlx-guided-1028 --cpus 4 --memory 16g --memory-swap 16g -v "$ROOT":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/trial.tcl > /work/trial.log 2>&1'
python3 "$ROOT/geom_rules.py" "$ROOT/geom.tsv" --odb "$ROOT/3_place_guided.odb" --all-kits --json "$ROOT/auto_geom.json"
