#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
docker run --rm --cpus 2 --memory 8g --memory-swap 8g -v "$D/input":/input:ro -v "$D":/work openroad/orfs:asap7lock bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 2 -python -exit /work/audit.py' > "$D/audit.log" 2>&1
