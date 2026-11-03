#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")" && pwd)
docker run --rm --cpus 2 --memory 4g --memory-swap 4g -v "$R/input":/input:ro -v "$R":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 2 -python -exit /work/audit.py' > "$R/audit.log" 2>&1
