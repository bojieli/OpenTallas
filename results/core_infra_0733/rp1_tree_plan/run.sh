#!/bin/bash
set -euo pipefail
TASK_DIR=$(cd "$(dirname "$0")" && pwd)
docker run --rm --cpus=2 --memory=8g --memory-swap=8g -v "$TASK_DIR":/work -w /work openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/apply_tree.tcl > "$TASK_DIR/apply_tree.log" 2>&1
