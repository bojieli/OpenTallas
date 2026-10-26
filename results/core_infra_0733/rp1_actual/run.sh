#!/bin/bash
set -euo pipefail
TASK_DIR=$(cd "$(dirname "$0")" && pwd)
docker run --rm --cpus=2 --memory=8g --memory-swap=8g -v "$TASK_DIR":/work -w /work openroad/orfs:asap7lock bash -c 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /work/apply.tcl' > "$TASK_DIR/apply.log" 2>&1
