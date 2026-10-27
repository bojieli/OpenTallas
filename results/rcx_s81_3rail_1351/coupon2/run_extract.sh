#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
python3 "$D/../width_guard.py" "$D/physical_multi.rules" "$D/geometry.json" > "$D/width_guard.json"
docker run --rm --name s81-3rail-rcx-$$ --cpus=2 --memory=8g --memory-swap=8g -v "$D:/out" openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 2 -exit /out/extract.tcl"
